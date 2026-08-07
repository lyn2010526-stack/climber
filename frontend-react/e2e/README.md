# E2E Tests

Playwright-based end-to-end tests for the Climber agent-engine frontend.

## Structure

```
e2e/
  helpers.ts              -- Shared utilities (navigation, API helpers)
  01-navigation.spec.ts   -- Navigation & dashboard tests
  02-agents.spec.ts       -- Agent CRUD flow tests
  03-chat.spec.ts         -- Chat & task execution tests
  04-dashboard.spec.ts    -- Dashboard & settings page tests
  05-mobile.spec.ts       -- Mobile responsive layout tests
```

## Running

```bash
# Run all tests (requires backend + frontend running)
npm run test:e2e

# Run with Playwright UI for debugging
npm run test:e2e:ui

# Run headed (visible browser)
npm run test:e2e:headed

# Run only chromium project
npx playwright test --project=chromium

# Run only mobile project
npx playwright test --project=mobile
```

## Prerequisites

1. Backend running on http://localhost:8000
2. Frontend running on http://localhost:5173

```bash
# Terminal 1: Backend
cd .. && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
npm run dev

# Terminal 3: Tests
npm run test:e2e
```

## Configuration

Edit `playwright.config.ts` to adjust:
- `baseURL` - Frontend URL (default: http://localhost:5173)
- `API_URL` - Backend URL (default: http://localhost:8000)
- `timeout` - Test timeout (default: 30s)
- `workers` - Parallel workers (default: 1)

## CI Integration

Tests run automatically on push/PR via `.github/workflows/ci.yml` (e2e-test job).

## Test Projects

| Project | Device | Coverage |
|---------|--------|----------|
| chromium | Desktop Chrome | All tests |
| mobile | Pixel 7 | Responsive tests |
