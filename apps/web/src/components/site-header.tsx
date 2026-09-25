import { Link, useLocation } from "react-router-dom";
import { EventLyraLogo } from "@/components/eventlyra-logo";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const LINKS = [
  { to: "/", label: "Home", match: (path: string) => path === "/" },
  {
    to: "/events",
    label: "Events",
    match: (path: string) => path.startsWith("/events") || path.startsWith("/watch"),
  },
  {
    to: "/setup",
    label: "For organizers",
    match: (path: string) => path.startsWith("/setup") || path.startsWith("/live"),
  },
];

const REPO_URL = "https://github.com/jinderve/EventLyra";

export function SiteHeader() {
  const { pathname } = useLocation();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-[#07090e]/82 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-3">
        <Link to="/" className="flex items-center gap-2.5 text-sm font-semibold tracking-tight">
          <EventLyraLogo className="h-[34px] w-[34px]" />
          <span>
            Event<span className="text-[#b89cff]">Lyra</span>
          </span>
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <nav className="flex flex-wrap gap-1" aria-label="Main">
            {LINKS.map((link) => (
              <Link
                key={`${link.to}-${link.label}`}
                to={link.to}
                aria-current={link.match(pathname) ? "page" : undefined}
                className={cn(
                  "h-10 rounded-control border px-3 text-sm leading-10",
                  link.match(pathname)
                    ? "border-[#25314a] bg-[#101624] text-ink"
                    : "border-transparent text-muted hover:bg-[#0d131d] hover:text-ink",
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants()}
          >
            GitHub ↗
          </a>
        </div>
      </div>
    </header>
  );
}
