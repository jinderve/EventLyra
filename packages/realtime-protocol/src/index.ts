/** SSE events for this cut. WebSocket may reuse the same names later. */
export const REALTIME_EVENTS = ["cue", "status"] as const;

export type RealtimeEventName = (typeof REALTIME_EVENTS)[number];
