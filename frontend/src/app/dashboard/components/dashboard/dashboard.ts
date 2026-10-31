import { Component, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormField, form, required, validate } from '@angular/forms/signals';
import { DashboardService } from '../../service/dashboard';
import { Icon } from '../../../shared/components/icon/icon';
import { FieldErrors } from '../../../shared/components/field-errors/field-errors';
import { isDate, offsetDate, today } from '../../../core/service/date-utils';
import { AuthService } from '../../../auth/service/auth';

@Component({
  imports: [CurrencyPipe, DatePipe, RouterLink, FormField, Icon, FieldErrors],
  selector: 'app-dashboard',
  styleUrl: './dashboard.scss',
  templateUrl: './dashboard.html',
})
export class Dashboard {
  readonly service = inject(DashboardService);
  readonly inventory = this.service.inventory;
  readonly auth = inject(AuthService);
  readonly isQuery = inject(ActivatedRoute).snapshot.routeConfig?.path === 'consultas';
  readonly now = new Date();
  readonly fromDefault = offsetDate(-29);
  readonly filtersModel = signal({ from: this.fromDefault, to: today() });
  readonly filters = form(this.filtersModel, (path) => {
    required(path.from, { message: 'Selecciona la fecha inicial.' });
    required(path.to, { message: 'Selecciona la fecha final.' });
    validate(path.from, ({ value }) =>
      value() && !isDate(value())
        ? { kind: 'date', message: 'Ingresa una fecha válida.' }
        : undefined,
    );
    validate(path.to, ({ value }) =>
      value() && (!isDate(value()) || value() < this.filtersModel().from)
        ? { kind: 'range', message: 'La fecha final debe ser igual o posterior a la inicial.' }
        : undefined,
    );
  });
  readonly summary = computed(() =>
    this.filters().valid()
      ? this.service.summarize(this.filtersModel().from, this.filtersModel().to)
      : null,
  );
  readonly chartMax = computed(() =>
    Math.max(1, ...(this.summary()?.series.map((s) => Math.max(s.entries, s.exits)) ?? [1])),
  );
  readonly latest = computed(() =>
    this.inventory
      .movements()
      .filter((m) => m.date >= this.filtersModel().from && m.date <= this.filtersModel().to)
      .reverse()
      .sort((a, b) => b.date.localeCompare(a.date))
      .slice(0, 4),
  );
  readonly alertLots = computed(() =>
    this.inventory
      .lots()
      .filter(
        (l) =>
          l.stock > 0 &&
          this.inventory.activeProducts().some((p) => p.id === l.productId) &&
          l.expirationDate &&
          l.expirationDate <= offsetDate(this.inventory.warningDays),
      )
      .sort((a, b) => a.expirationDate!.localeCompare(b.expirationDate!)),
  );
  readonly currentDate = today();
  async refresh() {
    try {
      await this.inventory.refresh();
    } catch {
      /* Shared error banner provides retry. */
    }
  }
}
