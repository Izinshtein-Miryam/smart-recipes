import type { Difficulty, DishType, KosherType } from '@/api/types';

export const kosherLabels: Record<KosherType, string> = {
  meat: 'בשרי',
  dairy: 'חלבי',
  parve: 'פרווה',
};

export const dishLabels: Record<DishType, string> = {
  starter: 'ראשונה',
  main: 'עיקרית',
  side: 'תוספת',
  dessert: 'קינוח',
  baked: 'מאפה',
};

export const difficultyLabels: Record<Difficulty, string> = {
  easy: 'קל',
  medium: 'בינוני',
  hard: 'מאתגר',
};
