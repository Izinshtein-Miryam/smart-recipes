import { Link } from 'react-router';

import type { RecipeCard as RecipeCardData } from '@/api/types';
import { difficultyLabels, dishLabels } from '@/lib/labels';

import { KosherBadge } from './KosherBadge';

export function RecipeCard({ recipe }: { recipe: RecipeCardData }) {
  return (
    <article className="bg-surface border-line shadow-card rounded-card flex flex-col gap-2 border p-4">
      <div className="flex items-center gap-2">
        <KosherBadge type={recipe.kosher_type} />
        {recipe.source === 'ai' && (
          <span className="bg-ai-soft text-ai rounded-full px-2.5 py-0.5 text-sm">נוצר ב-AI</span>
        )}
      </div>
      <h3 className="text-lg font-bold">
        <Link to={`/recipe/${recipe.slug}`} className="hover:text-brand">
          {recipe.title}
        </Link>
      </h3>
      <p className="text-muted text-sm">
        {dishLabels[recipe.dish_type]} · {recipe.total_minutes} דק׳ ·{' '}
        {difficultyLabels[recipe.difficulty]}
      </p>
    </article>
  );
}
