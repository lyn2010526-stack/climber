# Round 8 Task 02: Chat Input And Markdown States

- Status: read-only research; `ChatInterface.tsx`, `MarkdownRenderer.tsx`, and `MessageContent.tsx` are occupied.
- Mature source evidence: Cline `ChatView.tsx:415-432` places auto-approval, actions, queued prompts, and input in one footer. Chainlit `SubmitButton.tsx:27-70` makes loading plus first interaction render Stop, otherwise Send, with disabled and tooltip states.
- Climber evidence: `ChatInterface.tsx:134-155` already covers blank-send prevention, IME, Shift+Enter, 200px growth, and follow-output. `MarkdownRenderer.tsx:121-180` covers copy, line numbers, language labels, and horizontal code scrolling. `MessageContent.tsx:46-67` routes assistant content through Markdown and user content through preserved whitespace.
- Finding: the remaining state gap is behavior verification for streaming partial content, copy failure, and manual-scroll preservation. The current architecture matches the mature footer/state contracts.
- Test: source inspection only; focused existing suites include `src/components/chat/__tests__/MarkdownRenderer.toc.test.tsx` and `src/components/agent/ChatInterface.task03.test.tsx`.
- Risk: changing composer state while `useChat.ts` and chat components are occupied can reintroduce duplicate sends or lose partial output.
