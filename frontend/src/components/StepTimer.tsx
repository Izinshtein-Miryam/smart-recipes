import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { beep, formatClock } from '@/lib/timer';

/** Countdown for one step. Mounted per step by the parent, which keeps state in `remaining`. */
export function StepTimer({
  seconds,
  remaining,
  running,
  onChange,
}: {
  seconds: number;
  remaining: number;
  running: boolean;
  onChange: (remaining: number, running: boolean) => void;
}) {
  const { t } = useTranslation();
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      const next = remaining - 1;
      if (next <= 0) {
        setDone(true);
        beep();
        onChange(0, false);
      } else onChange(next, true);
    }, 1000);
    return () => clearInterval(id);
  }, [running, remaining, onChange]);

  const btn = 'border-line rounded-full border px-4 py-2 font-semibold';
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="font-mono text-3xl" aria-hidden="true">
        {formatClock(remaining)}
      </span>
      <button
        type="button"
        className={btn}
        onClick={() => {
          setDone(false);
          onChange(remaining || seconds, !running);
        }}
      >
        {running ? t('cook.pause') : t('cook.start')}
      </button>
      <button
        type="button"
        className={btn}
        onClick={() => {
          setDone(false);
          onChange(seconds, false);
        }}
      >
        {t('cook.reset')}
      </button>
      <span role="status" aria-live="assertive" className="text-brand font-bold">
        {done && t('cook.timerDone')}
      </span>
    </div>
  );
}
