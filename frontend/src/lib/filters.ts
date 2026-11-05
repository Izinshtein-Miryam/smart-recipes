import type { Difficulty, Equipment, Kashrut } from '@/api/types';

export interface FilterValues {
  q: string;
  kashrut: Kashrut | '';
  difficulty: Difficulty | '';
  max_minutes: string;
  equipment: Equipment | '';
  servings: string;
}

export const EMPTY_FILTERS: FilterValues = {
  q: '',
  kashrut: '',
  difficulty: '',
  max_minutes: '',
  equipment: '',
  servings: '',
};
