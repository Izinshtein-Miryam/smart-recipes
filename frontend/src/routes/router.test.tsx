import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { renderRoute } from '@/test/utils';

const recipe = {
  id: '00000000-0000-0000-0000-000000000001',
  lang: 'he',
  title: 'foo',
  description: 'Lorem ipsum dolor sit amet',
  servings: 4,
  prep_minutes: 30,
  difficulty: 'easy',
  equipment: ['oven'],
  kashrut: 'parve',
  image_url: null,
};

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(() =>
    Promise.resolve(new Response(JSON.stringify([recipe]), { status: 200 })),
  );
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe('router', () => {
  it('renders the home page with approved recipes in the selected language', async () => {
    renderRoute('/');
    expect(await screen.findByRole('heading', { name: 'foo' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'ניווט ראשי' })).toBeInTheDocument();
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/recipes?lang=he&limit=12&offset=0');
  });

  it('renders the fridge search screen', () => {
    renderRoute('/fridge');
    expect(screen.getByRole('heading', { name: 'מה יש לי במקרר' })).toBeInTheDocument();
  });

  it('renders a not-found page for unknown paths', () => {
    renderRoute('/lorem-ipsum');
    expect(screen.getByRole('heading', { name: 'העמוד לא נמצא' })).toBeInTheDocument();
  });

  it('switches language and flips the document direction', async () => {
    renderRoute('/fridge');
    expect(document.documentElement.dir).toBe('rtl');

    await userEvent.click(screen.getByRole('button', { name: 'English' }));

    expect(document.documentElement.dir).toBe('ltr');
    expect(document.documentElement.lang).toBe('en');
    expect(screen.getByRole('heading', { name: "What's in my fridge" })).toBeInTheDocument();
  });
});
