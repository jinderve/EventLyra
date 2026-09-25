import { Link } from "react-router-dom";
import { SessionBoard } from "@/components/session-board";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";

export function LivePage() {
  return (
    <div className="stage min-h-screen">
      <SiteHeader />
      <main className="mx-auto min-h-screen max-w-5xl px-6 py-8">
        <div className="mb-6 flex flex-wrap gap-3">
          <Link to="/setup/sessions" className={buttonVariants({ variant: "ghost" })}>
            Back to setup
          </Link>
          <Link to="/events" className={buttonVariants({ variant: "outline" })}>
            Audience events
          </Link>
        </div>
        <SessionBoard variant="live" />
      </main>
    </div>
  );
}
