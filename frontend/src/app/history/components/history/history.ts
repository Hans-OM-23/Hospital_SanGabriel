import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormField, form, submit, validate } from '@angular/forms/signals';
import { ActivatedRoute, ParamMap, Router, RouterLink } from '@angular/router';
import { explainError } from '../../../core/service/api-error';
import { isDate } from '../../../core/service/date-utils';
import { InventoryService } from '../../../core/service/inventory.service';
import { FieldErrors } from '../../../shared/components/field-errors/field-errors';
import { Icon } from '../../../shared/components/icon/icon';

interface HistoryFilters {
  productId: string;
  type: string;
  areaId: string;
  from: string;
  to: string;
}
const emptyFilters = (): HistoryFilters => ({
  productId: '',
  type: '',
  areaId: '',
  from: '',
  to: '',
});

@Component({
  imports: [DatePipe, FormField, RouterLink, FieldErrors, Icon],
  selector: 'app-history',
  styleUrl: './history.scss',
  templateUrl: './history.html',
})
export class History {
  readonly inventory = inject(InventoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly query = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });
  readonly selectedMovementId = computed(() => this.query().get('movimiento'));
  readonly error = signal('');
  readonly refreshed = signal(false);
  readonly model = signal<HistoryFilters>(emptyFilters());
  readonly applied = signal<HistoryFilters>(emptyFilters());
  readonly filtersForm = form(this.model, (path) => {
    validate(path.from, ({ value }) =>
      value() && !isDate(value())
        ? { kind: 'date', message: 'Ingresa una fecha de inicio válida.' }
        : undefined,
    );
    validate(path.to, ({ value }) =>
      value() && !isDate(value())
        ? { kind: 'date', message: 'Ingresa una fecha final válida.' }
        : value() && this.model().from && value() < this.model().from
          ? { kind: 'range', message: 'La fecha final debe ser igual o posterior a la inicial.' }
          : undefined,
    );
  });
  readonly filtered = computed(() => {
    const filters = this.applied();
    const selected = this.selectedMovementId();
    return this.inventory
      .movements()
      .filter(
        (movement) =>
          (!selected || movement.id === selected) &&
          (!filters.productId || movement.productId === filters.productId) &&
          (!filters.type || movement.type === filters.type) &&
          (!filters.areaId || movement.areaId === filters.areaId) &&
          (!filters.from || movement.date >= filters.from) &&
          (!filters.to || movement.date <= filters.to),
      )
      .reverse()
      .sort((a, b) => b.date.localeCompare(a.date));
  });
  readonly entryCount = computed(() => this.filtered().filter((m) => m.type === 'entry').length);
  readonly exitCount = computed(() => this.filtered().filter((m) => m.type === 'exit').length);
  readonly hasFilters = computed(() => Object.values(this.applied()).some(Boolean));

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const filters = this.filtersFromParams(params);
      this.filtersForm().reset(filters);
      if (this.filtersForm().invalid()) {
        this.filtersForm().markAsTouched();
        this.applied.set(emptyFilters());
      } else {
        this.applied.set(filters);
      }
    });
  }

  private filtersFromParams(params: ParamMap): HistoryFilters {
    const type = params.get('tipo');
    return {
      productId: params.get('producto') ?? '',
      type: type === 'entry' || type === 'exit' ? type : '',
      areaId: params.get('area') ?? '',
      from: params.get('desde') ?? '',
      to: params.get('hasta') ?? '',
    };
  }

  async applyFilters(event: Event) {
    event.preventDefault();
    await submit(this.filtersForm, async () => {
      const filters = this.model();
      this.applied.set({ ...filters });
      this.refreshed.set(false);
      await this.router.navigate([], {
        relativeTo: this.route,
        queryParamsHandling: 'merge',
        queryParams: {
          producto: filters.productId || null,
          tipo: filters.type || null,
          area: filters.areaId || null,
          desde: filters.from || null,
          hasta: filters.to || null,
          movimiento: null,
        },
      });
    });
  }

  async resetFilters() {
    this.filtersForm().reset(emptyFilters());
    this.applied.set(emptyFilters());
    await this.router.navigate([], {
      relativeTo: this.route,
      queryParamsHandling: 'merge',
      queryParams: {
        producto: null,
        tipo: null,
        area: null,
        desde: null,
        hasta: null,
        movimiento: null,
      },
    });
  }

  clearSelection() {
    return this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { movimiento: null },
      queryParamsHandling: 'merge',
    });
  }

  async refresh() {
    this.error.set('');
    this.refreshed.set(false);
    try {
      await this.inventory.refresh();
      this.refreshed.set(true);
    } catch (error) {
      this.error.set(explainError(error).message);
    }
  }
}
