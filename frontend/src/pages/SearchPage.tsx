import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router';

import { useRecipes } from '@/api/recipes';
import { RecipeCard } from '@/components/RecipeCard';
import { difficultyLabels, dietLabels, dishLabels, kosherLabels } from '@/lib/labels';
import {
  DIET_TAGS,
  DIFFICULTIES,
  DISH_TYPES,
  KOSHER_TYPES,
  MAX_MINUTES,
  hasActiveFilters,
  parseFilters,
  toApiParams,
  toUrlParams,
  type DietTag,
  type SearchFilters,
} from '@/lib/searchParams';

interface SelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, value, options, onChange }: SelectProps) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-muted">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-surface border-line rounded-lg border px-3 py-2"
      >
        <option value="">הכול</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = parseFilters(searchParams);
  const [draftQuery, setDraftQuery] = useState(filters.q);
  const { data, isPending, isError, isPlaceholderData } = useRecipes(toApiParams(filters));

  /** Applies a change. Any filter change goes back to the first page; a page change keeps filters. */
  function update(change: Partial<SearchFilters>) {
    setSearchParams(toUrlParams({ ...filters, page: 1, ...change }));
  }

  function submitQuery(e: FormEvent) {
    e.preventDefault();
    update({ q: draftQuery });
  }

  function toggleDiet(tag: DietTag) {
    const diet = filters.diet.includes(tag)
      ? filters.diet.filter((t) => t !== tag)
      : [...filters.diet, tag];
    update({ diet });
  }

  function clearAll() {
    setDraftQuery('');
    setSearchParams(new URLSearchParams());
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-3xl font-bold">חיפוש מתכונים</h1>

      <form role="search" onSubmit={submitQuery} className="flex gap-2">
        <label className="flex-1">
          <span className="sr-only">חיפוש לפי שם מתכון</span>
          <input
            type="search"
            value={draftQuery}
            onChange={(e) => setDraftQuery(e.target.value)}
            placeholder="חיפוש לפי שם מתכון"
            maxLength={100}
            className="bg-surface border-line w-full rounded-lg border px-3 py-2"
          />
        </label>
        <button type="submit" className="bg-brand text-brand-ink rounded-lg px-5 py-2">
          חפש
        </button>
      </form>

      <div className="bg-surface border-line rounded-card flex flex-col gap-4 border p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <FilterSelect
            label="סוג"
            value={filters.kosher_type}
            options={KOSHER_TYPES.map((v) => ({ value: v, label: kosherLabels[v] }))}
            onChange={(v) => update({ kosher_type: v as SearchFilters['kosher_type'] })}
          />
          <FilterSelect
            label="סוג מנה"
            value={filters.dish_type}
            options={DISH_TYPES.map((v) => ({ value: v, label: dishLabels[v] }))}
            onChange={(v) => update({ dish_type: v as SearchFilters['dish_type'] })}
          />
          <FilterSelect
            label="זמן מקסימלי"
            value={filters.max_minutes}
            options={MAX_MINUTES.map((v) => ({ value: v, label: `עד ${v} דקות` }))}
            onChange={(v) => update({ max_minutes: v as SearchFilters['max_minutes'] })}
          />
          <FilterSelect
            label="רמת קושי"
            value={filters.difficulty}
            options={DIFFICULTIES.map((v) => ({ value: v, label: difficultyLabels[v] }))}
            onChange={(v) => update({ difficulty: v as SearchFilters['difficulty'] })}
          />
        </div>
        <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <legend className="text-muted mb-1 text-sm">מגבלות תזונה</legend>
          {DIET_TAGS.map((tag) => (
            <label key={tag} className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={filters.diet.includes(tag)}
                onChange={() => toggleDiet(tag)}
              />
              {dietLabels[tag]}
            </label>
          ))}
        </fieldset>
        {hasActiveFilters(filters) && (
          <button type="button" onClick={clearAll} className="text-brand self-start underline">
            נקה את כל המסננים
          </button>
        )}
      </div>

      <div aria-live="polite" className="text-muted text-sm">
        {data && !isPending && `נמצאו ${data.total} מתכונים`}
      </div>

      {isPending && <p className="text-muted">טוען…</p>}
      {isError && <p role="alert">שגיאה בטעינת המתכונים. נסו שוב מאוחר יותר.</p>}

      {data && data.items.length === 0 && (
        <div className="bg-surface border-line rounded-card flex flex-col items-center gap-2 border p-8 text-center">
          <p className="text-lg font-bold">לא נמצאו מתכונים</p>
          <p className="text-muted">נסו להסיר מסנן או לחפש שם אחר.</p>
          {hasActiveFilters(filters) && (
            <button type="button" onClick={clearAll} className="text-brand underline">
              נקה את כל המסננים
            </button>
          )}
        </div>
      )}

      {data && data.items.length > 0 && (
        <div
          className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-3 ${isPlaceholderData ? 'opacity-60' : ''}`}
          aria-busy={isPlaceholderData}
        >
          {data.items.map((r) => (
            <RecipeCard key={r.id} recipe={r} />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <nav aria-label="עימוד" className="flex items-center justify-center gap-4">
          <button
            type="button"
            disabled={filters.page <= 1}
            onClick={() => update({ page: filters.page - 1 })}
            className="border-line bg-surface rounded-lg border px-4 py-2 disabled:opacity-40"
          >
            הקודם
          </button>
          <span>
            עמוד {filters.page} מתוך {totalPages}
          </span>
          <button
            type="button"
            disabled={filters.page >= totalPages}
            onClick={() => update({ page: filters.page + 1 })}
            className="border-line bg-surface rounded-lg border px-4 py-2 disabled:opacity-40"
          >
            הבא
          </button>
        </nav>
      )}
    </section>
  );
}
