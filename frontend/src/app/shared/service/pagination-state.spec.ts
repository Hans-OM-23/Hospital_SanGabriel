import { signal } from '@angular/core';
import { PaginationState } from './pagination-state';

describe('PaginationState: páginas sobre resultados filtrados', () => {
  const makeItems = (count: number) => Array.from({ length: count }, (_, index) => index + 1);

  it('permite recorrer todos los registros sin omitir ni repetir elementos', () => {
    const source = signal(makeItems(12));
    const filter = signal('');
    const pagination = new PaginationState(source, filter);
    expect(pagination.items()).toEqual([1, 2, 3, 4, 5]);
    expect(pagination.totalItems()).toBe(12);
    expect(pagination.totalPages()).toBe(3);
    pagination.setPage(2);
    expect(pagination.items()).toEqual([6, 7, 8, 9, 10]);
    pagination.setPage(3);
    expect(pagination.items()).toEqual([11, 12]);
    expect([pagination.start(), pagination.end()]).toEqual([11, 12]);
    pagination.setPage(1);
    expect(pagination.items()).toEqual([1, 2, 3, 4, 5]);
    expect(source()).toEqual(makeItems(12));
  });

  it('regresa a la primera página al cambiar filtros o tamaño y conserva el tamaño elegido', () => {
    const source = signal(makeItems(26));
    const filter = signal('');
    const pagination = new PaginationState(source, filter);
    pagination.setPage(4);
    filter.set('nuevo filtro');
    expect(pagination.page()).toBe(1);
    pagination.setPage(3);
    pagination.setPageSize(10);
    expect(pagination.page()).toBe(1);
    expect(pagination.items()).toHaveLength(10);
    pagination.setPage(3);
    filter.set('otro filtro');
    expect(pagination.page()).toBe(1);
    expect(pagination.pageSize()).toBe(10);
    pagination.setPageSize(20);
    expect(pagination.items()).toHaveLength(20);
  });

  it('conserva la página al refrescar y la ajusta si desaparece la última página', () => {
    const source = signal(makeItems(12));
    const pagination = new PaginationState(source, () => 'mismo filtro');
    pagination.setPage(3);
    source.set(makeItems(13));
    expect(pagination.page()).toBe(3);
    expect(pagination.items()).toEqual([11, 12, 13]);
    source.set(makeItems(6));
    expect(pagination.page()).toBe(2);
    expect(pagination.items()).toEqual([6]);
    source.set([]);
    expect(pagination.page()).toBe(1);
    expect(pagination.totalPages()).toBe(1);
    expect(pagination.items()).toEqual([]);
    expect([pagination.start(), pagination.end()]).toEqual([0, 0]);
  });

  it('limita las páginas y rechaza tamaños y números inválidos', () => {
    const pagination = new PaginationState(signal(makeItems(12)), () => '');
    pagination.setPage(999);
    expect(pagination.page()).toBe(3);
    for (const page of [NaN, 1.5, Infinity]) pagination.setPage(page);
    expect(pagination.page()).toBe(3);
    pagination.setPage(-1);
    expect(pagination.page()).toBe(1);
    for (const size of [0, -5, 7, NaN, Infinity]) pagination.setPageSize(size);
    expect(pagination.pageSize()).toBe(5);
  });
});
