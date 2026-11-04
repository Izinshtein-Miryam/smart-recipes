import { useTranslation } from 'react-i18next';

/** Stand-in for screens that are not built yet. */
export function Placeholder({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-3xl">{t(titleKey)}</h1>
      <p className="text-muted">{t('common.comingSoon')}</p>
    </section>
  );
}
