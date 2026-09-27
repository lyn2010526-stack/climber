"""HTTP-level tests for the API layer.

Every test in this package drives the real ASGI application through
``httpx.AsyncClient`` + ``ASGITransport``, so routing, middleware, dependency
injection, serialization and status codes are all exercised end to end. Assertions
check the real response status and the contract-bearing fields of the body.
"""
