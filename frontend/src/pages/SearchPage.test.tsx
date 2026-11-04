import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Page, RecipeCard } from '@/api/types';
import { routes } from '@/routes/router';

function card(id: number, title: string): RecipeCard {
  return {
    id,
    slug: `recipe-${id}`,
    title,
    description: 'lorem ipsum',
    kosher_type: 'parve',
    dish_type: 'main',
    difficulty: 'easy',
    total_minutes: 20,
    diet_tags: [],
    source: 'admin',
  };
}

function page(items: RecipeCard[], total = items.length, pageNo = 1): Page<RecipeCard> {
  return { items, total, page: pageNo, page_size: 12 };
}

let requested: string[] = [];
let respond: (url: string) => Page<RecipeCard>;

beforeEach(() => {
  requested = [];
  respond = () => page([card(1, 'foo'), card(2, 'bar')]);
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      requested.push(url);
      return Promise.resolve(new Response(JSON.stringify(respond(url)), { status: 200 }));
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

function renderSearch(path = '/search') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe('SearchPage', () => {
  it('shows a loading state and then the results', async () => {
    renderSearch();
    expect(screen.getByText('טוען…')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'foo' })).toBeInTheDocument();
    expect(screen.getByText('נמצאו 2 מתכונים')).toBeInTheDocument();
    expect(requested[0]).toBe('/api/recipes?page_size=12');
  });

  it('reads the initial filters from the URL', async () => {
    renderSearch('/search?kosher_type=dairy&diet=vegan&max_minutes=30&page=2');
    await screen.findByRole('link', { name: 'foo' });
    expect(screen.getByLabelText('סוג')).toHaveValue('dairy');
    expect(screen.getByLabelText('זמן מקסימלי')).toHaveValue('30');
    expect(screen.getByRole('checkbox', { name: 'טבעוני' })).toBeChecked();
    expect(requested[0]).toContain('kosher_type=dairy');
    expect(requested[0]).toContain('diet=vegan');
    expect(requested[0]).toContain('page=2');
  });

  it('updates the URL and the results when a filter changes', async () => {
    const user = userEvent.setup();
    const router = renderSearch('/search?page=2');
    await screen.findByRole('link', { name: 'foo' });

    await user.selectOptions(screen.getByLabelText('סוג מנה'), 'dessert');
    await waitFor(() => expect(router.state.location.search).toBe('?dish_type=dessert'));
    await waitFor(() => expect(requested.at(-1)).toContain('dish_type=dessert'));
    expect(requested.at(-1)).not.toContain('page=');

    await user.click(screen.getByRole('checkbox', { name: 'ללא גלוטן' }));
    await user.click(screen.getByRole('checkbox', { name: 'טבעוני' }));
    await waitFor(() =>
      expect(router.state.location.search).toBe('?dish_type=dessert&diet=gluten_free&diet=vegan'),
    );
    await waitFor(() => expect(requested.at(-1)).toContain('diet=gluten_free&diet=vegan'));
  });

  it('searches by name on submit', async () => {
    const user = userEvent.setup();
    const router = renderSearch();
    await screen.findByRole('link', { name: 'foo' });
    await user.type(screen.getByRole('searchbox'), 'baz{Enter}');
    await waitFor(() => expect(router.state.location.search).toBe('?q=baz'));
  });

  it('shows an empty state and clears all filters', async () => {
    respond = (url) => (url.includes('dish_type') ? page([]) : page([card(1, 'foo')]));
    const user = userEvent.setup();
    const router = renderSearch('/search?dish_type=dessert');
    expect(await screen.findByText('לא נמצאו מתכונים')).toBeInTheDocument();
    expect(screen.queryByRole('article')).not.toBeInTheDocument();

    await user.click(
      screen.getAllByRole('button', { name: 'נקה את כל המסננים' }).at(0) as HTMLElement,
    );
    await waitFor(() => expect(router.state.location.search).toBe(''));
    expect(await screen.findByRole('link', { name: 'foo' })).toBeInTheDocument();
  });

  it('shows an error message when loading fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('{}', { status: 500 }))),
    );
    renderSearch();
    expect(await screen.findByRole('alert')).toHaveTextContent('שגיאה בטעינת המתכונים');
  });

  it('paginates with previous and next buttons', async () => {
    respond = (url) => {
      const p = Number(new URL(url, 'http://x').searchParams.get('page') ?? 1);
      return page([card(p, `recipe page ${p}`)], 30, p);
    };
    const user = userEvent.setup();
    const router = renderSearch();
    expect(await screen.findByText('עמוד 1 מתוך 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'הקודם' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'הבא' }));
    await waitFor(() => expect(router.state.location.search).toBe('?page=2'));
    expect(await screen.findByRole('link', { name: 'recipe page 2' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'הבא' }));
    expect(await screen.findByText('עמוד 3 מתוך 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'הבא' })).toBeDisabled();
  });
});
