import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from '../../auth/service/auth';
import { environment } from '../../../environments/environment';
import { authInterceptor } from './auth-interceptor';

describe('authInterceptor: alcance del token de acceso', () => {
  let http: HttpTestingController;
  let client: HttpClient;
  const auth = { token: vi.fn<() => string | null>(), logout: vi.fn() };
  const router = { navigateByUrl: vi.fn().mockResolvedValue(true) };

  beforeEach(() => {
    auth.token.mockReturnValue('example-access-token');
    auth.logout.mockReset();
    router.navigateByUrl.mockClear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    client = TestBed.inject(HttpClient);
  });
  afterEach(() => http.verify());

  it('agrega Bearer a la API propia conservando las demás cabeceras', async () => {
    const url = `${environment.apiUrl}/products`;
    const pending = firstValueFrom(client.get(url, { headers: { 'X-Trace': 'inventory' } }));
    const request = http.expectOne(url);
    expect(request.request.headers.get('Authorization')).toBe('Bearer example-access-token');
    expect(request.request.headers.get('X-Trace')).toBe('inventory');
    request.flush([]);
    await pending;
  });

  it('no envía el token a servicios de terceros ni URLs con un prefijo parecido', async () => {
    for (const url of [
      'https://third-party.example/products',
      `${environment.apiUrl}-other/products`,
    ]) {
      const pending = firstValueFrom(client.get(url));
      const request = http.expectOne(url);
      expect(request.request.headers.has('Authorization')).toBe(false);
      request.flush([]);
      await pending;
    }
  });

  it('cierra la sesión y vuelve al login cuando FastAPI devuelve 401', async () => {
    const url = `${environment.apiUrl}/products`;
    const pending = firstValueFrom(client.get(url));
    http.expectOne(url).flush(
      { detail: 'El token de acceso no es válido o ha expirado.' },
      { status: 401, statusText: 'Unauthorized' },
    );
    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(auth.logout).toHaveBeenCalledOnce();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/login');
  });

  it('no cierra sesión por un 401 del propio formulario de login', async () => {
    const url = `${environment.apiUrl}/auth/login`;
    const pending = firstValueFrom(client.post(url, { email: 'x@y.com', password: 'mal' }));
    const request = http.expectOne(url);
    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({}, { status: 401, statusText: 'Unauthorized' });
    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(auth.logout).not.toHaveBeenCalled();
  });

  it('consulta el token vigente y deja de enviarlo cuando se cierra la sesión', async () => {
    auth.token.mockReturnValue(null);
    const url = `${environment.apiUrl}/products`;
    const pending = firstValueFrom(client.get(url));
    const request = http.expectOne(url);
    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush([]);
    await pending;
  });
});
