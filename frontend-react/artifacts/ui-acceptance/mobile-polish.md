# Mobile Polish Acceptance

Run command:

```bash
npx playwright test mobile-polish.mobile.spec.ts --project=mobile
```

Matrix: 390x844, 375x812, and 768x1024. Each case checks the chat composer, draft retention after a viewport resize, single-column document geometry, and minimum 44px interactive targets. The related unit suite covers visual viewport keyboard clamping, safe-area reserve, focus restoration, IME behavior, send/stop, error retry, and desktop fallback rendering.

Chromium run: 6 tests passed across 390x844, 375x812, and 768x1024. The 768x1024 boundary cases verify the desktop shell is present and visible. The command remains the reproducible acceptance entry point.

Typecheck result: passed with `npm run typecheck`.

Build result: passed with `npm run build`.
