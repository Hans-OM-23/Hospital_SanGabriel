import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { email, FormField, form, required, submit, validate } from '@angular/forms/signals';
import { Router } from '@angular/router';
import { environment } from '../../../../environments/environment';
import { FieldErrors } from '../../../shared/components/field-errors/field-errors';
import { Icon } from '../../../shared/components/icon/icon';
import { AuthService } from '../../service/auth';
import { DEMO_PASSWORD, DEMO_USERS } from '../../service/demo-users';

@Component({
  imports: [FormField, FieldErrors, Icon],
  selector: 'app-login',
  styleUrl: './login.scss',
  templateUrl: './login.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly isDemo = environment.useMock;
  readonly demoUsers = DEMO_USERS;
  readonly demoPassword = DEMO_PASSWORD;
  readonly showPassword = signal(false);
  readonly error = signal('');
  readonly credentials = signal({ email: '', password: '' });
  readonly loginForm = form(this.credentials, (path) => {
    required(path.email, { message: 'Escribe tu correo institucional.' });
    email(path.email, { message: 'Ingresa un correo válido, por ejemplo: example@example.pe' });
    required(path.password, { message: 'Escribe tu contraseña.' });
    validate(path.password, ({ value }) =>
      value().length > 0 && value().trim().length === 0
        ? { kind: 'blank', message: 'La contraseña no puede contener solamente espacios.' }
        : undefined,
    );
  });

  fillDemo(email: string): void {
    this.credentials.set({ email, password: DEMO_PASSWORD });
    this.error.set('');
  }

  async signIn(event: Event): Promise<void> {
    event.preventDefault();
    if (this.loginForm().submitting()) return;
    this.loginForm().reset(structuredClone(this.credentials()));
    this.error.set('');
    await submit(this.loginForm, async () => {
      try {
        await this.auth.login(this.credentials());
        await this.router.navigateByUrl('/');
      } catch (error) {
        this.error.set(
          error instanceof Error
            ? error.message
            : 'No pudimos iniciar sesión. Inténtalo nuevamente.',
        );
        return { kind: 'authentication', message: this.error() };
      }
      return undefined;
    });
  }
}
