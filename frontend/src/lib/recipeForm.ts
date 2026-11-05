import type { Lang, RecipeContent } from '@/api/types';

export type FormValue = RecipeContent & { lang: Lang };

export const EMPTY_RECIPE: FormValue = {
  lang: 'he',
  title: '',
  description: '',
  servings: 4,
  prep_minutes: 30,
  difficulty: 'easy',
  equipment: [],
  kashrut: 'parve',
  ingredients: [{ name: '', quantity: null, unit: null, note: null }],
  steps: [''],
};
