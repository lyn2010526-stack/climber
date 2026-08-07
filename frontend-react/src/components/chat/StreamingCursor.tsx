export function StreamingCursor() {
  return (
    <span
      className="inline-block w-[2px] h-[1.1em] ml-0.5 rounded-full align-middle"
      style={{
        background: 'linear-gradient(180deg, var(--color-accent) 0%, #8B5CF6 100%)',
        animation: 'cursorBlink 1s step-end infinite',
      }}
    />
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
