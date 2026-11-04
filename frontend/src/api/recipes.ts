import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from './client';
import type { Page, RecipeCard, RecipeDetail } from './types';

export function useRecipes(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString();
  return useQuery({
    queryKey: ['recipes', params],
    queryFn: () => api<Page<RecipeCard>>(`/recipes${qs ? `?${qs}` : ''}`),
  });
}

export function useRecipe(slug: string, servings?: number) {
  return useQuery({
    queryKey: ['recipe', slug, servings],
    queryFn: () => api<RecipeDetail>(`/recipes/${slug}${servings ? `?servings=${servings}` : ''}`),
    // Keep showing the current quantities while a new serving count loads, instead of a spinner.
    placeholderData: keepPreviousData,
  });
}
