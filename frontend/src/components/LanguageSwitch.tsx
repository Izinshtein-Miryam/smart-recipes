import { useTranslation } from 'react-i18next';

export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
  const next = i18n.language === 'he' ? 'en' : 'he';
  return (
    <button
      type="button"
      lang={next}
      onClick={() => void i18n.changeLanguage(next)}
      className="border-line hover:border-brand hover:text-brand rounded-full border px-4 py-1.5 text-sm font-semibold"
    >
      {t('lang.switchTo')}
    </button>
  );
}
