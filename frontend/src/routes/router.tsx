import { createBrowserRouter, type RouteObject } from 'react-router';

import { Layout } from '@/components/Layout';
import { HomePage } from '@/pages/HomePage';
import * as P from '@/pages/placeholders';
import { RecipePage } from '@/pages/RecipePage';

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'fridge', element: <P.FridgePage /> },
      { path: 'recipes/:id', element: <RecipePage /> },
      { path: 'recipes/:id/adapted', element: <P.AdaptedRecipePage /> },
      { path: 'submit', element: <P.SubmitPage /> },
      { path: 'admin/login', element: <P.AdminLoginPage /> },
      { path: 'admin/queue', element: <P.AdminQueuePage /> },
      { path: '*', element: <P.NotFoundPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
