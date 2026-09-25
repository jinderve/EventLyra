export function EventLyraLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 36 36"
      role="img"
      aria-label="EventLyra signal logo"
      className={className}
    >
      <defs>
        <linearGradient id="eventlyra-signal" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#8B5CF6" />
          <stop offset="1" stopColor="#22D3EE" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="34" height="34" rx="10" fill="#0c1119" stroke="#2a3650" />
      <path
        d="M7 19h3m2-5v10m3-15v18m3-12v6m3-10v14m3-8v4m3-3h3"
        fill="none"
        stroke="url(#eventlyra-signal)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
