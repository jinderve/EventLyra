import { NavLink, Outlet } from "react-router-dom";
import { SiteHeader } from "@/components/site-header";
import { cn } from "@/lib/utils";

const STEPS = [
  { to: "/setup/event", label: "Event" },
  { to: "/setup/sessions", label: "Sessions" },
  { to: "/live", label: "Live desk" },
];

export function SetupLayout() {
  return (
    <div className="stage min-h-screen">
      <SiteHeader />
      <aside className="sticky top-[57px] z-10 border-b border-line bg-[#090c12]/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-6 overflow-x-auto px-6 py-4">
          <p className="shrink-0 text-xs tracking-[0.2em] text-muted">SETUP</p>
          <nav className="flex gap-1" aria-label="Organizer setup">
            {STEPS.map((step, index) => (
              <NavLink
                key={step.to}
                to={step.to}
                className={({ isActive }) =>
                  cn(
                    "whitespace-nowrap rounded-control border border-line px-3 py-2 text-sm",
                    isActive ? "bg-white/10 text-ink" : "text-muted hover:text-ink",
                  )
                }
              >
                <span className="mr-2 text-primary">{index + 1}</span>
                {step.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
}
