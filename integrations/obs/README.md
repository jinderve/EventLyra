# OBS overlay

EventLyra does not ship an OBS plugin.

1. Add a **Browser Source**.
2. URL: `http://127.0.0.1:8000/overlay/1` (or `/overlay?sesion=1` on the legacy page).
3. Width 1920, height 1080.
4. Enable **Shutdown source when not visible** only if you accept the overlay reconnecting; the GPU session itself does not cancel on `pagehide`.

The page is transparent. Captions are the only chrome.
