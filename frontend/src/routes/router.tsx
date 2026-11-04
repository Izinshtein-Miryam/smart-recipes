import { createBrowserRouter, Navigate, type RouteObject } from 'react-router';

import { Layout } from '@/components/Layout';
import { HomePage } from '@/pages/HomePage';
import * as P from '@/pages/placeholders';
import { RecipePage } from '@/pages/RecipePage';

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'search', element: <P.SearchPage /> },
      { path: 'recipe/:slug', element: <RecipePage /> },
      { path: 'generate', element: <P.GeneratePage /> },
      { path: 'shopping', element: <P.ShoppingPage /> },
      { path: 'favorites', element: <P.FavoritesPage /> },
      { path: 'login', element: <P.LoginPage /> },
      { path: 'admin', element: <P.AdminRecipesPage /> },
      { path: 'admin/edit/:id', element: <P.AdminEditRecipePage /> },
      { path: 'system', element: <Navigate to="/system/users" replace /> },
      { path: 'system/users', element: <P.SystemUsersPage /> },
      { path: 'system/settings', element: <P.SystemSettingsPage /> },
      { path: 'system/stats', element: <P.SystemStatsPage /> },
      { path: 'system/audit', element: <P.SystemAuditPage /> },
      { path: '*', element: <P.NotFoundPage /> },
    ],
  },
  // Cooking mode is full screen, outside the main layout.
  { path: 'cook/:slug', element: <P.CookPage /> },
];

export const router = createBrowserRouter(routes);
