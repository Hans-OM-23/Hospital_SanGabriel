import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from '../../service/auth';
import { Login } from './login';

describe('Login: validación y recuperación de errores', () => {
  let component: Login;
  const login = vi.fn();
  const navigateByUrl = vi.fn();
  const credentials = { email: 'almacen@sgabriel.pe', password: 'SanGabriel2026!' };

  beforeEach(async () => {
    login.mockReset().mockResolvedValue(undefined);
    navigateByUrl.mockReset().mockResolvedValue(true);
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        { provide: AuthService, useValue: { login } },
        { provide: Router, useValue: { navigateByUrl } },
      ],
    }).compileComponents();
    component = TestBed.createComponent(Login).componentInstance;
  });

  it('impide un envío vacío y muestra validaciones de los campos', async () => {
    await component.signIn(new Event('submit'));
    expect(login).not.toHaveBeenCalled();
    expect(component.loginForm.email().touched()).toBe(true);
    expect(component.loginForm.email().invalid()).toBe(true);
    expect(component.loginForm.password().invalid()).toBe(true);
  });

  it('permite reintentar las mismas credenciales después de un fallo del servicio', async () => {
    component.credentials.set({ ...credentials });
    login.mockRejectedValueOnce(new Error('El servicio no está disponible.'));
    await component.signIn(new Event('submit'));
    expect(component.error()).toBe('El servicio no está disponible.');
    expect(component.loginForm().invalid()).toBe(true);
    expect(component.credentials()).toEqual(credentials);
    await component.signIn(new Event('submit'));
    expect(login).toHaveBeenCalledTimes(2);
    expect(login).toHaveBeenNthCalledWith(2, credentials);
    expect(component.error()).toBe('');
    expect(navigateByUrl).toHaveBeenCalledWith('/');
  });

  it('evita otro envío mientras el acceso anterior sigue pendiente', async () => {
    component.credentials.set({ ...credentials });
    let complete!: () => void;
    login.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        complete = resolve;
      }),
    );
    const first = component.signIn(new Event('submit'));
    await component.signIn(new Event('submit'));
    expect(login).toHaveBeenCalledTimes(1);
    complete();
    await first;
  });
});
