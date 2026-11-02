import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../../auth/service/auth';
import { environment } from '../../../environments/environment';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();
  const isOwnApi = request.url.startsWith(`${environment.apiUrl}/`);
  const isLogin = request.url === `${environment.apiUrl}/auth/login`;
  const authorizedRequest = token && isOwnApi && !isLogin
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;

  return next(authorizedRequest).pipe(
    catchError((error: unknown) => {
      if (
        isOwnApi &&
        !isLogin &&
        error instanceof HttpErrorResponse &&
        error.status === 401
      ) {
        // Una sesión vencida no debe dejar la página inutilizable con 401.
        auth.logout();
        void router.navigateByUrl('/login');
      }
      return throwError(() => error);
    }),
  );
};
