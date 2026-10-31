import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  disabled,
  FormField,
  form,
  maxLength,
  required,
  submit,
  validate,
} from '@angular/forms/signals';
import { ProductsService } from '../../service/products';
import { Product, ProductInput } from '../../interface/product';
import { FieldErrors } from '../../../shared/components/field-errors/field-errors';
import { Icon } from '../../../shared/components/icon/icon';
import { SelectControl } from '../../../shared/components/select-control/select-control';
import { DatePicker } from '../../../shared/components/date-picker/date-picker';
import { SuccessAlert } from '../../../shared/components/success-alert/success-alert';
import { explainError } from '../../../core/service/api-error';
import { isDate } from '../../../core/service/date-utils';

interface ProductModel {
  code: string;
  name: string;
  description: string;
  categoryId: string;
  unit: string;
  unitPrice: number;
  minStock: number;
  tracksExpiration: boolean;
  expirationDate: string;
}

const emptyProduct = (): ProductModel => ({
  code: '',
  name: '',
  description: '',
  categoryId: '',
  unit: '',
  unitPrice: NaN,
  minStock: 0,
  tracksExpiration: false,
  expirationDate: '',
});

@Component({
  selector: 'app-product-form',
  imports: [RouterLink, FormField, FieldErrors, Icon, SelectControl, DatePicker, SuccessAlert],
  templateUrl: './product-form.html',
  styleUrl: './product-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductForm {
  readonly service = inject(ProductsService);
  private readonly params = toSignal(inject(ActivatedRoute).paramMap);
  readonly editId = computed(() => this.params()?.get('id') ?? undefined);
  readonly isEdit = computed(() => !!this.editId());
  private initializedId: string | undefined;
  readonly model = signal<ProductModel>(emptyProduct());
  readonly error = signal('');
  readonly saved = signal(false);
  readonly successOpen = signal(false);
  readonly savedProduct = signal<Product | null>(null);
  readonly savedWasEdit = signal(false);
  readonly units = [
    'Unidad',
    'Tableta',
    'Cápsula',
    'Ampolla',
    'Frasco',
    'Caja',
    'Par',
    'Paquete',
    'Litro',
    'Kilogramo',
  ];
  readonly categories = computed(() =>
    this.service.categories().filter((category) => category.active),
  );
  readonly categoryOptions = computed(() =>
    this.categories().map((category) => ({ value: category.id, label: category.name })),
  );
  readonly unitOptions = this.units.map((unit) => ({ value: unit, label: unit }));
  readonly hasMovements = computed(
    () =>
      !!this.editId() &&
      this.service.inventory.movements().some((movement) => movement.productId === this.editId()),
  );
  readonly notFound = computed(
    () =>
      !!this.editId() &&
      !!this.service.inventory.lastRefresh() &&
      !this.service.products().some((p) => p.id === this.editId()),
  );
  readonly productForm = form(this.model, (path) => {
    disabled(path.unit, { when: () => this.hasMovements() });
    disabled(path.tracksExpiration, { when: () => this.hasMovements() });
    maxLength(path.code, 40, { message: 'El código admite hasta 40 caracteres.' });
    maxLength(path.name, 160, { message: 'El nombre admite hasta 160 caracteres.' });
    maxLength(path.description, 1000, { message: 'La descripción admite hasta 1000 caracteres.' });
    required(path.code, { message: 'Ingresa el código del producto.' });
    validate(path.code, ({ value }) => {
      if (!value()) return undefined;
      const code = value().trim().toUpperCase();
      if (!code) return { kind: 'required', message: 'Ingresa un código válido.' };
      if (
        this.service
          .products()
          .some((p) => p.id !== this.editId() && p.code.trim().toUpperCase() === code)
      )
        return {
          kind: 'duplicate',
          message: 'Este código ya está registrado. Utiliza uno diferente.',
        };
      return undefined;
    });
    required(path.name, { message: 'Ingresa el nombre del producto.' });
    validate(path.name, ({ value }) =>
      !value() || value().trim()
        ? undefined
        : { kind: 'required', message: 'El nombre no puede contener solo espacios.' },
    );
    required(path.description, { message: 'Describe el producto y su uso.' });
    validate(path.description, ({ value }) =>
      !value() || value().trim()
        ? undefined
        : { kind: 'required', message: 'Ingresa una descripción válida.' },
    );
    required(path.categoryId, { message: 'Selecciona una categoría.' });
    validate(path.categoryId, ({ value }) =>
      !value() || this.categories().some((c) => c.id === value())
        ? undefined
        : { kind: 'category', message: 'Selecciona una categoría disponible.' },
    );
    required(path.unit, { message: 'Selecciona la unidad de medida.' });
    validate(path.unit, ({ value }) =>
      !value() || this.units.includes(value())
        ? undefined
        : { kind: 'unit', message: 'Selecciona una unidad de medida válida.' },
    );
    required(path.unitPrice, { message: 'Ingresa el precio unitario.' });
    validate(path.unitPrice, ({ value }) =>
      Number.isNaN(value()) || (Number.isFinite(value()) && value() > 0)
        ? undefined
        : { kind: 'price', message: 'El precio debe ser un número mayor que cero.' },
    );
    required(path.minStock, { message: 'Ingresa el stock mínimo.' });
    validate(path.minStock, ({ value }) =>
      Number.isNaN(value()) || (Number.isSafeInteger(value()) && value() >= 0)
        ? undefined
        : {
            kind: 'integer',
            message: 'El stock mínimo debe ser un número entero igual o mayor que cero.',
          },
    );
    required(path.expirationDate, {
      when: ({ valueOf }) => valueOf(path.tracksExpiration),
      message: 'Selecciona la fecha de vencimiento.',
    });
    validate(path.expirationDate, ({ value, valueOf }) =>
      !valueOf(path.tracksExpiration) || !value() || isDate(value())
        ? undefined
        : { kind: 'date', message: 'Ingresa una fecha de vencimiento válida.' },
    );
  });

  constructor() {
    effect(() => {
      const id = this.editId();
      if (!id) {
        if (this.initializedId) {
          this.model.set(emptyProduct());
          this.saved.set(false);
          this.successOpen.set(false);
          this.initializedId = undefined;
        }
        return;
      }
      const product = this.service.products().find((p) => p.id === id);
      if (product && this.initializedId !== id) {
        this.model.set({ ...product, expirationDate: product.expirationDate ?? '' });
        this.initializedId = id;
        this.saved.set(false);
        this.successOpen.set(false);
      }
    });
  }

  async save(event: Event) {
    event.preventDefault();
    if (this.productForm().submitting()) return;
    this.productForm().reset(structuredClone(this.model()));
    this.error.set('');
    this.saved.set(false);
    this.successOpen.set(false);
    await submit(this.productForm, async () => {
      const model = this.model();
      const input: ProductInput = {
        ...model,
        code: model.code.trim().toUpperCase(),
        name: model.name.trim(),
        description: model.description.trim(),
        expirationDate: model.tracksExpiration ? model.expirationDate : null,
      };
      try {
        const product = await this.service.save(input, this.editId());
        this.savedProduct.set(product);
        this.savedWasEdit.set(this.isEdit());
        this.saved.set(true);
        this.successOpen.set(true);
        if (!this.editId()) {
          this.model.set(emptyProduct());
          this.productForm().reset();
        }
        return undefined;
      } catch (error) {
        const apiError = explainError(error);
        if (apiError.field === 'code')
          return [{ fieldTree: this.productForm.code, kind: 'server', message: apiError.message }];
        this.error.set(apiError.message);
        return [{ fieldTree: this.productForm, kind: 'server', message: apiError.message }];
      }
    });
  }

  closeSuccess() {
    this.successOpen.set(false);
  }
}
