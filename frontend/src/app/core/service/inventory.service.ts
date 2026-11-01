import { computed, inject, Injectable, signal } from '@angular/core';
import { InventoryGateway, InventorySnapshot } from '../interface/inventory';
import { ProductInput } from '../../products/interface/product';
import { CategoryInput } from '../../categories/interface/category';
import { MovementInput } from '../../movements/interface/movement';
import { explainError } from './api-error';
import { offsetDate, today } from './date-utils';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class InventoryService {
  private readonly gateway = inject(InventoryGateway);
  private readonly state = signal<InventorySnapshot>({
    products: [],
    categories: [],
    lots: [],
    areas: [],
    movements: [],
  });
  readonly products = computed(() => this.state().products);
  readonly categories = computed(() => this.state().categories);
  readonly lots = computed(() => this.state().lots);
  readonly areas = computed(() => this.state().areas);
  readonly movements = computed(() => this.state().movements);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly lastRefresh = signal<Date | null>(null);
  readonly warningDays = environment.expirationWarningDays;
  readonly activeProducts = computed(() => this.products().filter((p) => p.active));
  readonly lowStock = computed(() =>
    this.activeProducts().filter((p) => this.stock(p.id) <= p.minStock),
  );
  readonly expiring = computed(() =>
    this.activeProducts().filter((p) =>
      this.productLots(p.id).some(
        (l) =>
          l.stock > 0 &&
          l.expirationDate &&
          l.expirationDate >= today() &&
          l.expirationDate <= offsetDate(this.warningDays),
      ),
    ),
  );
  readonly expired = computed(() =>
    this.activeProducts().filter((p) =>
      this.productLots(p.id).some(
        (l) => l.stock > 0 && l.expirationDate && l.expirationDate < today(),
      ),
    ),
  );
  readonly inventoryValue = computed(() =>
    this.activeProducts().reduce((sum, p) => sum + this.stock(p.id) * p.unitPrice, 0),
  );

  async refresh(): Promise<void> {
    this.loading.set(true);
    this.error.set('');
    try {
      this.state.set(await this.gateway.load());
      this.lastRefresh.set(new Date());
    } catch (error) {
      this.error.set(explainError(error).message);
      throw error;
    } finally {
      this.loading.set(false);
    }
  }

  stock(productId: string): number {
    return this.productLots(productId).reduce((sum, lot) => sum + lot.stock, 0);
  }
  productLots(productId: string) {
    return this.lots()
      .filter((l) => l.productId === productId)
      .sort((a, b) => (a.expirationDate ?? '9999').localeCompare(b.expirationDate ?? '9999'));
  }
  productName(id: string) {
    return this.products().find((p) => p.id === id)?.name ?? 'Producto no disponible';
  }
  categoryName(id: string) {
    return this.categories().find((c) => c.id === id)?.name ?? 'Sin categoría';
  }
  areaName(id: string | null) {
    return this.areas().find((a) => a.id === id)?.name ?? 'Almacén central';
  }
  private async refreshAfterMutation(): Promise<void> {
    try {
      await this.refresh();
    } catch {
      this.error.set(
        'La operación se guardó, pero no se pudo actualizar la información. Usa Actualizar para consultar los saldos; no repitas el registro.',
      );
    }
  }
  async saveProduct(input: ProductInput, id?: string) {
    const result = await this.gateway.saveProduct(input, id);
    await this.refreshAfterMutation();
    return result;
  }
  async setProductActive(id: string, active: boolean) {
    await this.gateway.setProductActive(id, active);
    await this.refreshAfterMutation();
  }
  async saveCategory(input: CategoryInput) {
    const result = await this.gateway.saveCategory(input);
    await this.refreshAfterMutation();
    return result;
  }
  async registerMovement(input: MovementInput) {
    const result = await this.gateway.registerMovement(input);
    await this.refreshAfterMutation();
    return result;
  }
}
