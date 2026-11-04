import { useTranslation } from 'react-i18next';

import { useRecipes } from '@/api/recipes';
import type { Lang } from '@/api/types';
import { RecipeCard } from '@/components/RecipeCard';

export function HomePage() {
  const { t, i18n } = useTranslation();
  // The list shows recipes in the selected UI language.
  const { data, isPending, isError } = useRecipes({ lang: i18n.language as Lang });

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-4xl">{t('home.title')}</h1>
      {/* TODO: text search + filter panel (prep time, difficulty, equipment, servings, kashrut) */}
      {isPending && <p className="text-muted">{t('common.loading')}</p>}
      {isError && <p role="alert">{t('common.loadError')}</p>}
      {data?.length === 0 && <p className="text-muted">{t('home.empty')}</p>}
      {data && data.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-7">
          {data.map((r) => (
            <RecipeCard key={r.id} recipe={r} />
          ))}
        </div>
      )}
    </section>
  );
}
