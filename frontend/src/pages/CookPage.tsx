import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';

import { useRecipe } from '@/api/recipes';
import { StepTimer } from '@/components/StepTimer';
import { timerSeconds } from '@/lib/timer';

interface TimerState {
  remaining: number;
  running: boolean;
}

export function CookPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const { data: recipe, isPending, isError } = useRecipe(id);
  const [step, setStep] = useState(0);
  const [timers, setTimers] = useState<Record<number, TimerState>>({});
  const touchX = useRef<number | null>(null);
  const rtl = i18n.language === 'he';
  const total = recipe?.steps.length ?? 0;

  const go = useCallback(
    (delta: number) => setStep((s) => Math.min(Math.max(s + delta, 0), Math.max(total - 1, 0))),
    [total],
  );

  // Arrow keys follow the reading direction: in RTL, "next" is the left arrow.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') go(rtl ? -1 : 1);
      if (e.key === 'ArrowLeft') go(rtl ? 1 : -1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, rtl]);

  // Keep the screen on while cooking; re-acquire when the tab becomes visible again.
  useEffect(() => {
    let lock: WakeLockSentinel | null = null;
    const acquire = async () => {
      try {
        lock = (await navigator.wakeLock?.request('screen')) ?? null;
      } catch {
        /* unsupported or denied */
      }
    };
    const onVisible = () => {
      if (document.visibilityState === 'visible') void acquire();
    };
    void acquire();
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      void lock?.release().catch(() => undefined);
    };
  }, []);

  const setTimer = useCallback(
    (i: number) => (remaining: number, running: boolean) =>
      setTimers((x) => ({ ...x, [i]: { remaining, running } })),
    [],
  );

  if (isPending) return <p className="text-muted">{t('common.loading')}</p>;
  if (isError) return <p role="alert">{t('recipe.notFound')}</p>;

  const text = recipe.steps[step] ?? '';
  const secs = timerSeconds(text);
  const running = Object.entries(timers).filter(([i, s]) => s.running && Number(i) !== step);
  const btn = 'border-line rounded-full border px-8 py-4 text-xl font-semibold disabled:opacity-40';

  return (
    <section
      className="flex min-h-[70vh] flex-col gap-6"
      onTouchStart={(e) => (touchX.current = e.touches[0]?.clientX ?? null)}
      onTouchEnd={(e) => {
        const start = touchX.current;
        const end = e.changedTouches[0]?.clientX;
        touchX.current = null;
        if (start == null || end == null || Math.abs(end - start) < 50) return;
        // Swiping left (finger moves left) goes forward in RTL; right goes forward in LTR.
        const left = end < start;
        go(left === rtl ? 1 : -1);
      }}
    >
      <header className="flex items-center justify-between">
        <h1 className="text-2xl">{recipe.title}</h1>
        <Link to={`/recipes/${recipe.id}`} className="text-brand font-semibold">
          {t('cook.exit')}
        </Link>
      </header>
      <progress
        className="w-full"
        max={total}
        value={step + 1}
        aria-label={t('cook.progress', { n: step + 1, total })}
      />
      <p className="text-muted">{t('cook.progress', { n: step + 1, total })}</p>
      <p className="flex-1 text-3xl leading-relaxed sm:text-4xl" aria-live="polite">
        {text}
      </p>
      {secs && (
        <StepTimer
          key={step}
          seconds={secs}
          remaining={timers[step]?.remaining ?? secs}
          running={timers[step]?.running ?? false}
          onChange={setTimer(step)}
        />
      )}
      {running.length > 0 && (
        <p className="text-brand">{t('cook.otherTimers', { count: running.length })}</p>
      )}
      <details>
        <summary className="cursor-pointer font-semibold">{t('common.ingredients')}</summary>
        <ul className="mt-2 list-disc ps-6">
          {recipe.ingredients.map((i, idx) => (
            <li key={idx}>{[i.quantity, i.unit, i.name].filter((x) => x != null).join(' ')}</li>
          ))}
        </ul>
      </details>
      <div className="flex justify-between gap-4">
        <button type="button" className={btn} disabled={step === 0} onClick={() => go(-1)}>
          {t('cook.prev')}
        </button>
        <button
          type="button"
          className={`${btn} bg-brand border-brand text-white`}
          disabled={step >= total - 1}
          onClick={() => go(1)}
        >
          {t('cook.next')}
        </button>
      </div>
    </section>
  );
}
