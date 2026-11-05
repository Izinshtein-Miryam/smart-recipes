import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { RecipeSummary } from '@/api/types';

import { KosherBadge } from './KosherBadge';

export function RecipeCard({ recipe }: { recipe: RecipeSummary }) {
  const { t } = useTranslation();
  return (
    <article className="bg-surface border-line shadow-card rounded-card hover:shadow-lift flex flex-col overflow-hidden border transition hover:-translate-y-1">
      {recipe.image_url && (
        <img src={recipe.image_url} alt="" className="h-44 w-full object-cover" loading="lazy" />
      )}
      <div className="flex flex-1 flex-col gap-2 p-5">
        <div>
          <KosherBadge type={recipe.kashrut} />
        </div>
        <h3 className="text-xl">
          <Link to={`/recipes/${recipe.id}`} className="hover:text-brand">
            {recipe.title}
          </Link>
        </h3>
        <p className="text-muted flex-1 text-sm">{recipe.description}</p>
        <p className="text-muted border-line border-t pt-3 text-sm">
          {recipe.prep_minutes} {t('common.minutes')} · {t(`difficulty.${recipe.difficulty}`)}
        </p>
      </div>
    </article>
  );
}
