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
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: 'var(--text-secondary)',
                animation: `bounce 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
        <style>{`
          @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-6px); }
          }
        `}</style>
      </div>
    </div>
  )
}
