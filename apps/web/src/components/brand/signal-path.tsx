export function SignalPath({ className = "h-10 w-full" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 320 40"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2 20 H48 C56 20 60 8 72 8 C84 8 88 32 100 32 C112 32 116 20 132 20 H188 C196 20 200 6 214 6 C228 6 232 34 246 34 C260 34 264 20 318 20"
        stroke="#22D3EE"
        strokeWidth="1.5"
        opacity="0.9"
      />
      <circle cx="72" cy="8" r="2.4" fill="#8B5CF6" />
      <circle cx="214" cy="6" r="2.4" fill="#F43F5E" />
      <circle cx="246" cy="34" r="2.4" fill="#34D399" />
    </svg>
  );
}
