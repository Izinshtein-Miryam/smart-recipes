import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

import type { DishType, RecipeCard as RecipeCardData } from '@/api/types';

import { RecipeCard } from './RecipeCard';

const base: RecipeCardData = {
  id: 1,
  slug: 'foo',
  title: 'Lorem ipsum',
  description: 'Dolor sit amet',
  kosher_type: 'parve',
  dish_type: 'main',
  difficulty: 'easy',
  total_minutes: 30,
  diet_tags: [],
  source: 'admin',
};

function renderCard(overrides: Partial<RecipeCardData> = {}) {
  return render(
    <MemoryRouter>
      <RecipeCard recipe={{ ...base, ...overrides }} />
    </MemoryRouter>,
  );
}

describe('RecipeCard', () => {
  it.each(['starter', 'main', 'side', 'dessert', 'baked'] as DishType[])(
    'renders an icon for dish type %s',
    (dish_type) => {
      renderCard({ dish_type });
      expect(screen.getByTestId('dish-icon')).toHaveAttribute('data-dish', dish_type);
    },
  );

  it('shows the AI badge only when source is ai', () => {
    const { unmount } = renderCard({ source: 'ai' });
    expect(screen.getByText('נוצר ב-AI')).toBeInTheDocument();
    unmount();
    renderCard({ source: 'admin' });
    expect(screen.queryByText('נוצר ב-AI')).not.toBeInTheDocument();
  });
});
