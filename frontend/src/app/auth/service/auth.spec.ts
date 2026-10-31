import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { AuthService } from './auth';

describe('AuthService: acceso de demostración', () => {
  beforeEach(() => {
    sessionStorage.removeItem('sgabriel.demo-session');
    TestBed.configureTestingModule({ providers: [provideHttpClient()] });
  });

  it('rechaza credenciales incorrectas sin crear una sesión', async () => {
    const auth = TestBed.inject(AuthService);
    await expect(
      auth.login({ email: 'almacen@sgabriel.pe', password: 'incorrecta' }),
    ).rejects.toThrow('no son correctos');
    expect(auth.isAuthenticated()).toBe(false);
    expect(sessionStorage.getItem('sgabriel.demo-session')).toBeNull();
  });

  it('guarda el perfil y token, nunca la contraseña, y cierra la sesión', async () => {
    const auth = TestBed.inject(AuthService);
    await auth.login({ email: 'almacen@sgabriel.pe', password: 'SanGabriel2026!' });
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.user()?.role).toBe('Responsable de almacén');
    const stored = sessionStorage.getItem('sgabriel.demo-session')!;
    expect(stored).not.toContain('SanGabriel2026!');
    expect(stored).not.toContain('password');
    expect(auth.token()).toBeTruthy();
    auth.logout();
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.token()).toBeNull();
    expect(sessionStorage.getItem('sgabriel.demo-session')).toBeNull();
  });

  it('ignora sesiones manipuladas o incompletas al cargar', () => {
    sessionStorage.setItem(
      'sgabriel.demo-session',
      JSON.stringify({ user: { role: 'Administrador' } }),
    );
    const auth = TestBed.inject(AuthService);
    expect(auth.isAuthenticated()).toBe(false);
    expect(sessionStorage.getItem('sgabriel.demo-session')).toBeNull();
  });
});
