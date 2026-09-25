const TAB_ID = crypto.randomUUID();

export async function claimSession(sessionId: string): Promise<boolean> {
  const locks = navigator.locks;
  if (!locks) return true;
  const name = `eventlyra-session-${sessionId}`;
  return new Promise((resolve) => {
    void locks.request(name, { ifAvailable: true }, async (lock) => {
      if (!lock) {
        resolve(false);
        return;
      }
      sessionStorage.setItem(`eventlyra.tab.${sessionId}`, TAB_ID);
      resolve(true);
      await new Promise<void>(() => undefined);
    });
  });
}
