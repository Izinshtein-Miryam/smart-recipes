/** Mirrors backend/app/schemas. Keep in sync when the API changes. */

export type Lang = 'he' | 'en';
export type Difficulty = 'easy' | 'medium' | 'hard';
export type Equipment = 'oven' | 'stovetop' | 'one_pot' | 'no_cook';
export type Kashrut = 'meat' | 'dairy' | 'parve';
export type RecipeStatus = 'pending' | 'approved' | 'rejected';

export interface Ingredient {
  name: string;
  quantity: number | null;
  unit: string | null;
  note: string | null;
}

export interface Nutrition {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  confidence: 'low' | 'medium' | 'high' | null;
}

export interface RecipeSummary {
  id: string;
  lang: Lang;
  title: string;
  description: string;
  servings: number;
  prep_minutes: number;
  difficulty: Difficulty;
  equipment: Equipment[];
  kashrut: Kashrut;
  image_url: string | null;
}

export interface Recipe extends RecipeSummary {
  ingredients: Ingredient[];
  steps: string[];
  nutrition: Nutrition | null;
  status: RecipeStatus;
  source_recipe_id: string | null;
  created_at: string;
  approved_at: string | null;
}

export interface RecipeFilters {
  lang?: Lang;
  q?: string;
  max_minutes?: number;
  difficulty?: Difficulty;
  equipment?: Equipment[];
  servings?: number;
  kashrut?: Kashrut;
  limit?: number;
  offset?: number;
}

export interface RecipeContent {
  title: string;
  description: string;
  servings: number;
  prep_minutes: number;
  difficulty: Difficulty;
  equipment: Equipment[];
  kashrut: Kashrut;
  ingredients: Ingredient[];
  steps: string[];
}

export interface AdaptedRecipe extends RecipeContent {
  changes_summary: string[];
  feasible: boolean;
  reason: string | null;
}

export interface FridgeSearchItem {
  recipe: RecipeSummary;
  match_score: number;
  missing_ingredients: string[];
}
