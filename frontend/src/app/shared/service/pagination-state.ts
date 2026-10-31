import { computed, linkedSignal, Signal, signal } from '@angular/core';

export const PAGE_SIZES = [5, 10, 20] as const;

/** A separate instance per list; filtering always happens before pagination. */
export class PaginationState<T> {
  private readonly size = signal<number>(PAGE_SIZES[0]);
  readonly pageSize = this.size.asReadonly();
  readonly totalItems = computed(() => this.source().length);
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.totalItems() / this.pageSize())));
  private readonly selectedPage = linkedSignal({
    source: () => ({ key: this.resetKey(), size: this.pageSize(), pages: this.totalPages() }),
    computation: (current, previous): number => {
      if (
        !previous ||
        previous.source.key !== current.key ||
        previous.source.size !== current.size
      ) {
        return 1;
      }
      return Math.min(previous.value, current.pages);
    },
  });
  readonly page = this.selectedPage.asReadonly();
  readonly start = computed(() =>
    this.totalItems() ? (this.page() - 1) * this.pageSize() + 1 : 0,
  );
  readonly end = computed(() => Math.min(this.page() * this.pageSize(), this.totalItems()));
  readonly items = computed(() => {
    const start = (this.page() - 1) * this.pageSize();
    return this.source().slice(start, start + this.pageSize());
  });

  constructor(
    private readonly source: Signal<readonly T[]>,
    private readonly resetKey: () => unknown,
  ) {}

  setPage(value: number): void {
    if (!Number.isSafeInteger(value)) return;
    this.selectedPage.set(Math.max(1, Math.min(value, this.totalPages())));
  }

  setPageSize(value: number): void {
    if (PAGE_SIZES.some((size) => size === value)) this.size.set(value);
  }
}
