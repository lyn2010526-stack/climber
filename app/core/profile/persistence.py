"""Persistence adapter between the in-memory profile loop and the database.

``ProfileStore`` is the only writer of ``user_profile_events``: it re-uses the
``ProfileLoopService`` validation semantics (privacy boundary, outcome and
feedback vocabulary) before anything reaches the database, then replays the
stored event log into a fresh service on every read so summaries survive
restarts and never depend on process-local state.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.profile import (
    PrivacyBoundaryError,
    ProfileEvent,
    ProfileLoopService,
    ProfileSummary,
)
from app.core.profile.settings import (
    NOTICE_VERSION,
    ProfileLearningSettings,
    learning_enabled,
    load_settings,
    settings_payload,
)
from app.storage import async_session
from app.storage.models_user_profile import UserProfileEvent
from app.storage.repository_user_profile import (
    DEFAULT_SOURCE,
    append_event,
    upsert_snapshot,
)

REPLAY_EVENT_LIMIT = 10_000

# Verbatim instruction text is not persisted in the event log (it lives in
# user_instruction_traces), so replay fills the mandatory field with a fixed,
# clearly-marked placeholder. It only feeds the non-empty validation check;
# the statistical fields all come from the stored row.
REPLAYED_INSTRUCTION = "(archived interaction)"


class ProfileStore:
    """Persist Agent-internal profile events and rebuild summaries from them."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        half_life_days: float = 30.0,
        persona_clusters: int = 4,
    ) -> None:
        self._service_kwargs: dict[str, Any] = {
            "enabled": enabled,
            "half_life_days": half_life_days,
            "persona_clusters": persona_clusters,
        }

    async def get_settings(self, user_id: str) -> dict[str, Any]:
        async with async_session() as db:
            return settings_payload(await load_settings(db, user_id))

    async def update_settings(
        self,
        user_id: str,
        *,
        enabled: bool,
        consent_version: str | None = None,
        show_raw_profile: bool | None = None,
    ) -> dict[str, Any]:
        if type(enabled) is not bool or (
            show_raw_profile is not None and type(show_raw_profile) is not bool
        ):
            raise ValueError("settings must be boolean")
        async with async_session() as db:
            row = await load_settings(db, user_id, lock=True)
            if (
                enabled
                and not (row and row.consent_version == NOTICE_VERSION and row.consented_at)
                and consent_version != NOTICE_VERSION
            ):
                raise ValueError("explicit consent to the current notice is required")
            if row is None:
                row = ProfileLearningSettings(user_id=user_id, show_raw_profile=False)
                db.add(row)
            if enabled and consent_version == NOTICE_VERSION:
                row.consent_version = NOTICE_VERSION
                row.consented_at = datetime.now(UTC)
            row.enabled = enabled
            if show_raw_profile is not None:
                row.show_raw_profile = show_raw_profile
            await db.commit()
            return settings_payload(row)

    async def record_event(self, user_id: str, **event_fields: Any) -> UserProfileEvent:
        """Validate one event through the profile loop, then persist it.

        ``event_fields`` accepts the same keyword arguments as
        :class:`~app.core.profile.ProfileEvent`. ``None`` values are dropped so
        the dataclass defaults apply, and a source outside the Agent-internal
        boundary raises ``ValueError`` before any write happens.
        Disabled learning also raises ``ValueError`` before opening a database
        session, preserving existing events without accepting new signals.
        """
        source = event_fields.get("source") or DEFAULT_SOURCE
        if source not in ProfileLoopService.ALLOWED_SOURCES:
            allowed = ", ".join(sorted(ProfileLoopService.ALLOWED_SOURCES))
            raise ValueError(f"source must be one of [{allowed}], got {source!r}")

        fields = {key: value for key, value in event_fields.items() if value is not None}
        fields["source"] = source
        event = ProfileEvent(**fields)

        service = ProfileLoopService(**self._service_kwargs)
        try:
            if not service.record(event):
                raise ValueError("profile learning is disabled")
        except PrivacyBoundaryError as exc:
            raise ValueError(str(exc)) from exc

        async with async_session() as db:
            if not learning_enabled(await load_settings(db, user_id, lock=True)):
                raise ValueError("profile learning is disabled")
            row = await append_event(
                db,
                user_id=user_id,
                task_type=event.task_type,
                outcome=event.outcome,
                tool=event.tool,
                reasoning_level=event.reasoning_level,
                feedback=event.feedback,
                interrupted=event.interrupted,
                retried=event.retried,
                source=event.source,
                occurred_at=event.occurred_at,
            )
            await db.commit()
        return row

    async def record_run(
        self,
        user_id: str,
        *,
        instruction: str,
        outcome: str,
        task_type: str = "general",
        **event_fields: Any,
    ) -> UserProfileEvent:
        """Record a completed run using the profile event contract."""
        return await self.record_event(
            user_id,
            instruction=instruction,
            task_type=task_type,
            outcome=outcome,
            **event_fields,
        )

    async def summary(self, user_id: str) -> ProfileSummary:
        """Rebuild the summary from the stored event log and refresh the snapshot."""
        service = await self._load_service(user_id)
        result = service.summary()
        if not result.enabled:
            return result
        async with async_session() as db:
            # A pause committed during replay also takes effect before return.
            if not learning_enabled(await load_settings(db, user_id, lock=True)):
                return ProfileLoopService(enabled=False).summary()
            # The snapshot caches this replay; blending it back double-counts events.
            await upsert_snapshot(
                db,
                user_id=user_id,
                payload=asdict(result),
                confidence=result.confidence,
            )
            await db.commit()
        return result

    async def suggestions(self, user_id: str, current_instruction: str) -> dict[str, object]:
        """Return profile hints that keep the current instruction authoritative."""
        service = await self._load_service(user_id)
        if service.enabled:
            async with async_session() as db:
                # Recheck consent after replay, matching the summary read path.
                if not learning_enabled(await load_settings(db, user_id, lock=True)):
                    service = ProfileLoopService(enabled=False)
        return service.auxiliary_context(current_instruction)

    async def _load_service(self, user_id: str) -> ProfileLoopService:
        """Replay one user's stored events into a fresh in-memory service."""
        async with async_session() as db:
            if not self._service_kwargs["enabled"] or not learning_enabled(
                await load_settings(db, user_id)
            ):
                return ProfileLoopService(**{**self._service_kwargs, "enabled": False})
            # Select the recent window first, then replay it oldest-first.
            rows = (
                (
                    await db.execute(
                        select(UserProfileEvent)
                        .where(UserProfileEvent.user_id == user_id)
                        .order_by(UserProfileEvent.occurred_at.desc(), UserProfileEvent.id.desc())
                        .limit(REPLAY_EVENT_LIMIT)
                    )
                )
                .scalars()
                .all()
            )
        service = ProfileLoopService(**self._service_kwargs)
        for row in reversed(rows):
            service.record(self._to_event(row))
        return service

    @staticmethod
    def _to_event(row: UserProfileEvent) -> ProfileEvent:
        return ProfileEvent(
            instruction=REPLAYED_INSTRUCTION,
            task_type=row.task_type,
            outcome=row.outcome,
            tool=row.tool,
            reasoning_level=row.reasoning_level,
            feedback=row.feedback or "neutral",
            interrupted=row.interrupted,
            retried=row.retried,
            occurred_at=row.occurred_at,
            source=row.source,
        )
