import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';

import { useRecipe } from '@/api/recipes';
import { KosherBadge } from '@/components/KosherBadge';

export function RecipePage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const { data: recipe, isPending, isError } = useRecipe(id);

  if (isPending) return <p className="text-muted">{t('common.loading')}</p>;
  if (isError) return <p role="alert">{t('recipe.notFound')}</p>;

  const n = recipe.nutrition;
  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <KosherBadge type={recipe.kashrut} />
        <h1 className="text-4xl">{recipe.title}</h1>
        <p className="text-muted">{recipe.description}</p>
        <p className="text-muted text-sm">
          {recipe.prep_minutes} {t('common.minutes')} · {recipe.servings} {t('common.servings')} ·{' '}
          {t(`difficulty.${recipe.difficulty}`)}
        </p>
      </header>

      <section>
        <h2 className="mb-2 text-2xl">{t('common.ingredients')}</h2>
        <ul className="list-disc ps-6">
          {recipe.ingredients.map((i, idx) => (
            <li key={idx}>{[i.quantity, i.unit, i.name].filter((x) => x != null).join(' ')}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-2xl">{t('common.steps')}</h2>
        <ol className="list-decimal ps-6">
          {recipe.steps.map((s, idx) => (
            <li key={idx}>{s}</li>
          ))}
        </ol>
      </section>

      {n && (
        <section>
          <h2 className="mb-2 text-2xl">{t('recipe.nutrition')}</h2>
          <dl className="grid max-w-md grid-cols-2 gap-x-6 gap-y-1">
            <dt>{t('recipe.calories')}</dt>
            <dd>{n.calories}</dd>
            <dt>{t('recipe.protein')}</dt>
            <dd>{n.protein_g} g</dd>
            <dt>{t('recipe.carbs')}</dt>
            <dd>{n.carbs_g} g</dd>
            <dt>{t('recipe.fat')}</dt>
            <dd>{n.fat_g} g</dd>
          </dl>
        </section>
      )}
      {/* TODO: quick adapt buttons, free-text adapt field, chat side panel */}
    </article>
  );
}
