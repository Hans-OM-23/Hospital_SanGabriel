import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { form, FormField } from '@angular/forms/signals';
import { ProductsService } from '../../service/products';
import { Product } from '../../interface/product';
import { Icon } from '../../../shared/components/icon/icon';
import { explainError } from '../../../core/service/api-error';
import { offsetDate, today } from '../../../core/service/date-utils';
import { PaginationState } from '../../../shared/service/pagination-state';
import { Pagination } from '../../../shared/components/pagination/pagination';

@Component({
  selector: 'app-product-list',
  imports: [CurrencyPipe, DatePipe, RouterLink, FormField, Icon, Pagination],
  templateUrl: './product-list.html',
  styleUrl: './product-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductList {
  readonly service = inject(ProductsService);
  readonly today = today();
  readonly filtersModel = signal({ search: '', category: '', status: 'active' });
  readonly filters = form(this.filtersModel);
  readonly selectedId = signal<string | null>(null);
  readonly confirmId = signal<string | null>(null);
  readonly busy = signal(false);
  readonly message = signal('');
  readonly error = signal('');
  readonly products = computed(() => {
    const { search, category, status } = this.filtersModel();
    const query = search.trim().toLocaleLowerCase('es');
    return this.service
      .products()
      .filter(
        (p) =>
          (!query || `${p.code} ${p.name}`.toLocaleLowerCase('es').includes(query)) &&
          (!category || p.categoryId === category) &&
          (!status || (status === 'active' ? p.active : !p.active)),
      );
  });
  readonly activeCount = computed(() => this.service.products().filter((p) => p.active).length);
  readonly pagination = new PaginationState(this.products, this.filtersModel);
  readonly lowCount = computed(() => this.service.inventory.lowStock().length);
  readonly expiringCount = computed(() => this.service.inventory.expiring().length);

  toggleDetails(id: string) {
    this.selectedId.update((value) => (value === id ? null : id));
  }
  changePage(page: number) {
    if (page === this.pagination.page()) return;
    this.selectedId.set(null);
    this.confirmId.set(null);
    this.pagination.setPage(page);
  }
  changePageSize(size: number) {
    if (size === this.pagination.pageSize()) return;
    this.selectedId.set(null);
    this.confirmId.set(null);
    this.pagination.setPageSize(size);
  }
  productHistory(id: string) {
    return this.service.inventory
      .movements()
      .filter((m) => m.productId === id)
      .reverse()
      .sort((a, b) => b.date.localeCompare(a.date));
  }
  expirationStatus(id: string): 'expired' | 'soon' | 'ok' {
    const lots = this.service.lots(id).filter((lot) => lot.stock > 0 && lot.expirationDate);
    if (lots.some((lot) => lot.expirationDate! < today())) return 'expired';
    return lots.some((lot) => lot.expirationDate! <= offsetDate(this.service.inventory.warningDays))
      ? 'soon'
      : 'ok';
  }
  async toggleActive(product: Product) {
    this.busy.set(true);
    this.message.set('');
    this.error.set('');
    try {
      await this.service.setActive(product.id, !product.active);
      this.message.set(
        `${product.name}: ${product.active ? 'producto desactivado. Su historial se conserva.' : 'producto reactivado.'}`,
      );
      this.confirmId.set(null);
    } catch (error) {
      this.error.set(explainError(error).message);
    } finally {
      this.busy.set(false);
    }
  }
}
