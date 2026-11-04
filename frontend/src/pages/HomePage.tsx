import { useRecipes } from '@/api/recipes';
import { RecipeCard } from '@/components/RecipeCard';

export function HomePage() {
  const { data, isPending, isError } = useRecipes();

  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-3xl font-bold">מה מבשלים היום?</h1>
      {isPending && <p className="text-muted">טוען…</p>}
      {isError && <p role="alert">שגיאה בטעינת המתכונים</p>}
      {data && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((r) => (
            <RecipeCard key={r.id} recipe={r} />
          ))}
        </div>
      )}
    </section>
  );
}
