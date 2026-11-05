import { useTranslation } from 'react-i18next';

import type { Difficulty, Equipment, Kashrut } from '@/api/types';
import { EMPTY_FILTERS, type FilterValues } from '@/lib/filters';

const sel = 'border-line bg-surface rounded-lg border px-3 py-2';

export function Filters({
  value,
  onChange,
}: {
  value: FilterValues;
  onChange: (next: FilterValues) => void;
}) {
  const { t } = useTranslation();
  const set = <K extends keyof FilterValues>(k: K, v: FilterValues[K]) =>
    onChange({ ...value, [k]: v });
  const field = 'flex flex-col gap-1 text-sm font-semibold';
  return (
    <form
      role="search"
      aria-label={t('filters.label')}
      onSubmit={(e) => e.preventDefault()}
      className="flex flex-wrap items-end gap-4"
    >
      <label className={`${field} min-w-48 flex-1`}>
        {t('filters.search')}
        <input
          type="search"
          value={value.q}
          onChange={(e) => set('q', e.target.value)}
          className={sel}
        />
      </label>
      <label className={field}>
        {t('filters.kashrut')}
        <select
          value={value.kashrut}
          onChange={(e) => set('kashrut', e.target.value as Kashrut | '')}
          className={sel}
        >
          <option value="">{t('filters.any')}</option>
          {(['meat', 'dairy', 'parve'] as const).map((k) => (
            <option key={k} value={k}>
              {t(`kashrut.${k}`)}
            </option>
          ))}
        </select>
      </label>
      <label className={field}>
        {t('filters.difficulty')}
        <select
          value={value.difficulty}
          onChange={(e) => set('difficulty', e.target.value as Difficulty | '')}
          className={sel}
        >
          <option value="">{t('filters.any')}</option>
          {(['easy', 'medium', 'hard'] as const).map((k) => (
            <option key={k} value={k}>
              {t(`difficulty.${k}`)}
            </option>
          ))}
        </select>
      </label>
      <label className={field}>
        {t('filters.equipment')}
        <select
          value={value.equipment}
          onChange={(e) => set('equipment', e.target.value as Equipment | '')}
          className={sel}
        >
          <option value="">{t('filters.any')}</option>
          {(['oven', 'stovetop', 'one_pot', 'no_cook'] as const).map((k) => (
            <option key={k} value={k}>
              {t(`equipment.${k}`)}
            </option>
          ))}
        </select>
      </label>
      <label className={field}>
        {t('filters.maxMinutes')}
        <input
          type="number"
          min={1}
          value={value.max_minutes}
          onChange={(e) => set('max_minutes', e.target.value)}
          className={`${sel} w-28`}
        />
      </label>
      <label className={field}>
        {t('filters.servings')}
        <input
          type="number"
          min={1}
          value={value.servings}
          onChange={(e) => set('servings', e.target.value)}
          className={`${sel} w-24`}
        />
      </label>
      <button
        type="button"
        onClick={() => onChange(EMPTY_FILTERS)}
        className="text-brand px-2 py-2 font-semibold"
      >
        {t('filters.clear')}
      </button>
    </form>
  );
}
