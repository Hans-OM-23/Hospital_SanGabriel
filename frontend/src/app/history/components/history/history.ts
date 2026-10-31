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
import { Pagination } from '../../../shared/components/pagination/pagination';
import { PaginationState } from '../../../shared/service/pagination-state';

interface HistoryFilters {
  search: string;
  productId: string;
  type: string;
  areaId: string;
  from: string;
  to: string;
}
const emptyFilters = (): HistoryFilters => ({
  search: '',
  productId: '',
  type: '',
  areaId: '',
  from: '',
  to: '',
});
const normalizeSearch = (value: string) =>
  value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-PE');

@Component({
  imports: [DatePipe, FormField, RouterLink, FieldErrors, Icon, Pagination],
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
    const search = normalizeSearch(filters.search.trim());
    return this.inventory
      .movements()
      .filter(
        (movement) =>
          (!selected || movement.id === selected) &&
          (!search ||
            normalizeSearch(
              [
                this.inventory.productName(movement.productId) ?? '',
                this.inventory.products().find((product) => product.id === movement.productId)
                  ?.code ?? '',
                movement.lotNumber ?? '',
                movement.reason ?? '',
                this.inventory.areaName(movement.areaId) ?? '',
              ].join(' '),
            ).includes(search)) &&
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
  readonly pagination = new PaginationState(this.filtered, () =>
    JSON.stringify({ filters: this.applied(), movement: this.selectedMovementId() }),
  );

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
      search: params.get('busqueda') ?? '',
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
      const filters = { ...this.model(), search: this.model().search.trim() };
      this.applied.set({ ...filters });
      this.refreshed.set(false);
      await this.router.navigate([], {
        relativeTo: this.route,
        queryParamsHandling: 'merge',
        queryParams: {
          busqueda: filters.search || null,
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
        busqueda: null,
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
