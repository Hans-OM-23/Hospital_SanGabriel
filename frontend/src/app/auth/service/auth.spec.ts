import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { AuthService } from './auth';
import { DEMO_PASSWORD, DEMO_USERS } from './demo-users';

describe('AuthService: acceso de demostración', () => {
  beforeEach(() => {
    sessionStorage.removeItem('sgabriel.demo-session');
    TestBed.configureTestingModule({ providers: [provideHttpClient()] });
  });

  it('rechaza credenciales incorrectas sin crear una sesión', async () => {
    const auth = TestBed.inject(AuthService);
    await expect(
      auth.login({ email: DEMO_USERS[0].email, password: 'incorrecta' }),
    ).rejects.toThrow('no son correctos');
    expect(auth.isAuthenticated()).toBe(false);
    expect(sessionStorage.getItem('sgabriel.demo-session')).toBeNull();
  });

  it('guarda el perfil y token, nunca la contraseña, y cierra la sesión', async () => {
    const auth = TestBed.inject(AuthService);
    await auth.login({ email: DEMO_USERS[0].email, password: DEMO_PASSWORD });
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

  it.each(DEMO_USERS)('inicia sesión con la identidad de $name', async (user) => {
    const auth = TestBed.inject(AuthService);
    await auth.login({ email: `  ${user.email.toUpperCase()}  `, password: DEMO_PASSWORD });
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.user()).toEqual(user);
    expect(JSON.parse(sessionStorage.getItem('sgabriel.demo-session')!).user).toEqual(user);
  });

  it.each(['desconocido@sgabriel.pe', 'almacen@sgabriel.pe'])(
    'rechaza el correo no autorizado %s aunque la contraseña sea correcta',
    async (email) => {
      const auth = TestBed.inject(AuthService);
      await expect(auth.login({ email, password: DEMO_PASSWORD })).rejects.toThrow(
        'no son correctos',
      );
      expect(auth.isAuthenticated()).toBe(false);
      expect(auth.user()).toBeNull();
      expect(sessionStorage.getItem('sgabriel.demo-session')).toBeNull();
    },
  );

  it.each(DEMO_USERS)('restaura la sesión vigente de $name', (user) => {
    sessionStorage.setItem(
      'sgabriel.demo-session',
      JSON.stringify({ accessToken: 'san-gabriel-demo-session', user }),
    );
    const auth = TestBed.inject(AuthService);
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.user()).toEqual(user);
    expect(auth.token()).toBe('san-gabriel-demo-session');
  });

  it('descarta la sesión del usuario de demostración anterior', () => {
    sessionStorage.setItem(
      'sgabriel.demo-session',
      JSON.stringify({
        accessToken: 'san-gabriel-demo-session',
        user: {
          id: 'demo-1',
          name: 'María Torres',
          email: 'almacen@sgabriel.pe',
          role: 'Responsable de almacén',
        },
      }),
    );
    const auth = TestBed.inject(AuthService);
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.user()).toBeNull();
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
