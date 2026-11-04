import { useState } from 'react';
import { useParams } from 'react-router';

import { useRecipe } from '@/api/recipes';
import { KosherBadge } from '@/components/KosherBadge';
import { ServingsStepper } from '@/components/ServingsStepper';

const quantityFormat = new Intl.NumberFormat('he-IL', { maximumFractionDigits: 2 });

export function RecipePage() {
  const { slug = '' } = useParams();
  // Remount on slug change so the chosen serving count resets for a new recipe.
  return <RecipeView key={slug} slug={slug} />;
}

function RecipeView({ slug }: { slug: string }) {
  const [servings, setServings] = useState<number>();
  const { data: recipe, isPending, isError, isPlaceholderData } = useRecipe(slug, servings);

  if (isPending) return <p className="text-muted">טוען…</p>;
  if (isError) return <p role="alert">המתכון לא נמצא</p>;

  return (
    <article className="flex flex-col gap-4">
      <KosherBadge type={recipe.kosher_type} />
      <h1 className="text-3xl font-bold">{recipe.title}</h1>
      <p className="text-muted">{recipe.description}</p>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold">רכיבים</h2>
        <ServingsStepper value={servings ?? recipe.servings} onChange={setServings} />
      </div>
      <ul className="list-disc ps-6" aria-busy={isPlaceholderData}>
        {recipe.ingredients.map((i) => (
          <li key={i.ingredient_id}>
            {i.quantity !== null && quantityFormat.format(i.quantity)} {i.unit} {i.name}
          </li>
        ))}
      </ul>
      <h2 className="text-xl font-bold">אופן ההכנה</h2>
      <ol className="list-decimal ps-6">
        {recipe.steps.map((s) => (
          <li key={s.order}>{s.text}</li>
        ))}
      </ol>
    </article>
  );
}
