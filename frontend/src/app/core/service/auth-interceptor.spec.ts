import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from '../../auth/service/auth';
import { environment } from '../../../environments/environment';
import { authInterceptor } from './auth-interceptor';

describe('authInterceptor: alcance del token de acceso', () => {
  let http: HttpTestingController;
  let client: HttpClient;
  const auth = { token: vi.fn<() => string | null>() };

  beforeEach(() => {
    auth.token.mockReturnValue('example-access-token');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
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
