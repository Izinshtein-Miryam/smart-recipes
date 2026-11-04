import { screen } from '@testing-library/react';

import { renderRoute } from '@/test/utils';

const page = { items: [], total: 0, page: 1, page_size: 24 };

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(new Response(JSON.stringify(page), { status: 200 }))),
  );
});

afterEach(() => vi.unstubAllGlobals());

describe('router', () => {
  it('renders the home page inside the layout', async () => {
    renderRoute('/');
    expect(await screen.findByRole('heading', { name: 'מה מבשלים היום?' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'ניווט ראשי' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: "פתיחת צ'אט עוזר" })).toBeInTheDocument();
  });

  it('renders a not-found page for unknown paths', () => {
    renderRoute('/lorem-ipsum');
    expect(screen.getByRole('heading', { name: 'העמוד לא נמצא' })).toBeInTheDocument();
  });

  it('renders cooking mode without the main layout', () => {
    renderRoute('/cook/foo');
    expect(screen.getByRole('heading', { name: 'מצב בישול' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});
