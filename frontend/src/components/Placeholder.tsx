/** Temporary page body for screens that are not implemented yet. */
export function Placeholder({ title, description }: { title: string; description?: string }) {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-muted">{description ?? 'המסך בבנייה. ראו docs/recipe-screens.html.'}</p>
    </section>
  );
}
