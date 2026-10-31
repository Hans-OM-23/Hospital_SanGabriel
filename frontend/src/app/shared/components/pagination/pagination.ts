import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { FormField, form } from '@angular/forms/signals';
import { Icon } from '../icon/icon';
import { PAGE_SIZES } from '../../service/pagination-state';

@Component({
  selector: 'app-pagination',
  imports: [FormField, Icon],
  templateUrl: './pagination.html',
  styleUrl: './pagination.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Pagination {
  readonly totalItems = input(0);
  readonly page = input(1);
  readonly pageSize = input(5);
  readonly label = input('registros');
  readonly singularLabel = input('registro');
  readonly pageChange = output<number>();
  readonly pageSizeChange = output<number>();
  readonly pageSizes = PAGE_SIZES;
  readonly sizeModel = signal({ pageSize: '5' });
  readonly sizeForm = form(this.sizeModel);
  readonly total = computed(() => Math.max(0, Math.trunc(this.totalItems()) || 0));
  readonly size = computed(() => Math.max(1, Math.trunc(this.pageSize()) || 5));
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.size())));
  readonly currentPage = computed(() =>
    Math.min(this.totalPages(), Math.max(1, Math.trunc(this.page()) || 1)),
  );
  readonly firstItem = computed(() =>
    this.total() === 0 ? 0 : (this.currentPage() - 1) * this.size() + 1,
  );
  readonly lastItem = computed(() => Math.min(this.currentPage() * this.size(), this.total()));
  readonly range = computed(() => {
    const visible = this.total() ? `${this.firstItem()}–${this.lastItem()}` : '0';
    const label = this.total() === 1 ? this.singularLabel() : this.label();
    return `Mostrando ${visible} de ${this.total()} ${label}`;
  });
  readonly pages = computed<(number | 'start-gap' | 'end-gap')[]>(() => {
    const last = this.totalPages();
    if (last <= 7) return Array.from({ length: last }, (_, index) => index + 1);

    const current = this.currentPage();
    let firstVisible = Math.max(2, current - 1);
    let lastVisible = Math.min(last - 1, current + 1);
    if (current <= 3) lastVisible = 4;
    if (current >= last - 2) firstVisible = last - 3;

    const pages: (number | 'start-gap' | 'end-gap')[] = [1];
    if (firstVisible > 2) pages.push('start-gap');
    for (let page = firstVisible; page <= lastVisible; page++) pages.push(page);
    if (lastVisible < last - 1) pages.push('end-gap');
    pages.push(last);
    return pages;
  });

  constructor() {
    effect(() => {
      const pageSize = String(this.pageSize());
      untracked(() => this.sizeModel.set({ pageSize }));
    });
  }

  goToPage(page: number) {
    if (page < 1 || page > this.totalPages() || page === this.currentPage() || !this.total())
      return;
    this.pageChange.emit(page);
  }

  changePageSize(event: Event) {
    const pageSize = Number((event.target as HTMLSelectElement).value);
    if (this.pageSizes.some((size) => size === pageSize) && pageSize !== this.pageSize())
      this.pageSizeChange.emit(pageSize);
  }
}
