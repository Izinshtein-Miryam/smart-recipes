import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { RecipeDetail } from '@/api/types';
import { renderRoute } from '@/test/utils';

function recipe(servings: number): RecipeDetail {
  return {
    id: 1,
    slug: 'foo',
    title: 'Lorem ipsum',
    description: 'Dolor sit amet',
    kosher_type: 'parve',
    dish_type: 'main',
    difficulty: 'easy',
    total_minutes: 10,
    diet_tags: [],
    source: 'admin',
    prep_minutes: 5,
    cook_minutes: 5,
    servings,
    time_tags: [],
    ingredients: [
      { ingredient_id: 1, name: 'bar', quantity: servings * 100, unit: 'גרם', note: null },
      { ingredient_id: 2, name: 'baz', quantity: null, unit: null, note: null },
    ],
    steps: [{ order: 1, text: 'Lorem', timer_seconds: null, ingredient_ids: [] }],
    created_at: '2026-01-01T00:00:00Z',
  };
}

const fetchMock = vi.fn((input: string) => {
  const servings = Number(new URL(input, 'http://x').searchParams.get('servings') ?? 2);
  return Promise.resolve(new Response(JSON.stringify(recipe(servings)), { status: 200 }));
});

beforeEach(() => {
  fetchMock.mockClear();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe('RecipePage servings stepper', () => {
  it('starts at the recipe base servings', async () => {
    renderRoute('/recipe/foo');
    const group = await screen.findByRole('group', { name: 'מספר מנות' });
    expect(group).toHaveTextContent('2');
    expect(screen.getByText(/200 גרם bar/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/recipes/foo', expect.anything());
  });

  it('refetches with ?servings= and updates quantities in place', async () => {
    const user = userEvent.setup();
    renderRoute('/recipe/foo');
    await user.click(await screen.findByRole('button', { name: 'הוספת מנה' }));

    expect(await screen.findByText(/300 גרם bar/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith('/api/recipes/foo?servings=3', expect.anything());
    // Heading stays mounted: no full-page loading state between counts.
    expect(screen.getByRole('heading', { name: 'Lorem ipsum' })).toBeInTheDocument();
  });

  it('does not go below one serving', async () => {
    const user = userEvent.setup();
    renderRoute('/recipe/foo');
    const minus = await screen.findByRole('button', { name: 'הפחתת מנה' });
    await user.click(minus);
    await waitFor(() => expect(minus).toBeDisabled());
    expect(screen.getByRole('group', { name: 'מספר מנות' })).toHaveTextContent('1');
    await user.click(minus);
    expect(fetchMock).not.toHaveBeenCalledWith('/api/recipes/foo?servings=0', expect.anything());
  });

  it('is operable with the keyboard', async () => {
    const user = userEvent.setup();
    renderRoute('/recipe/foo');
    await screen.findByRole('group', { name: 'מספר מנות' });
    const plus = screen.getByRole('button', { name: 'הוספת מנה' });
    plus.focus();
    await user.keyboard('{Enter}');
    await user.keyboard(' ');
    expect(await screen.findByText(/400 גרם bar/)).toBeInTheDocument();
  });
});
