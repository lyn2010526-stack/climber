from datetime import UTC, datetime, timedelta

import pytest

from app.core.integration.domestic_provider import LocalQQBotProvider
from app.core.security.domestic_adapter import QRTokenStore, sign_webhook, verify_webhook_signature


def test_webhook_signature_is_fresh_and_constant_time_checked() -> None:
    body = b'{"event":"ready"}'
    signature = sign_webhook("local-test-secret", body, 100)
    assert verify_webhook_signature("local-test-secret", body, signature, "100", now=100)
    assert not verify_webhook_signature("wrong", body, signature, "100", now=100)
    assert not verify_webhook_signature("local-test-secret", body, signature, "100", now=401)


def test_qr_tokens_expire_and_are_single_use() -> None:
    store = QRTokenStore(ttl_seconds=60)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token = store.issue(now=now)
    assert store.consume(token.token, now=now + timedelta(seconds=59))
    assert not store.consume(token.token, now=now + timedelta(seconds=59))

    expired = store.issue(now=now)
    assert not store.consume(expired.token, now=now + timedelta(seconds=60))


def test_local_provider_is_external_call_free() -> None:
    provider = LocalQQBotProvider(QRTokenStore(ttl_seconds=30))
    assert provider.status().mode == "local"
    token = provider.issue_binding_token()
    assert provider.consume_binding_token(token.token)


@pytest.mark.asyncio
async def test_domestic_api_has_explicit_disabled_state(client) -> None:
    status = await client.get("/api/v1/integrations/domestic/status")
    assert status.status_code == 200
    assert status.json()["provider"]["mode"] == "disabled"

    qr = await client.post("/api/v1/integrations/domestic/qqbot/qr")
    assert qr.status_code == 200
    assert qr.json()["status"] == "disabled"

    webhook = await client.post("/api/v1/integrations/domestic/qqbot/webhook", content=b"{}")
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "disabled"
