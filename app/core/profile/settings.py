"""Persisted, explicit consent for local interaction learning."""

# Chinese user-facing notice uses Chinese punctuation.
# ruff: noqa: RUF001
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, select, text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base

NOTICE_VERSION = "2026-10-02-v1"
NOTICE = (
    "开启后，系统会使用本项目内的对话任务类型、工具、思考等级、成败及反馈学习习惯，"
    "并将统计摘要用于后续任务上下文；配置的模型服务可能接收该摘要。"
    "画像事件不保存指令正文，不采集外部隐私数据。"
    "可随时停用，停用后停止新增学习和使用画像，已有数据保留；原始画像默认隐藏。"
    "本版本清除接口仅提供设计说明，尚不执行清除。"
)


class ProfileLearningSettings(Base):
    __tablename__ = "user_profile_learning_settings"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_raw_profile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def load_settings(db, user_id: str, *, lock: bool = False):
    # Local installs can use this feature before a schema migration is applied.
    connection = await db.connection()
    if lock and connection.dialect.name == "sqlite":
        # Serialize setting updates with event acceptance on SQLite too.
        await db.execute(text("BEGIN IMMEDIATE"))
    await connection.run_sync(lambda conn: ProfileLearningSettings.__table__.create(conn, checkfirst=True))
    query = select(ProfileLearningSettings).where(ProfileLearningSettings.user_id == user_id)
    if lock:
        query = query.with_for_update()
    return (await db.execute(query)).scalar_one_or_none()


def learning_enabled(row) -> bool:
    return bool(row and row.enabled and row.consent_version == NOTICE_VERSION and row.consented_at)


def settings_payload(row) -> dict:
    return {
        "enabled": learning_enabled(row),
        "show_raw_profile": bool(row and row.show_raw_profile),
        "consent_required": not bool(row and row.consent_version == NOTICE_VERSION and row.consented_at),
        "consent_version": row.consent_version if row else None,
        "consented_at": row.consented_at if row else None,
        "notice_version": NOTICE_VERSION,
        "notice": NOTICE,
    }
