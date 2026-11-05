import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import he from './he.json';

export const languages = ['he', 'en'] as const;
export type Language = (typeof languages)[number];

const STORAGE_KEY = 'lang';

function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'he' || saved === 'en') return saved;
  } catch {
    /* storage unavailable */
  }
  return 'he';
}

/** Hebrew is RTL, English is LTR; the document direction follows the language. */
export function applyDirection(lng: string): void {
  document.documentElement.lang = lng;
  document.documentElement.dir = lng === 'he' ? 'rtl' : 'ltr';
}

void i18n.use(initReactI18next).init({
  resources: { he: { translation: he }, en: { translation: en } },
  lng: initialLanguage(),
  fallbackLng: 'he',
  interpolation: { escapeValue: false },
});

i18n.on('languageChanged', (lng) => {
  applyDirection(lng);
  try {
    localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    /* storage unavailable */
  }
});
applyDirection(i18n.language);

export default i18n;
