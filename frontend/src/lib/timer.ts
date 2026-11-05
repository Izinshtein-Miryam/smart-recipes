/** Finds "N דקות" / "N minutes" in a step; returns seconds or null. */
export function timerSeconds(step: string): number | null {
  const m = /(\d+)\s*(?:דקות|דקה|דק'|minutes?|mins?)/i.exec(step);
  return m?.[1] ? Number(m[1]) * 60 : null;
}

export function formatClock(total: number): string {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function beep(): void {
  try {
    const Ctx = window.AudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    osc.connect(ctx.destination);
    osc.frequency.value = 880;
    osc.start();
    osc.stop(ctx.currentTime + 0.6);
  } catch {
    /* audio unavailable */
  }
}
