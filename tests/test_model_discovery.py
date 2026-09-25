"""Isolated unittest suite: real service/router/SQL, mocked DNS and HTTP wire.

Run: python3 -m unittest discover -s tests -p test_model_discovery.py -v
No tests/conftest.py, shared database, real provider key or external request.
"""

# This suite deliberately avoids pytest and its shared-database conftest.
# ruff: noqa: PT009, PT027

import asyncio
import socket
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import model_discovery as routes
from app.core.api_key_crypto import encrypt_api_key
from app.core.principal import Principal, reset_current_principal, set_current_principal
from app.services import model_discovery as discovery
from app.storage.database import ApiKey


def addresses(*ips):
    return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, socket.SOCK_STREAM,
             socket.IPPROTO_TCP, '', (ip, 443)) for ip in ips]


class NetworkCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.responses = [httpx.Response(200, json={"data": [{"id": "model-test"}]})]
        self.dns = patch('socket.getaddrinfo', return_value=addresses('8.8.8.8')).start()
        self.addCleanup(patch.stopall)

        async def wire(request):
            self.requests.append(request)
            reply = self.responses.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

        self.wire = patch.object(httpx.AsyncHTTPTransport, 'handle_async_request', side_effect=wire).start()

    async def assert_error(self, code, provider='openai', key='user-test-key', base=None):
        with self.assertRaises(discovery.DiscoveryError) as caught:
            await discovery.discover_models(provider, key, base)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn('user-test-key', str(caught.exception))
        return caught.exception


