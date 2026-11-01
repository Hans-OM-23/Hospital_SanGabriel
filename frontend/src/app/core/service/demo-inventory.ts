import { Injectable } from '@angular/core';
import { InventoryGateway, InventorySnapshot } from '../interface/inventory';
import { Product, ProductInput } from '../../products/interface/product';
import { Category, CategoryInput } from '../../categories/interface/category';
import { Movement, MovementInput } from '../../movements/interface/movement';
import { ApiError } from './api-error';
import { createDemoSeed } from './demo-seed';
import { isDate, today } from './date-utils';

const STORAGE_KEY = 'san-gabriel.inventory.v1';

@Injectable({ providedIn: 'root' })
export class DemoInventory extends InventoryGateway {
  private memory = createDemoSeed();

  override async load(): Promise<InventorySnapshot> {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as InventorySnapshot;
        if (
          !Array.isArray(parsed.products) ||
          !Array.isArray(parsed.lots) ||
          !Array.isArray(parsed.movements) ||
          !Array.isArray(parsed.categories) ||
          !Array.isArray(parsed.areas)
        )
          throw new Error('Formato incorrecto');
        return structuredClone(parsed);
      } catch {
        throw new ApiError(
          'Los datos locales no se pueden leer. Puedes restablecer el ejemplo desde el menú de ayuda.',
        );
      }
    }
    return structuredClone(this.memory);
  }

  /** Persist the whole snapshot once: a failed write never mutates the current state. */
  private persist(state: InventorySnapshot): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      throw new ApiError(
        'No se pudieron guardar los datos locales. Comprueba el espacio disponible del navegador.',
      );
    }
    this.memory = structuredClone(state);
  }

  async reset(): Promise<void> {
    this.persist(createDemoSeed());
  }

  override async saveProduct(input: ProductInput, id?: string): Promise<Product> {
    const state = await this.load();
    const code = input.code.trim().toUpperCase();
    if (!code) throw new ApiError('Escribe el código del producto.', 'code');
    if (state.products.some((p) => p.code.toUpperCase() === code && p.id !== id))
      throw new ApiError('Este código ya está registrado. Usa un código único.', 'code');
    if (!input.name.trim()) throw new ApiError('Escribe el nombre del producto.', 'name');
    if (!input.description.trim()) throw new ApiError('Agrega una descripción.', 'description');
    if (!input.unit.trim()) throw new ApiError('Selecciona una unidad de medida.', 'unit');
    if (!Number.isFinite(input.unitPrice) || input.unitPrice <= 0)
      throw new ApiError('El precio debe ser mayor que cero.', 'unitPrice');
    if (!Number.isSafeInteger(input.minStock) || input.minStock < 0)
      throw new ApiError('El stock mínimo debe ser un entero igual o mayor que cero.', 'minStock');
    if (!state.categories.some((c) => c.id === input.categoryId && c.active))
      throw new ApiError('Selecciona una categoría disponible.', 'categoryId');
    if (input.tracksExpiration && (!input.expirationDate || !isDate(input.expirationDate)))
      throw new ApiError('Indica una fecha de vencimiento válida.', 'expirationDate');
    const existing = id ? state.products.find((p) => p.id === id) : undefined;
    if (id && !existing) throw new ApiError('El producto ya no está disponible.');
    if (existing && existing.unit !== input.unit && state.movements.some((m) => m.productId === id))
      throw new ApiError(
        'La unidad de medida no puede cambiar cuando existen movimientos.',
        'unit',
      );
    if (
      existing &&
      existing.tracksExpiration !== input.tracksExpiration &&
      state.movements.some((m) => m.productId === id)
    )
      throw new ApiError(
        'El control de vencimiento no puede cambiar cuando existen movimientos.',
        'tracksExpiration',
      );
    const product: Product = {
      ...input,
      code,
      name: input.name.trim(),
      description: input.description.trim(),
      expirationDate: input.tracksExpiration ? input.expirationDate : null,
      id: existing?.id ?? crypto.randomUUID(),
      active: existing?.active ?? true,
    };
    state.products = existing
      ? state.products.map((p) => (p.id === id ? product : p))
      : [...state.products, product];
    this.persist(state);
    return structuredClone(product);
  }

  override async setProductActive(id: string, active: boolean): Promise<void> {
    const state = await this.load();
    const product = state.products.find((p) => p.id === id);
    if (!product) throw new ApiError('No se encontró el producto.');
    product.active = active;
    this.persist(state);
  }

  override async saveCategory(input: CategoryInput): Promise<Category> {
    const state = await this.load();
    const name = input.name.trim();
    if (!name) throw new ApiError('Escribe el nombre de la categoría.', 'name');
    if (
      state.categories.some((c) => c.name.toLocaleLowerCase('es') === name.toLocaleLowerCase('es'))
    )
      throw new ApiError('Esta categoría ya existe.', 'name');
    const category: Category = {
      id: crypto.randomUUID(),
      name,
      description: input.description.trim(),
      active: true,
    };
    state.categories.push(category);
    this.persist(state);
    return structuredClone(category);
  }

  override async registerMovement(input: MovementInput): Promise<Movement> {
    const state = await this.load();
    const product = state.products.find((p) => p.id === input.productId && p.active);
    if (!product) throw new ApiError('Selecciona un producto activo.', 'productId');
    if (!Number.isSafeInteger(input.quantity) || input.quantity <= 0)
      throw new ApiError('La cantidad debe ser un número entero mayor que cero.', 'quantity');
    if (!isDate(input.date) || input.date > today())
      throw new ApiError('Selecciona una fecha válida que no sea futura.', 'date');
    if (!input.reason.trim()) throw new ApiError('Indica el motivo del movimiento.', 'reason');
    if (input.type !== 'entry' && input.type !== 'exit')
      throw new ApiError('Selecciona un tipo de movimiento válido.');
    const stockBefore = state.lots
      .filter((l) => l.productId === product.id)
      .reduce((sum, l) => sum + l.stock, 0);
    let lot = state.lots.find((l) => l.id === input.lotId && l.productId === product.id);
    if (input.type === 'entry') {
      if (!['Compra', 'Donación', 'Devolución'].includes(input.reason))
        throw new ApiError('Selecciona compra, donación o devolución.', 'reason');
      const number = input.lotNumber?.trim().toUpperCase();
      if (!number)
        throw new ApiError('Indica el número de lote para conservar la trazabilidad.', 'lotNumber');
      const expirationDate = product.tracksExpiration ? (input.expirationDate ?? null) : null;
      if (product.tracksExpiration && (!expirationDate || !isDate(expirationDate)))
        throw new ApiError('Selecciona un vencimiento válido para el lote.', 'expirationDate');
      if (expirationDate && expirationDate < input.date)
        throw new ApiError(
          'El lote no puede estar vencido a la fecha de ingreso.',
          'expirationDate',
        );
      lot = state.lots.find((l) => l.productId === product.id && l.number.toUpperCase() === number);
      if (lot && lot.expirationDate !== expirationDate)
        throw new ApiError(
          'Este lote ya tiene otro vencimiento registrado. Verifica sus datos.',
          'expirationDate',
        );
      if (!lot) {
        lot = { id: crypto.randomUUID(), productId: product.id, number, expirationDate, stock: 0 };
        state.lots.push(lot);
      }
      lot.stock += input.quantity;
    } else {
      if (!lot) throw new ApiError('Selecciona manualmente un lote del producto.', 'lotId');
      if (lot.expirationDate && (lot.expirationDate < today() || lot.expirationDate < input.date))
        throw new ApiError('El lote está vencido y no puede salir para uso hospitalario.', 'lotId');
      if (!state.areas.some((a) => a.id === input.areaId))
        throw new ApiError('Selecciona un área hospitalaria válida.', 'areaId');
      if (input.quantity > lot.stock)
        throw new ApiError(
          `El lote solo dispone de ${lot.stock} ${product.unit.toLowerCase()}(s). Reduce la cantidad.`,
          'quantity',
        );
      lot.stock -= input.quantity;
    }
    const movement: Movement = {
      id: crypto.randomUUID(),
      type: input.type,
      productId: product.id,
      quantity: input.quantity,
      date: input.date,
      reason: input.reason.trim(),
      stockBefore,
      stockAfter: stockBefore + (input.type === 'entry' ? input.quantity : -input.quantity),
      lotId: lot.id,
      lotNumber: lot.number,
      expirationDate: lot.expirationDate,
      areaId: input.type === 'exit' ? input.areaId! : null,
    };
    state.movements.push(movement);
    this.persist(state);
    return structuredClone(movement);
  }
}
