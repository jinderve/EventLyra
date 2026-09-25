import { Navigate, Route, Routes } from "react-router-dom";
import { LandingPage } from "@/pages/landing";
import { EventsPage } from "@/pages/events";
import { LivePage } from "@/pages/live";
import { OverlayPage } from "@/pages/overlay";
import { WatchPage } from "@/pages/watch";
import { WatchLobbyPage } from "@/pages/watch-lobby";
import { SetupLayout } from "@/pages/setup/layout";
import { SetupEventPage } from "@/pages/setup/event";
import { SetupSessionsPage } from "@/pages/setup/sessions";
import { SetupLanguagesPage } from "@/pages/setup/languages";
import { SetupAudioPage } from "@/pages/setup/audio";
import { SetupGoPage } from "@/pages/setup/go";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/events" element={<EventsPage />} />
      <Route path="/setup" element={<SetupLayout />}>
        <Route index element={<Navigate to="event" replace />} />
        <Route path="event" element={<SetupEventPage />} />
        <Route path="sessions" element={<SetupSessionsPage />} />
        <Route path="languages" element={<SetupLanguagesPage />} />
        <Route path="audio" element={<SetupAudioPage />} />
        <Route path="go" element={<SetupGoPage />} />
      </Route>
      <Route path="/live" element={<LivePage />} />
      <Route path="/watch" element={<WatchLobbyPage />} />
      <Route path="/watch/:sessionId" element={<WatchPage />} />
      <Route path="/overlay/:sessionId" element={<OverlayPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
