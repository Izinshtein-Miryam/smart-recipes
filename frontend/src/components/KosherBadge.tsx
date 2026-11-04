import { useTranslation } from 'react-i18next';

import type { Kashrut } from '@/api/types';

const styles: Record<Kashrut, string> = {
  meat: 'bg-meat-soft text-meat',
  dairy: 'bg-dairy-soft text-dairy',
  parve: 'bg-parve-soft text-parve',
};

export function KosherBadge({ type }: { type: Kashrut }) {
  const { t } = useTranslation();
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-bold ${styles[type]}`}>
      {t(`kashrut.${type}`)}
    </span>
  );
}
