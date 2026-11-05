import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useParams } from 'react-router';

import { submitRecipe } from '@/api/admin';
import { useRecipe } from '@/api/recipes';
import type { AdaptedRecipe } from '@/api/types';
import { KosherBadge } from '@/components/KosherBadge';

/** Temporary view of an AI-adapted recipe; saving submits it for admin approval. */
export function AdaptedRecipePage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const adapted = (useLocation().state as { adapted?: AdaptedRecipe } | null)?.adapted;
  const { data: original } = useRecipe(id);
  const save = useMutation({
    mutationFn: () => {
      const a = adapted as AdaptedRecipe;
      const content = {
        title: a.title,
        description: a.description,
        servings: a.servings,
        prep_minutes: a.prep_minutes,
        difficulty: a.difficulty,
        equipment: a.equipment,
        kashrut: a.kashrut,
        ingredients: a.ingredients,
        steps: a.steps,
      };
      return submitRecipe({ ...content, lang: original?.lang ?? 'he', source_recipe_id: id });
    },
  });

  if (!adapted)
    return (
      <div>
        <p>{t('adapted.missing')}</p>
        <Link to={`/recipes/${id}`} className="text-brand">
          {t('adapted.back')}
        </Link>
      </div>
    );

  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <KosherBadge type={adapted.kashrut} />
        <h1 className="text-4xl">{adapted.title}</h1>
        <p className="text-muted">{adapted.description}</p>
        <p className="text-muted text-sm">
          {adapted.prep_minutes} {t('common.minutes')} · {adapted.servings} {t('common.servings')}
        </p>
      </header>

      {!adapted.feasible && (
        <p role="alert" className="bg-meat-soft text-meat rounded-lg p-4">
          {t('adapted.infeasible')} {adapted.reason}
        </p>
      )}

      <section>
        <h2 className="mb-2 text-2xl">{t('adapted.changes')}</h2>
        <ul className="list-disc ps-6">
          {adapted.changes_summary.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section>
          <h2 className="mb-2 text-2xl">{t('adapted.original')}</h2>
          <ul className="list-disc ps-6">
            {original?.ingredients.map((i, idx) => (
              <li key={idx}>{[i.quantity, i.unit, i.name].filter((x) => x != null).join(' ')}</li>
            ))}
          </ul>
        </section>
        <section>
          <h2 className="mb-2 text-2xl">{t('adapted.adapted')}</h2>
          <ul className="list-disc ps-6">
            {adapted.ingredients.map((i, idx) => (
              <li key={idx}>{[i.quantity, i.unit, i.name].filter((x) => x != null).join(' ')}</li>
            ))}
          </ul>
        </section>
      </div>

      <section>
        <h2 className="mb-2 text-2xl">{t('common.steps')}</h2>
        <ol className="list-decimal space-y-2 ps-6">
          {adapted.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      </section>

      <div className="flex flex-wrap items-center gap-4">
        {adapted.feasible && !save.isSuccess && (
          <button
            type="button"
            disabled={save.isPending}
            onClick={() => save.mutate()}
            className="bg-brand rounded-full px-6 py-3 font-semibold text-white disabled:opacity-50"
          >
            {t('adapted.save')}
          </button>
        )}
        <Link to={`/recipes/${id}`} className="text-brand font-semibold">
          {t('adapted.back')}
        </Link>
      </div>
      <div role="status">
        {save.isSuccess && <p className="text-green">{t('submit.pending')}</p>}
      </div>
      {save.isError && <p role="alert">{t('submit.error')}</p>}
    </article>
  );
}
