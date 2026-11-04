import type { KosherType } from '@/api/types';
import { kosherLabels } from '@/lib/labels';

const styles: Record<KosherType, string> = {
  meat: 'bg-meat-soft text-meat',
  dairy: 'bg-dairy-soft text-dairy',
  parve: 'bg-parve-soft text-parve',
};

export function KosherBadge({ type }: { type: KosherType }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-sm font-medium ${styles[type]}`}>
      {kosherLabels[type]}
    </span>
  );
}
