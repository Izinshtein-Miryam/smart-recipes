import type { Difficulty, DishType, KosherType } from '@/api/types';

export const KOSHER_TYPES: readonly KosherType[] = ['meat', 'dairy', 'parve'];
export const DISH_TYPES: readonly DishType[] = ['starter', 'main', 'side', 'dessert', 'baked'];
export const DIFFICULTIES: readonly Difficulty[] = ['easy', 'medium', 'hard'];
export const MAX_MINUTES = ['15', '30', '60', '90'] as const;
export const DIET_TAGS = ['gluten_free', 'vegan', 'sugar_free', 'nut_free'] as const;
export type DietTag = (typeof DIET_TAGS)[number];

export const PAGE_SIZE = 12;

export interface SearchFilters {
  q: string;
  kosher_type: KosherType | '';
  dish_type: DishType | '';
  difficulty: Difficulty | '';
  max_minutes: (typeof MAX_MINUTES)[number] | '';
  diet: DietTag[];
  page: number;
}

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | '' {
  return allowed.includes(value as T) ? (value as T) : '';
}

/** Reads filters from the URL. Unknown or malformed values are ignored. */
export function parseFilters(params: URLSearchParams): SearchFilters {
  const page = Number.parseInt(params.get('page') ?? '1', 10);
  return {
    q: (params.get('q') ?? '').slice(0, 100),
    kosher_type: oneOf(params.get('kosher_type'), KOSHER_TYPES),
    dish_type: oneOf(params.get('dish_type'), DISH_TYPES),
    difficulty: oneOf(params.get('difficulty'), DIFFICULTIES),
    max_minutes: oneOf(params.get('max_minutes'), MAX_MINUTES),
    diet: DIET_TAGS.filter((tag) => params.getAll('diet').includes(tag)),
    page: Number.isFinite(page) && page > 1 ? page : 1,
  };
}

/** Builds the URL query string for the given filters. Empty values and page 1 are omitted. */
export function toUrlParams(filters: SearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set('q', filters.q.trim());
  if (filters.kosher_type) params.set('kosher_type', filters.kosher_type);
  if (filters.dish_type) params.set('dish_type', filters.dish_type);
  if (filters.difficulty) params.set('difficulty', filters.difficulty);
  if (filters.max_minutes) params.set('max_minutes', filters.max_minutes);
  filters.diet.forEach((tag) => params.append('diet', tag));
  if (filters.page > 1) params.set('page', String(filters.page));
  return params;
}

/** Query for GET /api/recipes: the URL params plus the page size. */
export function toApiParams(filters: SearchFilters): URLSearchParams {
  const params = toUrlParams(filters);
  params.set('page_size', String(PAGE_SIZE));
  return params;
}

export function hasActiveFilters(filters: SearchFilters): boolean {
  return Boolean(
    filters.q.trim() ||
    filters.kosher_type ||
    filters.dish_type ||
    filters.difficulty ||
    filters.max_minutes ||
    filters.diet.length,
  );
}
