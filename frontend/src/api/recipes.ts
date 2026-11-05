import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api, apiWithTotal } from './client';
import type { Recipe, RecipeFilters, RecipeSummary } from './types';

export function toQuery(filters: Record<string, unknown>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, String(v)));
    else params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export function useRecipes(filters: RecipeFilters = {}) {
  return useQuery({
    queryKey: ['recipes', filters],
    queryFn: () => apiWithTotal<RecipeSummary[]>(`/recipes${toQuery({ ...filters })}`),
    placeholderData: keepPreviousData,
  });
}

export function useRecipe(id: string | undefined, servings?: number) {
  return useQuery({
    queryKey: ['recipe', id, servings ?? null],
    queryFn: () => api<Recipe>(`/recipes/${id}${toQuery({ servings })}`),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  });
}