class DiscoveryServiceTests(NetworkCase):
    async def test_openai_deduplicates_and_pins_dns_with_tls_hostname(self):
        self.responses = [httpx.Response(200, json={"data": [{"id": "z"}, {"id": "a"}, {"id": "z"}]})]
        result = await discovery.discover_models('openai', 'user-test-key', 'https://models.example/v1/')
        self.assertEqual([model['model_id'] for model in result['models']], ['a', 'z'])
        self.assertEqual(result['source'], 'provider_api')
        request = self.requests[0]
        self.assertEqual(request.url.host, '8.8.8.8')
        self.assertEqual(request.headers['host'], 'models.example')
        self.assertEqual(request.extensions['sni_hostname'], 'models.example')
        self.assertEqual(request.url.path, '/v1/models')
        self.assertEqual(request.headers['authorization'], 'Bearer user-test-key')
        self.assertEqual(self.dns.call_count, 1)

    async def test_anthropic_native_auth_and_pagination(self):
        self.responses = [
            httpx.Response(200, json={"data": [{"id": "a", "display_name": "Alpha"}], "has_more": True, "last_id": "a"}),
            httpx.Response(200, json={"data": [{"id": "b"}], "has_more": False}),
        ]
        result = await discovery.discover_models('anthropic', 'user-test-key', None)
        self.assertEqual(len(result['models']), 2)
        self.assertEqual(result['models'][0]['label'], 'Alpha')
        self.assertEqual(self.requests[1].url.params['after_id'], 'a')
        self.assertEqual(self.requests[0].headers['x-api-key'], 'user-test-key')
        self.assertEqual(self.requests[0].headers['anthropic-version'], '2023-06-01')
        self.assertNotIn('authorization', self.requests[0].headers)
        self.assertEqual(self.requests[0].url.path, '/v1/models')

    async def test_anthropic_saved_base_matches_existing_adapter_semantics(self):
        await discovery.discover_models('anthropic', 'user-test-key', 'https://provider.example/anthropic/')
        self.assertEqual(self.requests[0].url.path, '/anthropic/v1/models')

    async def test_google_pagination_and_generation_filter(self):
        self.responses = [
            httpx.Response(200, json={"models": [
                {"name": "models/generate-test", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/embed-test", "supportedGenerationMethods": ["embedContent"]},
            ], "nextPageToken": "next"}),
            httpx.Response(200, json={"models": []}),
        ]
        result = await discovery.discover_models('google', 'user-test-key', None)
        self.assertEqual([m['model_id'] for m in result['models']], ['generate-test'])
        self.assertEqual(self.requests[1].url.params['pageToken'], 'next')
        self.assertEqual(self.requests[0].headers['x-goog-api-key'], 'user-test-key')
        self.assertNotIn('key', self.requests[0].url.params)

    async def test_stepfun_compatible_endpoint(self):
        result = await discovery.discover_models('stepfun', 'user-test-key', None)
        self.assertEqual(result['provider'], 'stepfun')
        self.assertEqual(self.requests[0].headers['host'], 'api.stepfun.com')
        self.assertEqual(self.requests[0].url.path, '/v1/models')

    async def test_ollama_explicit_public_endpoint_without_key(self):
        self.responses = [httpx.Response(200, json={"models": [{"name": "local-test:latest"}]})]
        result = await discovery.discover_models('ollama', '', 'https://ollama.example')
        self.assertEqual(result['models'][0]['model_id'], 'local-test:latest')
        self.assertEqual(self.requests[0].url.path, '/api/tags')
        self.assertNotIn('authorization', self.requests[0].headers)

    async def test_missing_key_never_resolves_or_requests(self):
        with patch('os.getenv', side_effect=AssertionError('environment must not be queried')):
            await self.assert_error('missing_key', key=' ')
        self.dns.assert_not_called()
        self.wire.assert_not_called()

    async def test_unsupported_provider_and_missing_ollama_endpoint(self):
        await self.assert_error('unsupported_provider', provider='unsupported')
        await self.assert_error('missing_endpoint', provider='ollama', key='')
        self.wire.assert_not_called()

    async def test_empty_list_is_explicit_without_static_fallback(self):
        self.responses = [httpx.Response(200, json={"data": []})]
        result = await discovery.discover_models('openai', 'user-test-key', None)
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['models'], [])

    async def test_provider_failures_redact_response_body(self):
        for status, code in [(401, 'provider_auth_failed'), (403, 'provider_auth_failed'),
                             (429, 'rate_limited'), (404, 'discovery_unavailable'),
                             (405, 'discovery_unavailable'), (500, 'provider_error')]:
            with self.subTest(status=status):
                self.responses = [httpx.Response(status, text='user-test-key upstream secret')]
                await self.assert_error(code)

    async def test_request_timeout_and_network_failure(self):
        for exception, code in [(httpx.ReadTimeout('user-test-key'), 'timeout'),
                                (httpx.ConnectError('user-test-key'), 'network_error')]:
            with self.subTest(code=code):
                self.responses = [exception]
                await self.assert_error(code)

    async def test_total_timeout_includes_dns(self):
        async def wait_forever(*args, **kwargs):
            await asyncio.Event().wait()
        with patch.object(asyncio.get_running_loop(), 'getaddrinfo', side_effect=wait_forever), \
                patch.object(discovery, 'DISCOVERY_TIMEOUT', 0.01):
            await self.assert_error('timeout')
        self.wire.assert_not_called()

    async def test_invalid_payloads(self):
        for payload in [[], {}, {"data": None}, {"data": [None]}, {"data": [{"id": ""}]},
                        {"data": [{"id": 12}]}]:
            with self.subTest(payload=payload):
                self.responses = [httpx.Response(200, json=payload)]
                await self.assert_error('invalid_response')
        self.responses = [httpx.Response(200, content=b'not-json')]
        await self.assert_error('invalid_response')

    async def test_bounded_body_model_count_and_pagination(self):
        with patch.object(discovery, 'MAX_RESPONSE_BYTES', 4):
            await self.assert_error('response_too_large')
        self.responses = [httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})]
        with patch.object(discovery, 'MAX_MODELS', 1):
            await self.assert_error('response_too_large')
        self.responses = [httpx.Response(200, json={"data": [], "has_more": True, "last_id": "a"})]
        with patch.object(discovery, 'MAX_PAGES', 1):
            await self.assert_error('pagination_limit', provider='anthropic')

    async def test_repeated_or_missing_cursor_rejected(self):
        page = {"data": [], "has_more": True, "last_id": "same"}
        self.responses = [httpx.Response(200, json=page), httpx.Response(200, json=page)]
        await self.assert_error('invalid_response', provider='anthropic')
        self.responses = [httpx.Response(200, json={"data": [], "has_more": True})]
        await self.assert_error('invalid_response', provider='anthropic')

    async def test_unsafe_url_forms_rejected_before_dns(self):
        for url in ['http://localhost:11434', 'file:///etc/hosts', 'https://user:pass@example.com',
                    'https://example.com?key=secret', 'https://example.com#fragment']:
            with self.subTest(url=url):
                await self.assert_error('unsafe_endpoint', base=url)
        self.dns.assert_not_called()
        self.wire.assert_not_called()

    async def test_private_and_mixed_dns_fail_closed(self):
        for ips in [('127.0.0.1',), ('10.0.0.1',), ('169.254.169.254',), ('::1',),
                    ('8.8.8.8', '192.168.1.1'), ('224.0.0.1',), ('::ffff:127.0.0.1',)]:
            with self.subTest(ips=ips):
                self.dns.return_value = addresses(*ips)
                await self.assert_error('unsafe_endpoint')
        self.wire.assert_not_called()

    async def test_dns_failure_has_no_wire_fallback(self):
        self.dns.side_effect = socket.gaierror('unresolved')
        await self.assert_error('network_error')
        self.dns.side_effect = None
        self.dns.return_value = []
        await self.assert_error('network_error')
        self.wire.assert_not_called()

    async def test_redirect_never_followed(self):
        self.responses = [httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})]
        await self.assert_error('unsafe_redirect')
        self.assertEqual(len(self.requests), 1)

    async def test_invalid_pagination_metadata(self):
        self.responses = [httpx.Response(200, json={"data": [], "has_more": "false"})]
        await self.assert_error('invalid_response', provider='anthropic')
        self.responses = [httpx.Response(200, json={"models": [], "nextPageToken": 0})]
        await self.assert_error('invalid_response', provider='google')


