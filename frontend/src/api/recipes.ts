import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from './client';
import type { Page, RecipeCard, RecipeDetail } from './types';

export function useRecipes(params: Record<string, string> | URLSearchParams = {}) {
  const qs = new URLSearchParams(params).toString();
  return useQuery({
    queryKey: ['recipes', qs],
    queryFn: () => api<Page<RecipeCard>>(`/recipes${qs ? `?${qs}` : ''}`),
    // Keep showing the previous results while a new filter combination loads.
    placeholderData: keepPreviousData,
  });
}

export function useRecipe(slug: string, servings?: number) {
  return useQuery({
    queryKey: ['recipe', slug, servings],
    queryFn: () => api<RecipeDetail>(`/recipes/${slug}${servings ? `?servings=${servings}` : ''}`),
  });
}
