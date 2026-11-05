import { api } from './client';
import type { Recipe, RecipeContent, RecipeStatus, Lang } from './types';

export const adminLogin = (password: string) =>
  api<{ access_token: string }>('/admin/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });

export const adminList = (status: RecipeStatus, q: string) =>
  api<Recipe[]>(`/admin/recipes?status=${status}${q ? `&q=${encodeURIComponent(q)}` : ''}`);

export const adminUpdate = (id: string, body: RecipeContent & { lang: Lang }) =>
  api<Recipe>(`/admin/recipes/${id}`, { method: 'PUT', body: JSON.stringify(body) });

export const adminApprove = (id: string) =>
  api<Recipe>(`/admin/recipes/${id}/approve`, { method: 'POST' });

export const adminReject = (id: string) =>
  api<Recipe>(`/admin/recipes/${id}/reject`, { method: 'POST' });

export function submitRecipe(
  body: RecipeContent & { lang: Lang; source_recipe_id?: string },
  image?: File | null,
) {
  const form = new FormData();
  const { ingredients, steps, equipment, source_recipe_id, ...rest } = body;
  for (const [k, v] of Object.entries(rest)) form.set(k, String(v));
  equipment.forEach((e) => form.append('equipment', e));
  form.set('ingredients', JSON.stringify(ingredients));
  form.set('steps', JSON.stringify(steps));
  if (source_recipe_id) form.set('source_recipe_id', source_recipe_id);
  if (image) form.set('image', image);
  return api<Recipe>('/recipes', { method: 'POST', body: form });
}