class DiscoveryRouteTests(NetworkCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as connection:
            await connection.run_sync(ApiKey.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            session.add_all([
                ApiKey(id='mine', user_id='owner-a', provider='openai', name='Mine',
                       api_key_encrypted=encrypt_api_key('user-test-key')),
                ApiKey(id='other', user_id='owner-b', provider='openai', name='Other',
                       api_key_encrypted=encrypt_api_key('other-test-key')),
                ApiKey(id='inactive', user_id='owner-a', provider='openai', name='Disabled',
                       api_key_encrypted='unused', is_active=False),
                ApiKey(id='broken', user_id='owner-a', provider='openai', name='Unreadable',
                       api_key_encrypted='enc:v1:invalid'),
                ApiKey(id='empty', user_id='owner-a', provider='openai', name='Empty',
                       api_key_encrypted=''),
            ])
            await session.commit()
        patch.object(routes, 'async_session', self.sessions).start()
        self.token = set_current_principal(Principal(subject_id='owner-a'))
        app = FastAPI()
        app.include_router(routes.router, prefix='/api/v1')
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        reset_current_principal(self.token)
        await self.engine.dispose()

    async def test_owned_credential_real_query_decrypt_and_service(self):
        response = await self.client.get('/api/v1/models/discover', params={'credential_id': 'mine'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['credential_id'], 'mine')
        self.assertEqual(response.json()['models'][0]['model_id'], 'model-test')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('user-test-key', response.text)
        self.assertEqual(self.requests[0].headers['authorization'], 'Bearer user-test-key')

    async def test_other_inactive_and_absent_credentials_indistinguishable(self):
        bodies = []
        for credential in ['other', 'inactive', 'absent']:
            response = await self.client.get('/api/v1/models/discover', params={'credential_id': credential})
            self.assertEqual(response.status_code, 404)
            bodies.append(response.json())
        self.assertTrue(all(body == bodies[0] for body in bodies))
        self.wire.assert_not_called()

    async def test_unreadable_or_empty_key_never_calls_provider(self):
        for credential, code in [('broken', 'credential_unreadable'), ('empty', 'missing_key')]:
            response = await self.client.get('/api/v1/models/discover', params={'credential_id': credential})
            self.assertEqual(response.json()['detail']['code'], code)
        self.wire.assert_not_called()

    async def test_no_credential_id_rejected_by_route_validation(self):
        response = await self.client.get('/api/v1/models/discover')
        self.assertEqual(response.status_code, 422)
        self.wire.assert_not_called()

    async def test_provider_error_contract_uses_safe_code(self):
        self.responses = [httpx.Response(401, text='user-test-key')]
        response = await self.client.get('/api/v1/models/discover', params={'credential_id': 'mine'})
        self.assertEqual(response.status_code, 424)
        self.assertEqual(response.json()['detail']['code'], 'provider_auth_failed')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('user-test-key', response.text)

    async def test_switching_owner_uses_own_key_without_execution_cache(self):
        response = await self.client.get('/api/v1/models/discover', params={'credential_id': 'mine'})
        self.assertEqual(response.status_code, 200)
        token = set_current_principal(Principal(subject_id='owner-b'))
        try:
            denied = await self.client.get('/api/v1/models/discover', params={'credential_id': 'mine'})
            self.assertEqual(denied.status_code, 404)
            self.responses = [httpx.Response(200, json={"data": [{"id": "owner-b-model"}]})]
            own = await self.client.get('/api/v1/models/discover', params={'credential_id': 'other'})
            self.assertEqual(own.json()['models'][0]['model_id'], 'owner-b-model')
            self.assertEqual(self.requests[-1].headers['authorization'], 'Bearer other-test-key')
        finally:
            reset_current_principal(token)

    async def test_authenticated_mode_requires_a_principal(self):
        from app.core import principal

        token = principal.principal_context.set(None)
        try:
            with patch.object(principal.settings, 'enable_auth', True):
                response = await self.client.get('/api/v1/models/discover', params={'credential_id': 'mine'})
            self.assertEqual(response.status_code, 401)
            self.wire.assert_not_called()
        finally:
            principal.principal_context.reset(token)


if __name__ == '__main__':
    unittest.main()
