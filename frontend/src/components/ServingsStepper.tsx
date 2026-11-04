export const MIN_SERVINGS = 1;
/** Matches the `le=100` bound on `GET /api/recipes/{slug}?servings=`. */
export const MAX_SERVINGS = 100;

interface Props {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

const buttonClass =
  'h-9 w-9 cursor-pointer text-lg disabled:cursor-not-allowed disabled:opacity-40 hover:bg-brand-soft';

export function ServingsStepper({
  value,
  onChange,
  min = MIN_SERVINGS,
  max = MAX_SERVINGS,
}: Props) {
  const set = (next: number) => onChange(Math.min(max, Math.max(min, next)));

  return (
    <div className="flex items-center gap-2">
      <div
        role="group"
        aria-label="מספר מנות"
        className="border-line bg-surface inline-flex items-center overflow-hidden rounded-[10px] border"
      >
        <button
          type="button"
          className={buttonClass}
          aria-label="הפחתת מנה"
          disabled={value <= min}
          onClick={() => set(value - 1)}
        >
          −
        </button>
        <output aria-live="polite" className="min-w-9 text-center font-bold">
          {value}
        </output>
        <button
          type="button"
          className={buttonClass}
          aria-label="הוספת מנה"
          disabled={value >= max}
          onClick={() => set(value + 1)}
        >
          +
        </button>
      </div>
      <span className="text-muted text-sm">מנות</span>
    </div>
  );
}
