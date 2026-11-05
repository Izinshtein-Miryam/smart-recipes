import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router';

import { LanguageSwitch } from './LanguageSwitch';

const links = [
  { to: '/', key: 'nav.recipes' },
  { to: '/fridge', key: 'nav.fridge' },
  { to: '/submit', key: 'nav.submit' },
];

export function Layout() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-surface border-line sticky top-0 z-10 border-b print:hidden">
        <nav
          aria-label={t('nav.label')}
          className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6"
        >
          <NavLink to="/" className="text-brand-hover font-serif text-2xl font-extrabold">
            🍳 {t('app.name')}
          </NavLink>
          <ul className="flex flex-1 flex-wrap items-center gap-x-6 gap-y-1 font-semibold">
            {links.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  end
                  className={({ isActive }) => (isActive ? 'text-brand' : 'hover:text-brand')}
                >
                  {t(l.key)}
                </NavLink>
              </li>
            ))}
          </ul>
          <LanguageSwitch />
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>
      <footer className="border-line bg-surface border-t py-6 print:hidden">
        <div className="mx-auto flex max-w-6xl justify-between px-6 text-sm">
          <span className="text-muted">{t('app.name')}</span>
          <NavLink to="/admin/login" className="text-muted hover:text-brand">
            {t('nav.admin')}
          </NavLink>
        </div>
      </footer>
    </div>
  );
}
