export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-slide-up">
      <div
        className="px-4 py-3 rounded-2xl rounded-bl-md shadow-sm"
        style={{ backgroundColor: 'var(--bubble-ai)' }}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full typing-dot"
              style={{
                backgroundColor: 'var(--text-secondary)',
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
