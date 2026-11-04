/** Mirrors backend Pydantic schemas (app/schemas). Keep in sync, or generate from /openapi.json. */

export type KosherType = 'meat' | 'dairy' | 'parve';
export type DishType = 'starter' | 'main' | 'side' | 'dessert' | 'baked';
export type Difficulty = 'easy' | 'medium' | 'hard';
export type Role = 'user' | 'content_manager' | 'sysadmin';

export interface RecipeCard {
  id: number;
  slug: string;
  title: string;
  description: string;
  kosher_type: KosherType;
  dish_type: DishType;
  difficulty: Difficulty;
  total_minutes: number;
  diet_tags: string[];
  source: 'admin' | 'ai';
  image_url: string | null;
}

export interface IngredientLine {
  ingredient_id: number;
  name: string;
  quantity: number | null;
  unit: string | null;
  note: string | null;
}

export interface Step {
  order: number;
  text: string;
  timer_seconds: number | null;
  ingredient_ids: number[];
}

export interface RecipeDetail extends RecipeCard {
  prep_minutes: number;
  cook_minutes: number;
  servings: number;
  base_servings: number;
  time_tags: string[];
  status: 'draft' | 'published' | 'hidden';
  ingredients: IngredientLine[];
  steps: Step[];
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  dietary_prefs: string[];
}
