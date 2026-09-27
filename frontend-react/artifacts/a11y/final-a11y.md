# Final Accessibility Audit

- Scans: 104
- Routes: 26
- Themes: light, dark
- Viewports: 1440px, 390px
- Total violation nodes: 403
- Blocking violations: 10

## Blocking Findings

- chat / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- factory / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- tasks / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- task-history / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- reasoning / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- reasoning-history / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- workflows / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- scheduler / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- terminal / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack
- cluster / light / 1440px: scrollable-region-focusable (serious)
  - vite-error-overlay,.stack

## Rule Summary

  region x210 impact=moderate wcag=best-practice
        h2
        p
        vite-error-overlay,.window
  landmark-one-main x91 impact=moderate wcag=best-practice
        html
  page-has-heading-one x91 impact=moderate wcag=best-practice
        html
  scrollable-region-focusable x10 impact=serious wcag=wcag2a, wcag211, wcag213
        vite-error-overlay,.stack
  heading-order x1 impact=moderate wcag=best-practice
        h3

Raw data: `a11y-report.json`
