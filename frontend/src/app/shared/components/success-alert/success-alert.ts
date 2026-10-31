import { DOCUMENT } from '@angular/common';
import { A11yModule } from '@angular/cdk/a11y';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  OnDestroy,
  output,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Icon } from '../icon/icon';

@Component({
  imports: [A11yModule, RouterLink, Icon],
  selector: 'app-success-alert',
  styleUrl: './success-alert.scss',
  templateUrl: './success-alert.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '(document:keydown.escape)': 'dismiss($event)' },
})
export class SuccessAlert implements OnDestroy {
  readonly title = input('Producto registrado');
  readonly productName = input.required<string>();
  readonly productCode = input.required<string>();
  readonly message = input('Los datos del producto se guardaron correctamente.');
  readonly continueLabel = input('Seguir registrando');
  readonly closed = output<void>();
  private readonly document = inject(DOCUMENT);
  private readonly previousOverflow = this.document.body.style.overflow;

  constructor() {
    this.document.body.style.overflow = 'hidden';
  }

  dismiss(event?: Event) {
    event?.preventDefault();
    event?.stopPropagation();
    this.closed.emit();
  }

  ngOnDestroy() {
    this.document.body.style.overflow = this.previousOverflow;
  }
}
