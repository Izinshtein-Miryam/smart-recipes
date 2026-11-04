import { useQuery } from '@tanstack/react-query';

import { api } from './client';
import type { Recipe, RecipeFilters, RecipeSummary } from './types';

function toQuery(filters: RecipeFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === '') continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export function useRecipes(filters: RecipeFilters = {}) {
  return useQuery({
    queryKey: ['recipes', filters],
    queryFn: () => api<RecipeSummary[]>(`/recipes${toQuery(filters)}`),
  });
}

export function useRecipe(id: string | undefined) {
  return useQuery({
    queryKey: ['recipe', id],
    queryFn: () => api<Recipe>(`/recipes/${id}`),
    enabled: Boolean(id),
  });
}
