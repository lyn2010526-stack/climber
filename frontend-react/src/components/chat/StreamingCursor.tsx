/**
 * 流式光标：呼吸动画。
 *
 * keyframes 随组件自带（index.css 归样式契约任务所有）：名称唯一的
 * keyframes 在多实例渲染时由浏览器按名去重，重复声明无害。
 * prefers-reduced-motion 由全局规则统一把动画时长压到 0.01ms，此处无需分支。
 */
const BREATHE_KEYFRAMES =
  '@keyframes climberCursorBreathe{0%,100%{opacity:1;transform:scaleY(1)}50%{opacity:.35;transform:scaleY(.8)}}';

export function StreamingCursor() {
  return (
    <>
      <style>{BREATHE_KEYFRAMES}</style>
      <span
        data-cursor-bar
        aria-hidden="true"
        className="ml-0.5 inline-block h-[1.1em] w-[2px] origin-bottom rounded-full align-middle will-change-[opacity,transform]"
        style={{
          backgroundColor: 'var(--color-accent-foreground)',
          animation: 'climberCursorBreathe 1.4s ease-in-out infinite',
        }}
      />
    </>
  );
}

export function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{
            backgroundColor: 'var(--color-text-muted)',
            animation: `bounce 1.4s ease-in-out ${i * 0.16}s infinite`,
          }}
        />
      ))}
    </span>
  );
}
