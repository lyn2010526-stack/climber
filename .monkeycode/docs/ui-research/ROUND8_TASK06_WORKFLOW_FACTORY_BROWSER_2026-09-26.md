# Round 8 Task 06: Workflow And Factory Browser Acceptance

- Status: source-level acceptance research; browser execution was intentionally skipped because the user requested no full build and implementation files are occupied.
- Mature source evidence: OpenHands `chat-interface-wrapper.tsx:37-71` demonstrates independent main/auxiliary layout boundaries. Dify `workflow/run/index.tsx:104-184` demonstrates stable tabbed run inspection with an independently scrolling content region.
- Climber evidence: `WorkflowsPage.tsx:41-87` loads, runs, edits, saves, and reports workflow results; `WorkflowEditor.tsx:57-153` handles connection, drop, node selection, save, and run. `FactoryModePage.tsx:137-173` loads active agents/providers and recent runs, while cleanup stops the stream on unmount.
- Acceptance matrix researched: workflow list error/retry/empty states at `WorkflowsPage.tsx:111-137`; workflow result rendering begins after `:139`; factory configuration loading/error begins at `FactoryModePage.tsx:137-149`; stream cleanup is `:165-173`.
- Test: source inspection only. Existing candidates include `FactoryModePage.test.tsx`; browser visual acceptance remains pending.
- Risk: visual browser claims require a running API and current parallel snapshot. Do not mark this task browser-accepted from static evidence.
