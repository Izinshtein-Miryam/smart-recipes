import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router';

import { adaptRecipe } from '@/api/ai';
import { useRecipe } from '@/api/recipes';
import type { AdaptedRecipe } from '@/api/types';
import { ChatPanel } from '@/components/ChatPanel';
import { KosherBadge } from '@/components/KosherBadge';
import { EQUIPMENT_ICON } from '@/lib/icons';

const QUICK = ['quick1', 'quick2', 'quick3'] as const;

export function RecipePage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [servings, setServings] = useState<number | undefined>();
  const [chatOpen, setChatOpen] = useState(false);
  const [instruction, setInstruction] = useState('');
  const [copied, setCopied] = useState(false);
  const { data: recipe, isPending, isError } = useRecipe(id, servings);

  const goAdapted = (adapted: AdaptedRecipe) =>
    void navigate(`/recipes/${id}/adapted`, { state: { adapted } });
  const adapt = useMutation({
    mutationFn: (text: string) => adaptRecipe(id ?? '', text),
    onSuccess: goAdapted,
  });

  if (isPending) return <p className="text-muted">{t('common.loading')}</p>;
  if (isError)
    return (
      <div role="alert">
        <h1 className="text-3xl">{t('recipe.notFound')}</h1>
        <Link to="/" className="text-brand">
          {t('recipe.backToList')}
        </Link>
      </div>
    );

  const n = recipe.nutrition;
  const current = servings ?? recipe.servings;

  const share = async () => {
    const url = window.location.href;
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({ title: recipe.title, url });
        return;
      } catch {
        /* cancelled: fall through to copying */
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      /* clipboard unavailable */
    }
  };

  const btn = 'border-line hover:border-brand rounded-full border px-4 py-2 text-sm font-semibold';
  return (
    <article className="flex flex-col gap-6">
      {recipe.image_url ? (
        <img
          src={recipe.image_url}
          alt={recipe.title}
          className="rounded-card h-64 w-full object-cover sm:h-96"
        />
      ) : (
        <div
          aria-hidden="true"
          className="bg-parve-soft rounded-card flex h-48 items-center justify-center text-7xl print:hidden"
        >
          {EQUIPMENT_ICON[recipe.equipment[0] ?? 'stovetop']}
        </div>
      )}
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <KosherBadge type={recipe.kashrut} />
          {recipe.equipment.map((e) => (
            <span key={e} className="bg-line rounded-full px-3 py-1 text-xs font-bold">
              {t(`equipment.${e}`)}
            </span>
          ))}
        </div>
        <h1 className="text-4xl">{recipe.title}</h1>
        <p className="text-muted">{recipe.description}</p>
        <p className="text-muted text-sm">
          {recipe.prep_minutes} {t('common.minutes')} · {t(`difficulty.${recipe.difficulty}`)}
        </p>
        <div className="flex flex-wrap gap-2 print:hidden">
          <Link
            to={`/recipes/${recipe.id}/cook`}
            className="bg-brand rounded-full px-5 py-2 font-semibold text-white"
          >
            {t('recipe.startCooking')}
          </Link>
          <button type="button" className={btn} onClick={() => window.print()}>
            {t('recipe.print')}
          </button>
          <button type="button" className={btn} onClick={() => void share()}>
            {t('recipe.share')}
          </button>
          <span role="status" className="text-green self-center text-sm">
            {copied && t('recipe.linkCopied')}
          </span>
        </div>
      </header>

      <section>
        <div className="mb-2 flex flex-wrap items-center gap-4">
          <h2 className="text-2xl">{t('common.ingredients')}</h2>
          <div
            role="group"
            aria-label={t('recipe.servingsPicker')}
            className="flex items-center gap-2 print:hidden"
          >
            <button
              type="button"
              aria-label={t('recipe.fewer')}
              disabled={current <= 1}
              onClick={() => setServings(Math.max(1, current - 1))}
              className="border-line size-9 rounded-full border text-lg disabled:opacity-40"
            >
              −
            </button>
            <output aria-live="polite" className="min-w-24 text-center font-semibold">
              {current} {t('common.servings')}
            </output>
            <button
              type="button"
              aria-label={t('recipe.more')}
              disabled={current >= 100}
              onClick={() => setServings(current + 1)}
              className="border-line size-9 rounded-full border text-lg"
            >
              +
            </button>
          </div>
        </div>
        <ul className="list-disc ps-6">
          {recipe.ingredients.map((i, idx) => (
            <li key={idx}>{[i.quantity, i.unit, i.name].filter((x) => x != null).join(' ')}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-2xl">{t('common.steps')}</h2>
        <ol className="list-decimal space-y-2 ps-6">
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

      <section className="print:hidden">
        <h2 className="mb-2 text-2xl">{t('recipe.adaptTitle')}</h2>
        <div className="mb-3 flex flex-wrap gap-2">
          {QUICK.map((k) => (
            <button
              key={k}
              type="button"
              disabled={adapt.isPending}
              className={btn}
              onClick={() => adapt.mutate(t(`recipe.${k}`))}
            >
              {t(`recipe.${k}`)}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (instruction.trim()) adapt.mutate(instruction.trim());
          }}
        >
          <input
            value={instruction}
            maxLength={500}
            onChange={(e) => setInstruction(e.target.value)}
            aria-label={t('recipe.adaptPlaceholder')}
            placeholder={t('recipe.adaptPlaceholder')}
            className="border-line bg-surface min-w-0 flex-1 rounded-lg border px-3 py-2"
          />
          <button
            type="submit"
            disabled={adapt.isPending}
            className="bg-brand rounded-lg px-5 text-white disabled:opacity-50"
          >
            {adapt.isPending ? t('common.loading') : t('recipe.adaptGo')}
          </button>
        </form>
        {adapt.isError && (
          <p role="alert" className="mt-2">
            {t('common.aiUnavailable')}
          </p>
        )}
      </section>

      {!chatOpen && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="bg-brand shadow-lift fixed end-6 bottom-6 rounded-full px-6 py-3 font-semibold text-white print:hidden"
        >
          💬 {t('chat.open')}
        </button>
      )}
      {chatOpen && (
        <ChatPanel
          recipeId={recipe.id}
          onClose={() => setChatOpen(false)}
          onAdapted={goAdapted}
          onScaled={setServings}
        />
      )}
    </article>
  );
}
