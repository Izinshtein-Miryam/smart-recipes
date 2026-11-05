import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { RecipeSummary } from '@/api/types';
import { EQUIPMENT_ICON } from '@/lib/icons';

import { KosherBadge } from './KosherBadge';

/** Recipes without a photo show an icon for their cooking method. */
export function RecipeCard({ recipe, extra }: { recipe: RecipeSummary; extra?: React.ReactNode }) {
  const { t } = useTranslation();
  const icon = EQUIPMENT_ICON[recipe.equipment[0] ?? 'stovetop'];
  return (
    <article className="bg-surface border-line shadow-card rounded-card hover:shadow-lift flex flex-col overflow-hidden border transition hover:-translate-y-1">
      {recipe.image_url ? (
        <img
          src={recipe.image_url}
          alt={recipe.title}
          className="h-44 w-full object-cover"
          loading="lazy"
        />
      ) : (
        <div
          role="img"
          aria-label={t(`equipment.${recipe.equipment[0] ?? 'stovetop'}`)}
          className="bg-parve-soft flex h-44 w-full items-center justify-center text-6xl"
        >
          {icon}
        </div>
      )}
      <div className="flex flex-1 flex-col gap-2 p-5">
        <div>
          <KosherBadge type={recipe.kashrut} />
        </div>
        <h2 className="text-xl">
          <Link to={`/recipes/${recipe.id}`} className="hover:text-brand">
            {recipe.title}
          </Link>
        </h2>
        <p className="text-muted flex-1 text-sm">{recipe.description}</p>
        {extra}
        <p className="text-muted border-line border-t pt-3 text-sm">
          {recipe.prep_minutes} {t('common.minutes')} · {t(`difficulty.${recipe.difficulty}`)}
        </p>
      </div>
    </article>
  );
}
