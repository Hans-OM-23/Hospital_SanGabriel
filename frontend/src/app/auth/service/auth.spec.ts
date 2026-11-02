import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth';

const storageKey = 'sgabriel.session';
const demoProfile = {
  id: 'usr-1',
  name: 'Administrador',
  email: 'admin@hospital.com',
  role: 'Responsable de almacén' as const,
};
const jwt = (seconds: number) => {
  const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds }));
  return `header.${payload}.signature`;
};

describe('AuthService: autenticación contra FastAPI', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-01T17:00:00Z'));
    sessionStorage.removeItem(storageKey);
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    http.verify();
    sessionStorage.removeItem(storageKey);
    vi.useRealTimers();
  });

  it('envía correo y contraseña a FastAPI, guarda un JWT vigente y permite salir', async () => {
    const pending = auth.login({ email: ' ADMIN@HOSPITAL.COM ', password: 'clave-local' });
    const request = http.expectOne(`${environment.apiUrl}/auth/login`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ email: 'admin@hospital.com', password: 'clave-local' });
    request.flush({ accessToken: jwt(1800), user: demoProfile });
    await pending;
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.hasValidSession()).toBe(true);
    expect(auth.user()).toEqual(demoProfile);
    expect(sessionStorage.getItem(storageKey)).not.toContain('clave-local');
    auth.logout();
    expect(auth.isAuthenticated()).toBe(false);
    expect(sessionStorage.getItem(storageKey)).toBeNull();
  });

  it('muestra un mensaje comprensible ante credenciales incorrectas', async () => {
    const pending = auth.login({ email: 'admin@hospital.com', password: 'incorrecta' });
    http.expectOne(`${environment.apiUrl}/auth/login`).flush(
      { detail: 'Usuario o contraseña incorrectos.' },
      { status: 401, statusText: 'Unauthorized' },
    );
    await expect(pending).rejects.toThrow('no son correctos');
    expect(auth.hasValidSession()).toBe(false);
  });

  it('restaura una sesión vigente y descarta tokens vencidos al cargar la página', () => {
    sessionStorage.setItem(storageKey, JSON.stringify({ accessToken: jwt(600), user: demoProfile }));
    const second = TestBed.runInInjectionContext(() => new AuthService());
    expect(second.hasValidSession()).toBe(true);
    sessionStorage.setItem(storageKey, JSON.stringify({ accessToken: jwt(-1), user: demoProfile }));
    const expired = TestBed.runInInjectionContext(() => new AuthService());
    expect(expired.hasValidSession()).toBe(false);
    expect(sessionStorage.getItem(storageKey)).toBeNull();
  });

  it('descarta el token al vencer sin exigir un nuevo comando o recarga', async () => {
    const pending = auth.login({ email: demoProfile.email, password: 'clave-local' });
    http.expectOne(`${environment.apiUrl}/auth/login`).flush({ accessToken: jwt(2), user: demoProfile });
    await pending;
    vi.advanceTimersByTime(3000);
    expect(auth.hasValidSession()).toBe(false);
    expect(auth.token()).toBeNull();
    expect(sessionStorage.getItem(storageKey)).toBeNull();
  });

  it('rechaza una respuesta de login sin JWT válido o sin datos de usuario', async () => {
    const pending = auth.login({ email: demoProfile.email, password: 'clave-local' });
    http.expectOne(`${environment.apiUrl}/auth/login`).flush({ accessToken: 'invalido', user: demoProfile });
    await expect(pending).rejects.toThrow('sesión incompleta');
    expect(auth.hasValidSession()).toBe(false);
  });
});
