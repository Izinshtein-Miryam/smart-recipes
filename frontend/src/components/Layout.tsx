import { NavLink, Outlet } from 'react-router';

const links = [
  { to: '/', label: 'בית' },
  { to: '/search', label: 'חיפוש' },
  { to: '/generate', label: 'יצירה חכמה' },
  { to: '/favorites', label: 'מועדפים' },
  { to: '/shopping', label: 'רשימת קניות' },
];

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="bg-surface border-line no-print border-b">
        <nav
          aria-label="ניווט ראשי"
          className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3"
        >
          <NavLink to="/" className="text-brand text-xl font-bold">
            מתכונים חכם
          </NavLink>
          <ul className="flex flex-wrap gap-3">
            {links.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  end
                  className={({ isActive }) => (isActive ? 'text-brand font-medium' : 'text-ink')}
                >
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <NavLink to="/login" className="ms-auto">
            התחברות
          </NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
      {/* Assistant chat - opens a side panel (feature 1.3). */}
      <button
        type="button"
        aria-label="פתיחת צ'אט עוזר"
        className="bg-brand text-brand-ink shadow-card no-print fixed bottom-5 left-5 rounded-full px-5 py-3"
      >
        עוזר
      </button>
    </div>
  );
}
