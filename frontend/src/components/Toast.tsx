/** Short status message, announced to screen readers via role="status". */
export function Toast({ message }: { message: string | null }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`bg-ink no-print pointer-events-none fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-[10px] px-4 py-2.5 text-white transition-opacity ${
        message ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {message}
    </div>
  );
}
