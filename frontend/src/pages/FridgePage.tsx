import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { fridgeSearch } from '@/api/ai';
import type { Lang } from '@/api/types';
import { RecipeCard } from '@/components/RecipeCard';
import { TagInput } from '@/components/TagInput';

export function FridgePage() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<string[]>([]);
  const search = useMutation({
    mutationFn: () => fridgeSearch({ ingredients: items, lang: i18n.language as Lang }),
  });

  return (
    <section className="flex max-w-5xl flex-col gap-6">
      <h1 className="text-4xl">{t('fridge.title')}</h1>
      <p className="text-muted">{t('fridge.hint')}</p>
      <TagInput
        id="fridge-items"
        label={t('fridge.ingredients')}
        value={items}
        onChange={setItems}
      />
      <button
        type="button"
        disabled={items.length === 0 || search.isPending}
        onClick={() => search.mutate()}
        className="bg-brand self-start rounded-full px-8 py-3 font-semibold text-white disabled:opacity-50"
      >
        {search.isPending ? t('common.loading') : t('fridge.search')}
      </button>
      <div aria-live="polite">
        {search.isError && <p role="alert">{t('common.aiUnavailable')}</p>}
        {search.data?.results.length === 0 && <p className="text-muted">{t('fridge.none')}</p>}
      </div>
      {search.data && search.data.results.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-7">
          {search.data.results.map((r) => (
            <RecipeCard
              key={r.recipe.id}
              recipe={r.recipe}
              extra={
                <div className="flex flex-col gap-1 text-sm">
                  <strong>
                    {t('fridge.match')}: {r.match_score}%
                  </strong>
                  {r.missing_ingredients.length > 0 && (
                    <ul className="flex flex-wrap gap-1" aria-label={t('fridge.missing')}>
                      {r.missing_ingredients.map((m) => (
                        <li key={m} className="bg-meat-soft text-meat rounded-full px-2 py-0.5">
                          {t('fridge.missing')}: {m}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              }
            />
          ))}
        </div>
      )}
    </section>
  );
}
