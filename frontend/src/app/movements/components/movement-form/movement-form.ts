import { DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormField, form, required, submit, validate } from '@angular/forms/signals';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { explainError } from '../../../core/service/api-error';
import { isDate, today } from '../../../core/service/date-utils';
import { FieldErrors } from '../../../shared/components/field-errors/field-errors';
import { Icon } from '../../../shared/components/icon/icon';
import { SelectControl } from '../../../shared/components/select-control/select-control';
import { DatePicker } from '../../../shared/components/date-picker/date-picker';
import { SelectOption } from '../../../shared/interface/select-option';
import { Movement, MovementInput, MovementType } from '../../interface/movement';
import { MovementsService } from '../../service/movements';

interface MovementDraft {
  type: MovementType;
  productId: string;
  quantity: string;
  date: string;
  reason: string;
  lotId: string;
  lotNumber: string;
  expirationDate: string;
  areaId: string;
}

@Component({
  imports: [DecimalPipe, FormField, RouterLink, FieldErrors, Icon, SelectControl, DatePicker],
  selector: 'app-movement-form',
  styleUrl: './movement-form.scss',
  templateUrl: './movement-form.html',
})
export class MovementForm {
  readonly service = inject(MovementsService);
  readonly inventory = this.service.inventory;
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly currentDate = today();
  readonly error = signal('');
  readonly success = signal<Movement | null>(null);
  readonly model = signal<MovementDraft>({
    type: 'entry',
    productId: '',
    quantity: '',
    date: today(),
    reason: '',
    lotId: '',
    lotNumber: '',
    expirationDate: '',
    areaId: '',
  });
  readonly isEntry = computed(() => this.model().type === 'entry');
  readonly product = computed(() =>
    this.inventory.activeProducts().find((p) => p.id === this.model().productId),
  );
  readonly lots = computed(() => this.inventory.productLots(this.model().productId));
  readonly selectedLot = computed(() => this.lots().find((l) => l.id === this.model().lotId));
  readonly expiredLot = computed(() => {
    const expiration = this.selectedLot()?.expirationDate;
    return !!expiration && expiration < today();
  });
  readonly productStock = computed(() => this.inventory.stock(this.model().productId));
  readonly productOptions = computed<SelectOption[]>(() =>
    this.inventory.activeProducts().map((product) => ({
      value: product.id,
      label: product.name,
      description: `${product.code} · ${this.inventory.stock(product.id)} ${product.unit.toLowerCase()}(s) disponibles`,
    })),
  );
  readonly reasonOptions: SelectOption[] = this.service.entryReasons.map((reason) => ({
    value: reason,
    label: reason,
  }));
  readonly areaOptions = computed<SelectOption[]>(() =>
    this.inventory.areas().map((area) => ({ value: area.id, label: area.name })),
  );
  readonly lotOptions = computed<SelectOption[]>(() =>
    this.lots().map((lot) => {
      const expired = !!lot.expirationDate && lot.expirationDate < today();
      const expiration = lot.expirationDate
        ? `Vence ${lot.expirationDate.split('-').reverse().join('/')}`
        : 'Sin vencimiento';
      return {
        value: lot.id,
        label: lot.number,
        description: `${lot.stock} disponibles · ${expiration}${expired ? ' · Vencido, salida bloqueada' : ''}`,
        disabled: expired || lot.stock <= 0,
      };
    }),
  );

