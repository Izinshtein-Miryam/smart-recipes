import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';

import { useRecipes } from '@/api/recipes';
import type { Lang, RecipeFilters } from '@/api/types';
import { Filters } from '@/components/Filters';
import { RecipeCard } from '@/components/RecipeCard';
import { EMPTY_FILTERS, type FilterValues } from '@/lib/filters';

const PAGE_SIZE = 12;

/** Filters live in the URL, so a filtered list can be shared and survives a refresh. */
export function HomePage() {
  const { t, i18n } = useTranslation();
  const [params, setParams] = useSearchParams();
  const values: FilterValues = { ...EMPTY_FILTERS };
  for (const key of Object.keys(EMPTY_FILTERS) as (keyof FilterValues)[])
    (values[key] as string) = params.get(key) ?? '';
  const page = Math.max(1, Number(params.get('page')) || 1);

  const filters: RecipeFilters = {
    lang: i18n.language as Lang,
    q: values.q || undefined,
    kashrut: values.kashrut || undefined,
    difficulty: values.difficulty || undefined,
    equipment: values.equipment ? [values.equipment] : undefined,
    max_minutes: values.max_minutes ? Number(values.max_minutes) : undefined,
    servings: values.servings ? Number(values.servings) : undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
  const { data, isPending, isError } = useRecipes(filters);
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));

  const update = (next: FilterValues) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(next)) if (v) p.set(k, v);
    setParams(p, { replace: true });
  };
  const goto = (n: number) => {
    const p = new URLSearchParams(params);
    if (n > 1) p.set('page', String(n));
    else p.delete('page');
    setParams(p);
  };

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-4xl">{t('home.title')}</h1>
      <Filters value={values} onChange={update} />
      <div aria-live="polite">
        {isPending && <p className="text-muted">{t('common.loading')}</p>}
        {isError && <p role="alert">{t('common.loadError')}</p>}
        {data?.data.length === 0 && <p className="text-muted">{t('home.empty')}</p>}
      </div>
      {data && data.data.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-7">
          {data.data.map((r) => (
            <RecipeCard key={r.id} recipe={r} />
          ))}
        </div>
      )}
      {pages > 1 && (
        <nav aria-label={t('common.pagination')} className="flex items-center justify-center gap-4">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => goto(page - 1)}
            className="border-line rounded-lg border px-4 py-2 disabled:opacity-40"
          >
            {t('common.prev')}
          </button>
          <span>
            {page} / {pages}
          </span>
          <button
            type="button"
            disabled={page >= pages}
            onClick={() => goto(page + 1)}
            className="border-line rounded-lg border px-4 py-2 disabled:opacity-40"
          >
            {t('common.next')}
          </button>
        </nav>
      )}
    </section>
  );
}
