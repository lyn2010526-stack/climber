# Round 8 Task 04: Plugins And Settings Integration

- Status: read-only research; plugin and settings pages are occupied.
- Mature source evidence: Dify `workflow/run/index.tsx:47-90` scopes fetches to URL inputs and reloads result/tracing data when the active run changes. This is the applicable integration pattern for plugin/settings selection changes.
- Climber evidence: `PluginsPage.tsx:83-145` uses real list/install/uninstall/enable/disable/import API calls, serializes actions through `actionLoading`, and restores dialog focus. `SettingsPage.tsx:30-107` maps sections to embedded credential/token pages; `:166-180` begins profile loading through the API.
- Finding: integration boundaries are present. The main review risk is duplicated plugin surfaces: `PluginPage.tsx` and `PluginsPage.tsx` both call the same plugin APIs with different state models.
- Test: source inspection only; existing candidate is `src/pages/__tests__/PluginAndOperationsPages.taskB.test.tsx` and `SettingsPage.credentials.test.tsx`.
- Risk: consolidating the duplicate surfaces can change route behavior and API payload assumptions; keep route-level compatibility until ownership is clear.
