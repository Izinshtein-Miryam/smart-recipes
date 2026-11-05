import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';

import { renderRoute } from '@/test/utils';

const recipe = {
  id: '00000000-0000-0000-0000-000000000001',
  lang: 'he',
  title: 'foo',
  description: 'Lorem ipsum',
  servings: 4,
  prep_minutes: 30,
  difficulty: 'easy',
  equipment: ['oven'],
  kashrut: 'parve',
  image_url: null,
  ingredients: [{ name: 'bar', quantity: 2, unit: 'g', note: null }],
  steps: ['baz 10 דקות', 'qux'],
  nutrition: null,
  status: 'approved',
  source_recipe_id: null,
  created_at: '2026-01-01T00:00:00Z',
  approved_at: null,
};

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation((url: string) => {
    const json = (x: unknown) => Promise.resolve(new Response(JSON.stringify(x), { status: 200 }));
    if (url.startsWith('/api/recipes?')) return json([recipe]);
    if (url.startsWith('/api/recipes/')) {
      const servings = /servings=(\d+)/.exec(url)?.[1];
      return json(
        servings
          ? {
              ...recipe,
              servings: Number(servings),
              ingredients: [{ ...recipe.ingredients[0], quantity: 4 }],
            }
          : recipe,
      );
    }
    return Promise.resolve(new Response('{}', { status: 404 }));
  });
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

async function violations(container: HTMLElement) {
  const res = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } });
  return res.violations.map((v) => v.id);
}

describe('home filters', () => {
  it('updates the URL-backed query when a filter changes', async () => {
    renderRoute('/');
    await screen.findByRole('heading', { name: 'foo' });
    await userEvent.selectOptions(screen.getByLabelText('כשרות'), 'dairy');
    await waitFor(() =>
      expect(fetchMock.mock.calls.some((c) => String(c[0]).includes('kashrut=dairy'))).toBe(true),
    );
  });

  it('has no axe violations', async () => {
    const { container } = renderRoute('/');
    await screen.findByRole('heading', { name: 'foo' });
    expect(await violations(container)).toEqual([]);
  });
});

describe('recipe page', () => {
  it('recalculates quantities through the API when servings change', async () => {
    const { container } = renderRoute(`/recipes/${recipe.id}`);
    await screen.findByRole('heading', { name: 'foo' });
    expect(await violations(container)).toEqual([]);
    await userEvent.click(screen.getByRole('button', { name: 'יותר מנות' }));
    await waitFor(() => expect(screen.getByText(/5 מנות/)).toBeInTheDocument());
    expect(fetchMock.mock.calls.some((c) => String(c[0]).endsWith('?servings=5'))).toBe(true);
  });

  it('disables decreasing below one serving', async () => {
    renderRoute(`/recipes/${recipe.id}`);
    await screen.findByRole('heading', { name: 'foo' });
    for (let i = 0; i < 3; i++)
      await userEvent.click(screen.getByRole('button', { name: 'פחות מנות' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'פחות מנות' })).toBeDisabled());
  });

  it('shows a 404 page for an unknown recipe', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(new Response('{}', { status: 404 })));
    renderRoute(`/recipes/${recipe.id}`);
    expect(await screen.findByText('המתכון לא נמצא')).toBeInTheDocument();
  });
});

describe('cook mode', () => {
  it('moves between steps and shows a timer for timed steps', async () => {
    renderRoute(`/recipes/${recipe.id}/cook`);
    expect(await screen.findByText('baz 10 דקות')).toBeInTheDocument();
    expect(screen.getByText('10:00')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'הבא' }));
    expect(screen.getByText('qux')).toBeInTheDocument();
    expect(screen.queryByText('10:00')).not.toBeInTheDocument();
    await userEvent.keyboard('{ArrowRight}'); // RTL: right arrow goes back
    expect(screen.getByText('baz 10 דקות')).toBeInTheDocument();
  });
});

describe('other screens', () => {
  it('renders the submit form and the admin login without axe violations', async () => {
    const a = renderRoute('/submit');
    await screen.findByRole('heading', { name: 'הגשת מתכון' });
    expect(await violations(a.container)).toEqual([]);
    a.unmount();
    const b = renderRoute('/admin/login');
    await screen.findByRole('heading', { name: 'כניסת מנהל' });
    expect(await violations(b.container)).toEqual([]);
  });

  it('fridge search shows the missing ingredient tag', async () => {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        new Response(
          JSON.stringify(
            url.includes('fridge-search')
              ? { results: [{ recipe, match_score: 80, missing_ingredients: ['baz'] }] }
              : {},
          ),
          { status: 200 },
        ),
      ),
    );
    renderRoute('/fridge');
    await userEvent.type(screen.getByRole('textbox', { name: 'מצרכים' }), 'bar{Enter}');
    await userEvent.click(screen.getByRole('button', { name: 'חפש מתכונים' }));
    expect(await screen.findByText('חסר: baz')).toBeInTheDocument();
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });
});
