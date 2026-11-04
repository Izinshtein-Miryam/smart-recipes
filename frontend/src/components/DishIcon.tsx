import type { ReactNode } from 'react';

import type { DishType } from '@/api/types';
import { dishLabels } from '@/lib/labels';

const paths: Record<DishType, ReactNode> = {
  // bowl with steam
  starter: (
    <>
      <path d="M4 12h16a8 8 0 0 1-16 0Z" />
      <path d="M9 4c-1 1.5 1 2.5 0 4M15 4c-1 1.5 1 2.5 0 4" />
    </>
  ),
  // plate with fork and knife
  main: (
    <>
      <circle cx="12" cy="12" r="5" />
      <path d="M3 4v6M5 4v6M3 10h2M4 10v10M20 4c-2 1-2 5 0 6v10" />
    </>
  ),
  // small dish with leaves
  side: (
    <>
      <path d="M3 14h18M5 14a7 5 0 0 0 14 0" />
      <path d="M8 11c0-3 2-4 4-4 0 3-1 4-4 4ZM12 11c0-3 2-4 4-4 0 3-1 4-4 4Z" />
    </>
  ),
  // cake slice
  dessert: (
    <>
      <path d="M3 20h18v-6H3ZM5 14v-3h14v3" />
      <path d="M8 11V8M12 11V7M16 11V8" />
    </>
  ),
  // bread loaf
  baked: (
    <>
      <path d="M5 11a4 4 0 0 1 3-6h8a4 4 0 0 1 3 6v8H5Z" />
      <path d="M9 9l1 3M13 9l1 3" />
    </>
  ),
};

export function DishIcon({ type, className }: { type: DishType; className?: string }) {
  return (
    <svg
      role="img"
      aria-label={dishLabels[type]}
      data-testid="dish-icon"
      data-dish={type}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {paths[type]}
    </svg>
  );
}
