import { Link } from "react-router-dom";
import { SiteHeader } from "@/components/site-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";

const HELLOS = [
  { word: "Hola", className: "lb1" },
  { word: "Hello", className: "lb2" },
  { word: "Olá", className: "lb3" },
  { word: "Bonjour", className: "lb4" },
  { word: "Ciao", className: "lb5" },
  { word: "こんにちは", className: "lb6" },
];

export function LandingPage() {
  return (
    <div className="stage flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto grid w-full max-w-6xl flex-1 content-center gap-10 px-6 py-12 lg:grid-cols-2 lg:items-center">
        <section className="space-y-6">
          <Badge tone="signal">Open source</Badge>
          <h1 className="text-5xl font-semibold leading-[0.95] tracking-tight sm:text-7xl">
            Every <span className="text-accent">voice.</span>
            <br />
            Every <span className="text-accent">language.</span>
            <br />
            Everyone included.
          </h1>
          <p className="max-w-xl text-lg text-muted">
            Real-time transcription and multilingual captions for live events.
            File, microphone, or a public YouTube URL. The audience never sees
            the engine.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/events" className={buttonVariants({ size: "lg" })}>
              Explore live events
            </Link>
            <Link
              to="/setup"
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              Open organizer setup
            </Link>
          </div>
        </section>
        <div
          className="hero-visual relative mx-auto grid min-h-[350px] w-full max-w-md place-items-center overflow-hidden"
          aria-label="Multilingual live signal"
        >
          {HELLOS.map((item) => (
            <span key={item.word} className={`lang-bubble ${item.className}`}>
              {item.word}
            </span>
          ))}
          <div className="hero-globe relative grid place-items-center">
            <div className="hero-orbit" aria-hidden />
            <div className="hero-wave relative z-10 flex items-end gap-1" aria-hidden>
              {Array.from({ length: 7 }).map((_, index) => (
                <i key={index} />
              ))}
            </div>
          </div>
        </div>
      </main>
      <footer className="mt-auto border-t border-line">
        <div className="mx-auto grid w-full max-w-6xl gap-4 px-6 py-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-t border-line pt-4">
            <p className="text-[13px] font-medium">Live transcription</p>
            <p className="text-xs text-muted">Speech → captions</p>
          </div>
          <div className="border-t border-line pt-4">
            <p className="text-[13px] font-medium">Multilingual translation</p>
            <p className="text-xs text-muted">EN · ES · PT</p>
          </div>
          <div className="border-t border-line pt-4">
            <p className="text-[13px] font-medium">Open source</p>
            <p className="text-xs text-muted">Self-hostable</p>
          </div>
          <div className="border-t border-line pt-4">
            <p className="text-[13px] font-medium">Built for events</p>
            <p className="text-xs text-muted">Web · OBS · vMix</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
