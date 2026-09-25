"""Local mock HTTP contracts only; NOT live service acceptance tests.

Run: python3 tests/test_integration_clients_http_contract.py
Loads only the owned clients, bypassing app startup, package barrels and conftest.
Every HTTP request uses MockTransport; sockets/DNS are blocked during each test.
Tokens and identifiers below are fictional fixtures, never environment values.

Primary contracts:
https://docs.slack.dev/reference/methods/chat.postMessage/
https://docs.discord.com/developers/resources/message#create-message
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/
https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/
https://developers.notion.com/reference/post-page
https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03
https://developers.notion.com/reference/retrieve-a-data-source
"""
from __future__ import annotations

import asyncio
import base64
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import httpx


PACKAGE = "_isolated_integration_http_contract"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(Path(__file__).resolve().parents[1] / "app/integrations/clients")]
sys.modules[PACKAGE] = package
http = importlib.import_module(f"{PACKAGE}._http")
slack = importlib.import_module(f"{PACKAGE}.slack_client")
discord = importlib.import_module(f"{PACKAGE}.discord_client")
jira = importlib.import_module(f"{PACKAGE}.jira_client")
notion = importlib.import_module(f"{PACKAGE}.notion_client")
REAL_ASYNC_CLIENT = httpx.AsyncClient
TOKEN = "fixture-token-not-a-credential"
CHANNEL = "123456789012345678"
DATABASE = "11111111-1111-4111-8111-111111111111"
SOURCE = "22222222-2222-4222-8222-222222222222"
PAGE = "33333333-3333-4333-8333-333333333333"


class LocalMockHTTPContracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.responses = []
        self.clients = []
        for target in ("socket.create_connection", "socket.socket.connect", "socket.getaddrinfo"):
            self.enterContext(patch(target, side_effect=AssertionError("Live networking forbidden")))
        self.factory = self.enterContext(patch.object(
            http.httpx, "AsyncClient", side_effect=self.make_http_client,
        ))

    def make_http_client(self, **kwargs):
        self.assertIs(kwargs["trust_env"], False)
        self.assertIs(kwargs["follow_redirects"], False)
        client = REAL_ASYNC_CLIENT(transport=httpx.MockTransport(self.handle), **kwargs)
        self.clients.append(client)
        return client

    def handle(self, request):
        self.requests.append(request)
        self.assertTrue(self.responses, f"Unexpected mock request: {request.method} {request.url}")
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def tearDown(self):
        self.assertEqual(self.responses, [], "Planned mock responses were not consumed")
        self.assertTrue(all(client.is_closed for client in self.clients))

    def respond(self, payload, status=200, **kwargs):
        self.responses.append(httpx.Response(status, json=payload, **kwargs))

    def source_schema(self):
        self.respond({"object": "data_source", "id": SOURCE, "properties": {
            "Work title": {"type": "title"}, "Notes": {"type": "rich_text"},
        }})

    def make_service(self, name):
        if name == "slack":
            return slack.SlackClient(slack.SlackConfig(TOKEN, "C123"))
        if name == "discord":
            return discord.DiscordClient(discord.DiscordConfig(TOKEN, CHANNEL))
        if name == "jira":
            return jira.JiraClient(jira.JiraConfig(
                "https://tenant.example.invalid", TOKEN, "DEMO",
                email="bot@example.invalid", issue_type="Bug",
            ))
        return notion.NotionClient(notion.NotionConfig(TOKEN, data_source_id=SOURCE))

    async def invoke(self, name, client):
        if name in ("slack", "discord"):
            return await client.send_message("fixture message")
        if name == "jira":
            return await client.create_issue("fixture summary")
        self.source_schema()
        # Source lookup precedes the queued creation response.
        self.responses.insert(0, self.responses.pop())
        return await client.create_page("fixture title")

    async def test_slack_posts_json_and_exposes_server_timestamp_with_bool_compatibility(self):
        client = self.make_service("slack")
        self.respond({"ok": True, "ts": "1700000000.123456", "channel": "C123"})
        self.assertIs(await client.send_message("hello \u4e16\u754c"), True)
        self.assertEqual(client.last_message_id, "1700000000.123456")
        self.assertEqual(client.last_channel_id, "C123")
        request = self.requests[0]
        self.assertEqual((request.method, str(request.url)), ("POST", "https://slack.com/api/chat.postMessage"))
        self.assertEqual(json.loads(request.content), {"channel": "C123", "text": "hello \u4e16\u754c"})
        self.assertEqual(request.headers["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(request.headers["Content-Type"], "application/json")

    async def test_slack_api_errors_and_missing_confirmation_raise(self):
        for payload in ({"ok": False, "error": "invalid_auth"}, {"ok": False, "error": "missing_scope"},
                        {"ok": 1, "ts": "1.2", "channel": "C123"},
                        {"ok": True}, {"ok": True, "ts": "1.2"},
                        {"ok": True, "ts": "", "channel": "C123"}):
            with self.subTest(payload=payload):
                client = self.make_service("slack")
                self.respond(payload)
                with self.assertRaises(http.IntegrationError):
                    await client.send_message("hello")
                self.assertIsNone(client.last_message_id)
                self.assertIsNone(client.last_channel_id)

    async def test_slack_dm_uses_returned_channel(self):
        client = slack.SlackClient(slack.SlackConfig(TOKEN, "U123"))
        self.respond({"ok": True, "ts": "1700000000.654321", "channel": "D123"})
        self.assertIs(await client.send_message("hello"), True)
        self.assertEqual(client.last_channel_id, "D123")

    async def test_discord_posts_bot_auth_and_exposes_server_id(self):
        client = self.make_service("discord")
        self.respond({"id": "987654321098765432", "channel_id": CHANNEL})
        self.assertIs(await client.send_message("hello"), True)
        self.assertEqual(client.last_message_id, "987654321098765432")
        request = self.requests[0]
        self.assertEqual((request.method, str(request.url)),
                         ("POST", f"https://discord.com/api/v10/channels/{CHANNEL}/messages"))
        self.assertEqual(request.headers["Authorization"], f"Bot {TOKEN}")
        self.assertEqual(json.loads(request.content), {"content": "hello"})

    async def test_discord_invalid_success_payloads_raise(self):
        for payload in ({}, {"id": 123, "channel_id": CHANNEL},
                        {"id": "123"}, {"id": "123", "channel_id": "999"}):
            with self.subTest(payload=payload):
                client = self.make_service("discord")
                self.respond(payload)
                with self.assertRaises(http.IntegrationError):
                    await client.send_message("hello")
                self.assertIsNone(client.last_message_id)

    async def test_message_failure_clears_previous_identifier(self):
        for name in ("slack", "discord"):
            with self.subTest(service=name):
                client = self.make_service(name)
                client.last_message_id = "previous-fixture-id"
                self.respond({}, 403)
                with self.assertRaises(http.IntegrationError):
                    await client.send_message("hello")
                self.assertIsNone(client.last_message_id)

    async def test_jira_posts_basic_auth_adf_and_returns_real_id_key(self):
        client = self.make_service("jira")
        self.respond({"id": "10042", "key": "DEMO-42", "self": "fixture-url"}, 201)
        result = await client.create_issue("Summary", "First\n\nLast")
        self.assertEqual(result, {"id": "10042", "key": "DEMO-42", "self": "fixture-url", "summary": "Summary"})
        request = self.requests[0]
        self.assertEqual((request.method, str(request.url)),
                         ("POST", "https://tenant.example.invalid/rest/api/3/issue"))
        auth = base64.b64encode(f"bot@example.invalid:{TOKEN}".encode()).decode()
        self.assertEqual(request.headers["Authorization"], f"Basic {auth}")
        self.assertEqual(json.loads(request.content), {"fields": {
            "project": {"key": "DEMO"}, "issuetype": {"name": "Bug"},
            "summary": "Summary", "description": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "First"}]},
                {"type": "paragraph", "content": []},
                {"type": "paragraph", "content": [{"type": "text", "text": "Last"}]},
            ]},
        }})

    async def test_jira_empty_description_omitted_and_base_path_preserved(self):
        client = self.make_service("jira")
        client.config.server += "/jira/"
        self.respond({"id": "10042", "key": "DEMO-42"}, 201)
        await client.create_issue("Summary")
        self.assertEqual(self.requests[0].url.path, "/jira/rest/api/3/issue")
        self.assertNotIn("description", json.loads(self.requests[0].content)["fields"])

    async def test_jira_missing_id_or_key_rejected(self):
        for payload in ({}, {"id": "10042"}, {"key": "DEMO-42"}, {"id": 10042, "key": "DEMO-42"}):
            with self.subTest(payload=payload):
                self.respond(payload, 201)
                with self.assertRaises(http.IntegrationError):
                    await self.make_service("jira").create_issue("Summary")

    async def test_jira_missing_email_or_type_is_explicitly_unsupported(self):
        for field in ("email", "issue_type"):
            with self.subTest(field=field):
                client = self.make_service("jira")
                setattr(client.config, field, "")
                with self.assertRaisesRegex(NotImplementedError, field):
                    await client.create_issue("Summary")
        self.factory.assert_not_called()

    async def test_jira_invalid_base_urls_fail_before_http(self):
        for server in ("http://example.invalid", "https://name:secret@example.invalid",
                       "https://example.invalid?token=secret", "https://example.invalid#x", "relative"):
            with self.subTest(server=server):
                client = self.make_service("jira")
                client.config.server = server
                with self.assertRaises(ValueError):
                    await client.create_issue("Summary")
        self.factory.assert_not_called()

    async def test_notion_discovers_source_and_actual_title_property(self):
        client = notion.NotionClient(notion.NotionConfig(TOKEN, DATABASE))
        self.respond({"object": "database", "data_sources": [{"id": SOURCE}]})
        self.source_schema()
        self.respond({"object": "page", "id": PAGE, "url": "fixture-page-url"})
        result = await client.create_page("Title", "Body")
        self.assertEqual(result, {"object": "page", "id": PAGE, "url": "fixture-page-url", "title": "Title"})
        self.assertEqual([(r.method, str(r.url)) for r in self.requests], [
            ("GET", f"https://api.notion.com/v1/databases/{DATABASE}"),
            ("GET", f"https://api.notion.com/v1/data_sources/{SOURCE}"),
            ("POST", "https://api.notion.com/v1/pages"),
        ])
        for request in self.requests:
            self.assertEqual(request.headers["Authorization"], f"Bearer {TOKEN}")
            self.assertEqual(request.headers["Notion-Version"], "2025-09-03")
        self.assertEqual(json.loads(self.requests[-1].content), {
            "parent": {"data_source_id": SOURCE},
            "properties": {"Work title": {"title": [{"type": "text", "text": {"content": "Title"}}]}},
            "children": [{"object": "block", "type": "paragraph", "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Body"}}],
            }}],
        })

    async def test_notion_explicit_source_skips_database_and_empty_children(self):
        self.source_schema()
        self.respond({"object": "page", "id": PAGE})
        result = await self.make_service("notion").create_page("Title")
        self.assertEqual(result["id"], PAGE)
        self.assertEqual(len(self.requests), 2)
        self.assertNotIn("children", json.loads(self.requests[-1].content))

    async def test_notion_explicit_source_disambiguates_database(self):
        client = notion.NotionClient(notion.NotionConfig(TOKEN, DATABASE, SOURCE))
        self.respond({"object": "database", "data_sources": [{"id": SOURCE}, {"id": PAGE}]})
        self.source_schema()
        self.respond({"object": "page", "id": PAGE})
        await client.create_page("Title")
        self.assertEqual(json.loads(self.requests[-1].content)["parent"], {"data_source_id": SOURCE})

    async def test_notion_ambiguous_database_never_creates_page(self):
        for sources in ([], [{"id": SOURCE}, {"id": PAGE}]):
            with self.subTest(sources=sources):
                self.respond({"object": "database", "data_sources": sources})
                client = notion.NotionClient(notion.NotionConfig(TOKEN, DATABASE))
                with self.assertRaisesRegex(NotImplementedError, "data_source_id"):
                    await client.create_page("Title")
        self.assertTrue(all(r.method == "GET" for r in self.requests))

    async def test_notion_mismatched_source_never_creates_page(self):
        self.respond({"object": "database", "data_sources": [{"id": PAGE}]})
        client = notion.NotionClient(notion.NotionConfig(TOKEN, DATABASE, SOURCE))
        with self.assertRaisesRegex(ValueError, "does not belong"):
            await client.create_page("Title")
        self.assertEqual(len(self.requests), 1)

    async def test_notion_bad_database_response_never_creates_page(self):
        for payload in ({}, {"object": "database", "data_sources": [None]},
                        {"object": "database", "data_sources": [{}]}):
            with self.subTest(payload=payload):
                self.respond(payload)
                client = notion.NotionClient(notion.NotionConfig(TOKEN, DATABASE))
                with self.assertRaises(http.IntegrationError):
                    await client.create_page("Title")
        self.assertTrue(all(r.method == "GET" for r in self.requests))

    async def test_notion_unsupported_title_schema_never_creates_page(self):
        for props in ({}, {"A": {"type": "title"}, "B": {"type": "title"}}):
            with self.subTest(properties=props):
                self.respond({"object": "data_source", "properties": props})
                with self.assertRaisesRegex(NotImplementedError, "title property"):
                    await self.make_service("notion").create_page("Title")
        self.assertTrue(all(r.method == "GET" for r in self.requests))

    async def test_notion_invalid_schema_raises(self):
        self.respond({"object": "data_source", "properties": []})
        with self.assertRaises(http.IntegrationError):
            await self.make_service("notion").create_page("Title")

    async def test_notion_bad_page_response_raises(self):
        for payload in ({"object": "page"}, {"object": "error", "id": PAGE},
                        {"object": "page", "id": ""}):
            with self.subTest(payload=payload):
                self.source_schema()
                self.respond(payload)
                with self.assertRaises(http.IntegrationError):
                    await self.make_service("notion").create_page("Title")

    async def test_notion_long_content_is_preserved_without_truncation(self):
        content = "x" * 2000 + "\u4e16\u754c"
        self.source_schema()
        self.respond({"object": "page", "id": PAGE})
        await self.make_service("notion").create_page("Title", content)
        children = json.loads(self.requests[-1].content)["children"]
        chunks = [b["paragraph"]["rich_text"][0]["text"]["content"] for b in children]
        self.assertEqual([len(chunk) for chunk in chunks], [2000, 2])
        self.assertEqual("".join(chunks), content)

    async def test_notion_lookup_http_failure_stops_before_creation(self):
        for config in (notion.NotionConfig(TOKEN, DATABASE), notion.NotionConfig(TOKEN, data_source_id=SOURCE)):
            self.respond({}, 403)
            with self.assertRaises(http.IntegrationError):
                await notion.NotionClient(config).create_page("Title")
        self.assertTrue(all(r.method == "GET" for r in self.requests))

    async def test_all_clients_reject_http_errors_and_redirects_without_retry(self):
        for name in ("slack", "discord", "jira", "notion"):
            for status in (301, 302, 307, 400, 401, 403, 404, 422, 429, 500, 503):
                with self.subTest(service=name, status=status):
                    before = len(self.requests)
                    self.respond({"error": TOKEN}, status, headers={"Retry-After": "2", "Location": "https://unused.invalid"})
                    with self.assertRaises(http.IntegrationError) as caught:
                        await self.invoke(name, self.make_service(name))
                    self.assertEqual(caught.exception.status_code, status)
                    self.assertEqual(caught.exception.retry_after, "2")
                    self.assertNotIn(TOKEN, str(caught.exception))
                    self.assertEqual(len(self.requests) - before, 2 if name == "notion" else 1)

    async def test_all_clients_reject_unexpected_success_statuses(self):
        for name in ("slack", "discord", "jira", "notion"):
            for status in (202, 204):
                with self.subTest(service=name, status=status):
                    self.respond({"id": "unconfirmed"}, status)
                    with self.assertRaises(http.IntegrationError):
                        await self.invoke(name, self.make_service(name))

    async def test_all_clients_reject_malformed_json(self):
        for name in ("slack", "discord", "jira", "notion"):
            with self.subTest(service=name):
                self.responses.append(httpx.Response(201 if name == "jira" else 200, content=b"<html>bad response</html>"))
                with self.assertRaisesRegex(http.IntegrationError, "invalid JSON"):
                    await self.invoke(name, self.make_service(name))

    async def test_all_clients_reject_nonobject_json(self):
        for name in ("slack", "discord", "jira", "notion"):
            for payload in ([], None, True, "success"):
                with self.subTest(service=name, payload=payload):
                    self.responses.append(httpx.Response(
                        201 if name == "jira" else 200, content=json.dumps(payload).encode(),
                    ))
                    with self.assertRaisesRegex(http.IntegrationError, "JSON object"):
                        await self.invoke(name, self.make_service(name))

    async def test_all_clients_handle_timeout_and_transport_failure_without_retry(self):
        for name in ("slack", "discord", "jira", "notion"):
            for error in (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError):
                with self.subTest(service=name, error=error.__name__):
                    before = len(self.requests)
                    self.responses.append(error(TOKEN))
                    with self.assertRaisesRegex(http.IntegrationError, "outcome unknown") as caught:
                        await self.invoke(name, self.make_service(name))
                    self.assertNotIn(TOKEN, str(caught.exception))
                    self.assertEqual(len(self.requests) - before, 2 if name == "notion" else 1)

    async def test_defaults_and_missing_credentials_never_reach_http(self):
        for name, client in (("slack", slack.SlackClient()), ("discord", discord.DiscordClient()),
                             ("jira", jira.JiraClient()), ("notion", notion.NotionClient())):
            with self.subTest(service=name):
                method = client.send_message if name in ("slack", "discord") else (
                    client.create_issue if name == "jira" else client.create_page
                )
                with self.assertRaisesRegex(NotImplementedError, "unsupported configuration"):
                    await method("Title")
        self.factory.assert_not_called()

    async def test_each_required_configuration_field_is_checked_before_http(self):
        fields = {"slack": ("token", "channel"), "discord": ("token", "channel_id"),
                  "jira": ("server", "token", "project", "email", "issue_type"), "notion": ("token",)}
        for name, names in fields.items():
            for field in names:
                with self.subTest(service=name, field=field):
                    client = self.make_service(name)
                    setattr(client.config, field, " ")
                    method = client.send_message if name in ("slack", "discord") else (
                        client.create_issue if name == "jira" else client.create_page
                    )
                    with self.assertRaisesRegex(NotImplementedError, field):
                        await method("Title")
        with self.assertRaisesRegex(NotImplementedError, "database_id"):
            await notion.NotionClient(notion.NotionConfig(TOKEN)).create_page("Title")
        self.factory.assert_not_called()

    async def test_invalid_text_and_limits_fail_before_http(self):
        for name, limit in (("slack", 40000), ("discord", 2000), ("jira", 255), ("notion", 2000)):
            for value in ("", " ", None, 123, "x" * (limit + 1)):
                with self.subTest(service=name, value_type=type(value).__name__):
                    client = self.make_service(name)
                    method = client.send_message if name in ("slack", "discord") else (
                        client.create_issue if name == "jira" else client.create_page
                    )
                    with self.assertRaises(ValueError):
                        await method(value)
        self.factory.assert_not_called()

    async def test_optional_content_types_and_limits_fail_before_http(self):
        for value in (None, 123, "x" * 200001):
            with self.assertRaises(ValueError):
                await self.make_service("notion").create_page("Title", value)
        for value in (None, 123, "x" * 32768):
            with self.assertRaises(ValueError):
                await self.make_service("jira").create_issue("Title", value)
        self.factory.assert_not_called()

    async def test_discord_invalid_channel_fails_before_http(self):
        for channel in ("name", "12/34", "\uff11\uff12"):
            with self.subTest(channel=channel):
                client = discord.DiscordClient(discord.DiscordConfig(TOKEN, channel))
                with self.assertRaises(ValueError):
                    await client.send_message("hello")
        self.factory.assert_not_called()

    async def test_invalid_timeout_fails_before_http(self):
        for name in ("slack", "discord", "jira", "notion"):
            for timeout in (None, True, 0, -1, float("inf"), float("nan"), "15"):
                with self.subTest(service=name, timeout=timeout):
                    client = self.make_service(name)
                    client.config.timeout = timeout
                    method = client.send_message if name in ("slack", "discord") else (
                        client.create_issue if name == "jira" else client.create_page
                    )
                    with self.assertRaisesRegex(ValueError, "timeout"):
                        await method("Title")
        self.factory.assert_not_called()

    async def test_configurable_timeout_reaches_httpx(self):
        client = self.make_service("slack")
        client.config.timeout = 2.5
        self.respond({"ok": True, "ts": "1700000000.123456", "channel": "C123"})
        await client.send_message("hello")
        self.assertEqual(self.requests[0].extensions["timeout"],
                         {"connect": 2.5, "read": 2.5, "write": 2.5, "pool": 2.5})

    async def test_notion_blank_database_with_explicit_source_is_unsupported(self):
        client = notion.NotionClient(notion.NotionConfig(TOKEN, " ", SOURCE))
        with self.assertRaisesRegex(NotImplementedError, "database_id"):
            await client.create_page("Title")
        self.factory.assert_not_called()

    async def test_cancellation_propagates_and_closes_http_clients(self):
        for name in ("slack", "discord", "jira", "notion"):
            with self.subTest(service=name):
                self.responses.append(asyncio.CancelledError())
                with self.assertRaises(asyncio.CancelledError):
                    await self.invoke(name, self.make_service(name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
