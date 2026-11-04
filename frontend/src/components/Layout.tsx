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
      <header className="bg-surface border-line sticky top-0 z-10 border-b">
        <nav
          aria-label={t('nav.label')}
          className="mx-auto flex h-20 max-w-6xl items-center gap-8 px-6"
        >
          <NavLink to="/" className="text-brand-hover font-serif text-2xl font-extrabold">
            🍳 {t('app.name')}
          </NavLink>
          <ul className="flex flex-1 items-center gap-6 font-semibold">
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
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <Outlet />
      </main>
      <footer className="border-line bg-surface border-t py-6">
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
