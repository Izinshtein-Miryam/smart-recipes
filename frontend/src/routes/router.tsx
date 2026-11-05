import { createBrowserRouter, type RouteObject } from 'react-router';

import { Layout } from '@/components/Layout';
import { Placeholder } from '@/components/Placeholder';
import { AdaptedRecipePage } from '@/pages/AdaptedRecipePage';
import { AdminLoginPage } from '@/pages/AdminLoginPage';
import { AdminQueuePage } from '@/pages/AdminQueuePage';
import { CookPage } from '@/pages/CookPage';
import { FridgePage } from '@/pages/FridgePage';
import { HomePage } from '@/pages/HomePage';
import { RecipePage } from '@/pages/RecipePage';
import { SubmitPage } from '@/pages/SubmitPage';

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'fridge', element: <FridgePage /> },
      { path: 'recipes/:id', element: <RecipePage /> },
      { path: 'recipes/:id/cook', element: <CookPage /> },
      { path: 'recipes/:id/adapted', element: <AdaptedRecipePage /> },
      { path: 'submit', element: <SubmitPage /> },
      { path: 'admin/login', element: <AdminLoginPage /> },
      { path: 'admin/queue', element: <AdminQueuePage /> },
      { path: '*', element: <Placeholder titleKey="notFound.title" /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
