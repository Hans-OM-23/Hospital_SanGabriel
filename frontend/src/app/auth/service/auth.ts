import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthResponse, LoginCredentials, Session } from '../interface/session';
import { DEMO_PASSWORD, DEMO_USERS } from './demo-users';

const DEMO_TOKEN = 'san-gabriel-demo-session';

/** Comprobación local de caducidad para la interfaz. La firma JWT la valida FastAPI. */
function tokenExpired(token: string): boolean {
  try {
    const payload = token.split('.')[1];
    if (!payload) return true;
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as {
      exp?: unknown;
    };
    return (
      typeof decoded.exp !== 'number' ||
      !Number.isFinite(decoded.exp) ||
      decoded.exp * 1000 <= Date.now()
    );
  } catch {
    return true;
  }
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly storageKey = environment.useMock ? 'sgabriel.demo-session' : 'sgabriel.session';
  private readonly accessToken = signal<string | null>(null);
  readonly user = signal<Session | null>(null);
  readonly isAuthenticated = computed(() => this.user() !== null && this.accessToken() !== null);

  constructor() {
    this.restoreSession();
  }

  async login(credentials: LoginCredentials): Promise<void> {
    const email = credentials.email.trim().toLowerCase();
    let response: AuthResponse;
    if (environment.useMock) {
      const user = DEMO_USERS.find((candidate) => candidate.email === email);
      if (!user || credentials.password !== DEMO_PASSWORD) {
        throw new Error(
          'El correo o la contraseña no son correctos. Revisa tus datos e inténtalo otra vez.',
        );
      }
      response = {
        accessToken: DEMO_TOKEN,
        user: { ...user },
      };
    } else {
      try {
        response = await firstValueFrom(
          this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, {
            email,
            password: credentials.password,
          }),
        );
      } catch (error) {
        if (error instanceof HttpErrorResponse && error.status === 401) {
          throw new Error(
            'El correo o la contraseña no son correctos. Revisa tus datos e inténtalo otra vez.',
          );
        }
        throw new Error(
          'No pudimos iniciar sesión. Comprueba la conexión con el servicio e inténtalo nuevamente.',
        );
      }
    }
    if (!this.isValidSession(response) || (!environment.useMock && tokenExpired(response.accessToken))) {
      throw new Error('El servicio devolvió una sesión incompleta. Contacta al administrador.');
    }
    this.accessToken.set(response.accessToken);
    this.user.set(response.user);
    try {
      sessionStorage.setItem(this.storageKey, JSON.stringify(response));
    } catch {
      /* La sesión continúa en memoria si el navegador no permite almacenamiento. */
    }
  }

  /** Descarta tokens vencidos antes de llamar a una ruta protegida. */
  token(): string | null {
    const current = this.accessToken();
    if (current && !environment.useMock && tokenExpired(current)) {
      this.logout();
      return null;
    }
    return current;
  }

  hasValidSession(): boolean {
    return this.token() !== null && this.user() !== null;
  }

  logout(): void {
    this.user.set(null);
    this.accessToken.set(null);
    try {
      sessionStorage.removeItem(this.storageKey);
    } catch {
      /* Almacenamiento no disponible. */
    }
  }

  private restoreSession(): void {
    try {
      const stored = sessionStorage.getItem(this.storageKey);
      if (!stored) return;
      const session: unknown = JSON.parse(stored);
      if (
        this.isValidSession(session) &&
        (environment.useMock ? this.isCurrentDemoSession(session) : !tokenExpired(session.accessToken))
      ) {
        this.user.set(session.user);
        this.accessToken.set(session.accessToken);
      } else {
        sessionStorage.removeItem(this.storageKey);
      }
    } catch {
      this.user.set(null);
      this.accessToken.set(null);
    }
  }

  private isCurrentDemoSession(session: AuthResponse): boolean {
    return (
      session.accessToken === DEMO_TOKEN &&
      DEMO_USERS.some(
        (user) =>
          user.id === session.user.id &&
          user.name === session.user.name &&
          user.email === session.user.email &&
          user.role === session.user.role,
      )
    );
  }

  private isValidSession(value: unknown): value is AuthResponse {
    if (!value || typeof value !== 'object') return false;
    const session = value as Partial<AuthResponse>;
    return (
      typeof session.accessToken === 'string' &&
      session.accessToken.length > 0 &&
      !!session.user &&
      typeof session.user.id === 'string' &&
      typeof session.user.name === 'string' &&
      typeof session.user.email === 'string' &&
      session.user.role === 'Responsable de almacén'
    );
  }
}