  readonly movementForm = form(this.model, (path) => {
    required(path.productId, { message: 'Selecciona un producto.' });
    validate(path.productId, ({ value }) =>
      value() && !this.inventory.activeProducts().some((p) => p.id === value())
        ? { kind: 'product', message: 'Selecciona un producto activo de la lista.' }
        : undefined,
    );
    required(path.quantity, { message: 'Ingresa una cantidad.' });
    validate(path.quantity, ({ value }) =>
      value() &&
      (!/^\d+$/.test(value()) || Number(value()) <= 0 || !Number.isSafeInteger(Number(value())))
        ? { kind: 'integer', message: 'La cantidad debe ser un número entero mayor que cero.' }
        : !this.isEntry() && this.selectedLot() && Number(value()) > this.selectedLot()!.stock
          ? {
              kind: 'stock',
              message: `El lote solo tiene ${this.selectedLot()!.stock} unidades disponibles.`,
            }
          : undefined,
    );
    required(path.date, { message: 'Selecciona la fecha del movimiento.' });
    validate(path.date, ({ value }) =>
      value() && (!isDate(value()) || value() > today())
        ? { kind: 'date', message: 'Ingresa una fecha válida que no sea futura.' }
        : undefined,
    );
    required(path.reason, { message: 'Indica el motivo del movimiento.' });
    validate(path.reason, ({ value }) =>
      value() && (this.isEntry() ? !this.service.entryReasons.includes(value()) : !value().trim())
        ? {
            kind: 'reason',
            message: this.isEntry()
              ? 'Selecciona compra, donación o devolución.'
              : 'Escribe el motivo de la salida.',
          }
        : undefined,
    );
    required(path.lotNumber, { when: () => this.isEntry(), message: 'Ingresa el número de lote.' });
    validate(path.lotNumber, ({ value }) =>
      this.isEntry() && value() && !value().trim()
        ? { kind: 'lot', message: 'El número de lote no puede contener solo espacios.' }
        : undefined,
    );
    required(path.expirationDate, {
      when: () => this.isEntry() && !!this.product()?.tracksExpiration,
      message: 'Selecciona el vencimiento de este lote.',
    });
    validate(path.expirationDate, ({ value }) =>
      this.isEntry() && this.product()?.tracksExpiration && value() && !isDate(value())
        ? { kind: 'date', message: 'Ingresa una fecha de vencimiento válida.' }
        : this.isEntry() &&
            this.product()?.tracksExpiration &&
            value() &&
            value() < this.model().date
          ? { kind: 'expired', message: 'El lote no puede estar vencido a la fecha del ingreso.' }
          : undefined,
    );
    required(path.lotId, {
      when: () => !this.isEntry(),
      message: 'Selecciona manualmente el lote que se utilizará.',
    });
    validate(path.lotId, ({ value }) =>
      !this.isEntry() && value() && (!this.selectedLot() || this.selectedLot()!.stock <= 0)
        ? { kind: 'lot', message: 'Selecciona un lote con existencias disponibles.' }
        : !this.isEntry() && this.expiredLot()
          ? {
              kind: 'expired',
              message: 'Este lote está vencido. Su salida para uso hospitalario está bloqueada.',
            }
          : undefined,
    );
    required(path.areaId, {
      when: () => !this.isEntry(),
      message: 'Selecciona el área hospitalaria de destino.',
    });
    validate(path.areaId, ({ value }) =>
      !this.isEntry() && value() && !this.inventory.areas().some((a) => a.id === value())
        ? { kind: 'area', message: 'Selecciona un área hospitalaria válida.' }
        : undefined,
    );
  });

  constructor() {
    let lastSelection = '';
    effect(() => {
      const model = this.model();
      const selection = `${model.type}:${model.productId}`;
      if (lastSelection && selection !== lastSelection) {
        untracked(() => {
          this.model.update((draft) => ({
            ...draft,
            lotId: '',
            lotNumber: '',
            expirationDate: '',
            reason: '',
            areaId: '',
          }));
          this.success.set(null);
          this.error.set('');
        });
      }
      lastSelection = selection;
    });
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const type: MovementType = params.get('tipo') === 'exit' ? 'exit' : 'entry';
      this.model.update((draft) => ({
        ...draft,
        type,
        productId: params.get('producto') ?? draft.productId,
      }));
    });
  }

  changeType(type: MovementType) {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tipo: type },
      queryParamsHandling: 'merge',
    });
  }

  async save(event: Event) {
    event.preventDefault();
    if (this.movementForm().submitting()) return;
    this.movementForm().reset(structuredClone(this.model()));
    this.error.set('');
    this.success.set(null);
    await submit(this.movementForm, async () => {
      const draft = this.model();
      const input: MovementInput = {
        type: draft.type,
        productId: draft.productId,
        quantity: Number(draft.quantity),
        date: draft.date,
        reason: draft.reason.trim(),
        ...(draft.type === 'entry'
          ? {
              lotNumber: draft.lotNumber.trim(),
              expirationDate: this.product()?.tracksExpiration ? draft.expirationDate : null,
            }
          : { lotId: draft.lotId, areaId: draft.areaId }),
      };
      try {
        const movement = await this.service.register(input);
        this.success.set(movement);
        this.movementForm().reset({
          ...draft,
          quantity: '',
          lotId: '',
          lotNumber: '',
          expirationDate: '',
          reason: '',
          areaId: '',
        });
        return undefined;
      } catch (error) {
        const detail = explainError(error);
        this.error.set(detail.message);
        const field =
          detail.field === 'quantity'
            ? this.movementForm.quantity
            : detail.field === 'date'
              ? this.movementForm.date
              : detail.field === 'reason'
                ? this.movementForm.reason
                : detail.field === 'lotId'
                  ? this.movementForm.lotId
                  : detail.field === 'lotNumber'
                    ? this.movementForm.lotNumber
                    : detail.field === 'expirationDate'
                      ? this.movementForm.expirationDate
                      : detail.field === 'areaId'
                        ? this.movementForm.areaId
                        : detail.field === 'productId'
                          ? this.movementForm.productId
                          : this.movementForm;
        return [{ fieldTree: field, kind: 'server', message: detail.message }];
      }
    });
  }
}
