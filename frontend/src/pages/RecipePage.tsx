import { useParams } from 'react-router';

import { useRecipe } from '@/api/recipes';
import { KosherBadge } from '@/components/KosherBadge';
import { RecipeShareActions } from '@/components/RecipeShareActions';

export function RecipePage() {
  const { slug = '' } = useParams();
  const { data: recipe, isPending, isError } = useRecipe(slug);

  if (isPending) return <p className="text-muted">טוען…</p>;
  if (isError) return <p role="alert">המתכון לא נמצא</p>;

  return (
    <article className="flex flex-col gap-4">
      <KosherBadge type={recipe.kosher_type} />
      <h1 className="text-3xl font-bold">{recipe.title}</h1>
      <p className="text-muted">{recipe.description}</p>
      <RecipeShareActions title={recipe.title} description={recipe.description} />
      <h2 className="text-xl font-bold">רכיבים</h2>
      <ul className="list-disc ps-6">
        {recipe.ingredients.map((i) => (
          <li key={i.ingredient_id}>
            {i.quantity} {i.unit} {i.name}
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
