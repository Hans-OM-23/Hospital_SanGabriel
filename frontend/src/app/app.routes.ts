import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './auth/service/auth-guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./auth/components/login/login').then((m) => m.Login),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/components/shell/shell').then((m) => m.Shell),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./dashboard/components/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'productos',
        loadComponent: () =>
          import('./products/components/product-list/product-list').then((m) => m.ProductList),
      },
      {
        path: 'productos/nuevo',
        loadComponent: () =>
          import('./products/components/product-form/product-form').then((m) => m.ProductForm),
      },
      {
        path: 'productos/:id/editar',
        loadComponent: () =>
          import('./products/components/product-form/product-form').then((m) => m.ProductForm),
      },
      {
        path: 'categorias',
        loadComponent: () =>
          import('./categories/components/category-list/category-list').then((m) => m.CategoryList),
      },
      {
        path: 'movimientos',
        loadComponent: () =>
          import('./movements/components/movement-form/movement-form').then((m) => m.MovementForm),
      },
      {
        path: 'historial',
        loadComponent: () => import('./history/components/history/history').then((m) => m.History),
      },
      {
        path: 'consultas',
        loadComponent: () =>
          import('./dashboard/components/dashboard/dashboard').then((m) => m.Dashboard),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
