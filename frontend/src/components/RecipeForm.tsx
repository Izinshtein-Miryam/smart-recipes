import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { Difficulty, Equipment, Ingredient, Kashrut, Lang } from '@/api/types';
import { EMPTY_RECIPE, type FormValue } from '@/lib/recipeForm';

const input = 'border-line bg-surface rounded-lg border px-3 py-2';
const label = 'flex flex-col gap-1 font-semibold';

/** Shared by the public submit page and the admin editor. */
export function RecipeForm({
  initial = EMPTY_RECIPE,
  withImage,
  submitLabel,
  busy,
  error,
  onSubmit,
}: {
  initial?: FormValue;
  withImage?: boolean;
  submitLabel: string;
  busy?: boolean;
  error?: string | null;
  onSubmit: (value: FormValue, image: File | null) => void;
}) {
  const { t } = useTranslation();
  const [v, setV] = useState<FormValue>(initial);
  const [image, setImage] = useState<File | null>(null);
  const set = <K extends keyof FormValue>(k: K, val: FormValue[K]) => setV({ ...v, [k]: val });
  const setIng = (i: number, patch: Partial<Ingredient>) =>
    set(
      'ingredients',
      v.ingredients.map((x, idx) => (idx === i ? { ...x, ...patch } : x)),
    );

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(
      {
        ...v,
        ingredients: v.ingredients.filter((i) => i.name.trim()),
        steps: v.steps.map((s) => s.trim()).filter(Boolean),
      },
      image,
    );
  };

  return (
    <form onSubmit={submit} className="flex max-w-3xl flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={label}>
          {t('form.title')}
          <input
            required
            maxLength={200}
            value={v.title}
            onChange={(e) => set('title', e.target.value)}
            className={input}
          />
        </label>
        <label className={label}>
          {t('form.lang')}
          <select
            value={v.lang}
            onChange={(e) => set('lang', e.target.value as Lang)}
            className={input}
          >
            <option value="he">עברית</option>
            <option value="en">English</option>
          </select>
        </label>
      </div>
      <label className={label}>
        {t('form.description')}
        <textarea
          maxLength={1000}
          rows={2}
          value={v.description}
          onChange={(e) => set('description', e.target.value)}
          className={input}
        />
      </label>
      <div className="grid gap-4 sm:grid-cols-4">
        <label className={label}>
          {t('common.servings')}
          <input
            type="number"
            required
            min={1}
            max={100}
            value={v.servings}
            onChange={(e) => set('servings', Number(e.target.value))}
            className={input}
          />
        </label>
        <label className={label}>
          {t('form.prepMinutes')}
          <input
            type="number"
            required
            min={1}
            value={v.prep_minutes}
            onChange={(e) => set('prep_minutes', Number(e.target.value))}
            className={input}
          />
        </label>
        <label className={label}>
          {t('filters.difficulty')}
          <select
            value={v.difficulty}
            onChange={(e) => set('difficulty', e.target.value as Difficulty)}
            className={input}
          >
            {(['easy', 'medium', 'hard'] as const).map((d) => (
              <option key={d} value={d}>
                {t(`difficulty.${d}`)}
              </option>
            ))}
          </select>
        </label>
        <label className={label}>
          {t('filters.kashrut')}
          <select
            value={v.kashrut}
            onChange={(e) => set('kashrut', e.target.value as Kashrut)}
            className={input}
          >
            {(['meat', 'dairy', 'parve'] as const).map((k) => (
              <option key={k} value={k}>
                {t(`kashrut.${k}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <fieldset className="flex flex-wrap gap-4">
        <legend className="mb-1 font-semibold">{t('filters.equipment')}</legend>
        {(['oven', 'stovetop', 'one_pot', 'no_cook'] as Equipment[]).map((eq) => (
          <label key={eq} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={v.equipment.includes(eq)}
              onChange={(e) =>
                set(
                  'equipment',
                  e.target.checked ? [...v.equipment, eq] : v.equipment.filter((x) => x !== eq),
                )
              }
            />
            {t(`equipment.${eq}`)}
          </label>
        ))}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-semibold">{t('common.ingredients')}</legend>
        {v.ingredients.map((ing, i) => (
          <div key={i} className="flex flex-wrap gap-2">
            <input
              aria-label={t('form.ingName')}
              placeholder={t('form.ingName')}
              value={ing.name}
              onChange={(e) => setIng(i, { name: e.target.value })}
              className={`${input} min-w-40 flex-1`}
            />
            <input
              aria-label={t('form.ingQty')}
              placeholder={t('form.ingQty')}
              type="number"
              step="any"
              min={0}
              value={ing.quantity ?? ''}
              onChange={(e) =>
                setIng(i, { quantity: e.target.value === '' ? null : Number(e.target.value) })
              }
              className={`${input} w-24`}
            />
            <input
              aria-label={t('form.ingUnit')}
              placeholder={t('form.ingUnit')}
              value={ing.unit ?? ''}
              onChange={(e) => setIng(i, { unit: e.target.value || null })}
              className={`${input} w-24`}
            />
            <button
              type="button"
              aria-label={t('common.remove')}
              onClick={() =>
                set(
                  'ingredients',
                  v.ingredients.filter((_, idx) => idx !== i),
                )
              }
              className="text-muted px-2"
            >
              ×
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            set('ingredients', [
              ...v.ingredients,
              { name: '', quantity: null, unit: null, note: null },
            ])
          }
          className="text-brand self-start font-semibold"
        >
          + {t('form.addIngredient')}
        </button>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-semibold">{t('common.steps')}</legend>
        {v.steps.map((s, i) => (
          <div key={i} className="flex gap-2">
            <textarea
              aria-label={`${t('form.step')} ${i + 1}`}
              rows={2}
              value={s}
              onChange={(e) =>
                set(
                  'steps',
                  v.steps.map((x, idx) => (idx === i ? e.target.value : x)),
                )
              }
              className={`${input} flex-1`}
            />
            <button
              type="button"
              aria-label={t('common.remove')}
              onClick={() =>
                set(
                  'steps',
                  v.steps.filter((_, idx) => idx !== i),
                )
              }
              className="text-muted px-2"
            >
              ×
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => set('steps', [...v.steps, ''])}
          className="text-brand self-start font-semibold"
        >
          + {t('form.addStep')}
        </button>
      </fieldset>

      {withImage && (
        <label className={label}>
          {t('form.image')}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setImage(e.target.files?.[0] ?? null)}
          />
        </label>
      )}
      {error && (
        <p role="alert" className="text-meat">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="bg-brand self-start rounded-full px-8 py-3 font-semibold text-white disabled:opacity-50"
      >
        {submitLabel}
      </button>
    </form>
  );
}
