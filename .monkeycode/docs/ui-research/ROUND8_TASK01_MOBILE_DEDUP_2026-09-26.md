# Round 8 Task 01: Mobile Pages And Components

- Status: read-only research; implementation files were occupied by parallel changes.
- Mature source evidence: OpenHands `chat-interface-wrapper.tsx:17-45` keeps the thread `min-w-0`, `min-h-0`, and `flex-1`; this prevents auxiliary columns from squeezing the chat surface. Climber `MobileChatPage.tsx:12-43` owns viewport-height reconciliation while `MobileChatInterface.tsx:41-60` owns message/input resizing and follow-output behavior.
- Climber evidence: `MobileChatPage.tsx:45-69` owns session send/stop/cache wiring. `MobileChatInterface.tsx:62-79` owns submission locking and error restoration. `LazyImage.tsx:11-65` owns image visibility/loading, while `useOnlineStatus` and `cacheManager` are separate concerns in the same file.
- Finding: page orchestration and component interaction responsibilities are already separated. The remaining duplication risk is duplicated mobile shell/height logic across `AdaptiveMobileLayout`, `MobileChatPage`, and `MobileChatInterface`; extraction should wait until occupied files are free.
- Test: source inspection only; no full build. Existing focused candidates are `src/components/mobile/MobileChatInterface.test.tsx` and `src/pages/mobile/__tests__/MobileChatPage.test.tsx`.
- Risk: editing occupied mobile files could overwrite active IME, safe-area, or streaming fixes. Recheck after the owning agent releases them.
