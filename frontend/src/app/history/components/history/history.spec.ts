import { signal, WritableSignal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InventoryService } from '../../../core/service/inventory.service';
import { Movement } from '../../../movements/interface/movement';
import { History } from './history';

describe('History: consulta combinada y validación de fechas', () => {
  let movements: WritableSignal<Movement[]>;
  const paginatedMovements = (): Movement[] =>
    Array.from({ length: 12 }, (_, index) => ({
      id: `movement-${index + 1}`,
      productId: index < 6 ? 'p1' : 'p2',
      type: index % 2 ? 'entry' : 'exit',
      areaId: index % 2 ? null : 'a1',
      date: '2026-10-02',
      quantity: 1,
      reason: 'Movimiento de prueba',
      stockBefore: 2,
      stockAfter: index % 2 ? 3 : 1,
      lotId: 'lot-1',
      lotNumber: 'LOTE-1',
      expirationDate: null,
    }));

  beforeEach(() => {
    movements = signal<Movement[]>(
      [
        { id: 'one', productId: 'p1', type: 'exit', areaId: 'a1', date: '2026-10-02' },
        { id: 'two', productId: 'p1', type: 'exit', areaId: 'a2', date: '2026-10-02' },
        { id: 'three', productId: 'p1', type: 'entry', areaId: null, date: '2026-10-01' },
        { id: 'four', productId: 'p2', type: 'exit', areaId: 'a1', date: '2026-10-02' },
        { id: 'five', productId: 'p1', type: 'exit', areaId: 'a1', date: '2026-09-01' },
      ].map((movement) => ({
        ...movement,
        type: movement.type as Movement['type'],
        quantity: 1,
        reason: 'Movimiento de prueba',
        stockBefore: 2,
        stockAfter: movement.type === 'entry' ? 3 : 1,
        lotId: 'lot-1',
        lotNumber: 'LOTE-1',
        expirationDate: null,
      })),
    );
    TestBed.configureTestingModule({
      imports: [History],
      providers: [
        provideRouter([{ path: 'historial', component: History }]),
        {
          provide: InventoryService,
          useValue: {
            products: signal([
              { id: 'p1', code: 'MED-001', name: 'Paracetamol', active: true },
              { id: 'p2', code: 'MAT-002', name: 'Guantes', active: true },
            ]),
            areas: signal([]),
            loading: signal(false),
            movements,
            productName: (id: string) => (id === 'p1' ? 'Paracetamol' : 'Guantes'),
            areaName: (id: string | null) =>
              id === 'a1' ? 'Emergencia' : (id ?? 'Almacén central'),
            refresh: vi.fn().mockResolvedValue(undefined),
          },
        },
      ],
    });
  });

  it('combina producto, tipo, área y rango de fechas en la misma consulta', async () => {
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const component = TestBed.createComponent(History).componentInstance;
    component.model.set({
      search: '',
      productId: 'p1',
      type: 'exit',
      areaId: 'a1',
      from: '2026-10-01',
      to: '2026-10-31',
    });
    await component.applyFilters(new Event('submit'));
    expect(component.filtered().map((movement) => movement.id)).toEqual(['one']);
  });

  it('impide aplicar un rango de fechas invertido', async () => {
    const component = TestBed.createComponent(History).componentInstance;
    component.model.update((filters) => ({ ...filters, from: '2026-10-31', to: '2026-10-01' }));
    expect(component.filtersForm.to().invalid()).toBe(true);
    await component.applyFilters(new Event('submit'));
    expect(component.applied().from).toBe('');
    expect(component.filtered()).toHaveLength(5);
  });

  it('abre desde un producto y un periodo, combina sus filtros y los limpia de la URL', async () => {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(
      '/historial?producto=p1&desde=2026-10-01&hasta=2026-10-31',
      History,
    );
    expect(component.model()).toMatchObject({
      productId: 'p1',
      from: '2026-10-01',
      to: '2026-10-31',
    });
    expect(component.filtered().map((movement) => movement.id)).toEqual(['two', 'one', 'three']);
    component.model.update((filters) => ({ ...filters, areaId: 'a1', type: 'exit' }));
    await component.applyFilters(new Event('submit'));
    expect(component.filtered().map((movement) => movement.id)).toEqual(['one']);
    expect(TestBed.inject(Router).url).toContain('producto=p1');
    expect(TestBed.inject(Router).url).toContain('desde=2026-10-01');
    expect(TestBed.inject(Router).url).toContain('area=a1');
    await component.resetFilters();
    expect(TestBed.inject(Router).url).toBe('/historial');
    expect(component.filtered()).toHaveLength(5);
  });
  it('muestra primero el último registro cuando hay varios movimientos del mismo día', () => {
    const component = TestBed.createComponent(History).componentInstance;
    expect(
      component
        .filtered()
        .slice(0, 3)
        .map((movement) => movement.id),
    ).toEqual(['four', 'two', 'one']);
  });

  it('pagina las filas y conserva los conteos de todos los resultados', () => {
    movements.set(paginatedMovements());
    const fixture = TestBed.createComponent(History);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('tbody tr')).toHaveLength(5);
    expect(component.pagination.items().map((movement) => movement.id)).toEqual([
      'movement-12',
      'movement-11',
      'movement-10',
      'movement-9',
      'movement-8',
    ]);
    component.pagination.setPage(2);
    fixture.detectChanges();
    expect(component.pagination.items()[0].id).toBe('movement-7');
    expect(component.pagination.items()).toHaveLength(5);
    expect(component.filtered()).toHaveLength(12);
    expect(component.entryCount()).toBe(6);
    expect(component.exitCount()).toBe(6);
    expect(fixture.nativeElement.querySelector('.history-summary').textContent).toContain(
      '12 movimientos encontrados',
    );
  });

  it('vuelve a la primera página al combinar filtros desde otra página', async () => {
    movements.set(paginatedMovements());
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const component = TestBed.createComponent(History).componentInstance;
    component.pagination.setPage(3);
    expect(component.pagination.page()).toBe(3);
    component.model.set({
      search: '',
      productId: 'p1',
      type: 'exit',
      areaId: 'a1',
      from: '2026-10-01',
      to: '2026-10-31',
    });
    await component.applyFilters(new Event('submit'));
    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.items().map((movement) => movement.id)).toEqual([
      'movement-5',
      'movement-3',
      'movement-1',
    ]);
    expect(component.pagination.totalItems()).toBe(3);
    expect(component.entryCount()).toBe(0);
    expect(component.exitCount()).toBe(3);
  });

  it('ajusta la página al actualizar si los registros ya no alcanzan para esa página', async () => {
    movements.set(paginatedMovements());
    const component = TestBed.createComponent(History).componentInstance;
    component.pagination.setPage(3);
    expect(component.pagination.page()).toBe(3);
    vi.mocked(TestBed.inject(InventoryService).refresh).mockImplementation(async () => {
      movements.update((items) => items.slice(0, 6));
    });
    await component.refresh();
    expect(component.pagination.page()).toBe(2);
    expect(component.pagination.items().map((movement) => movement.id)).toEqual(['movement-1']);
    expect(component.pagination.totalItems()).toBe(6);
    expect(component.refreshed()).toBe(true);
  });

  it('muestra el movimiento enlazado aunque estuviera fuera de la primera página', async () => {
    movements.set(paginatedMovements());
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl('/historial', History);
    component.pagination.setPage(3);
    expect(component.pagination.page()).toBe(3);
    const selected = await harness.navigateByUrl(
      '/historial?movimiento=movement-1&producto=p1&desde=2026-10-01&hasta=2026-10-31',
      History,
    );
    expect(selected.pagination.page()).toBe(1);
    expect(selected.pagination.totalItems()).toBe(1);
    expect(selected.pagination.items()[0].id).toBe('movement-1');
    expect(selected.applied()).toMatchObject({
      productId: 'p1',
      from: '2026-10-01',
      to: '2026-10-31',
    });
    harness.detectChanges();
    expect(harness.routeNativeElement?.querySelectorAll('tbody tr')).toHaveLength(1);
    expect(harness.routeNativeElement?.querySelector('tr.selected-row')).not.toBeNull();
    await selected.clearSelection();
    expect(TestBed.inject(Router).url).toContain('producto=p1');
    expect(TestBed.inject(Router).url).toContain('desde=2026-10-01');
    expect(TestBed.inject(Router).url).not.toContain('movimiento=');
    expect(selected.filtered()).toHaveLength(6);
    expect(selected.pagination.page()).toBe(1);
  });

  it('conserva los controles de paginación cuando no hay resultados', () => {
    movements.set([]);
    const fixture = TestBed.createComponent(History);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-pagination')).not.toBeNull();
    expect(fixture.componentInstance.pagination.totalItems()).toBe(0);
    expect(fixture.componentInstance.pagination.items()).toHaveLength(0);
  });

  it('busca en todos los registros y encuentra una coincidencia que estaba en la tercera página', async () => {
    movements.set(
      paginatedMovements().map((movement, index) => ({
        ...movement,
        reason: index === 0 ? 'Reposición prioritaria' : movement.reason,
      })),
    );
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const component = TestBed.createComponent(History).componentInstance;
    expect(component.pagination.items().some((movement) => movement.id === 'movement-1')).toBe(
      false,
    );
    component.pagination.setPage(3);
    expect(component.pagination.page()).toBe(3);
    component.model.update((filters) => ({ ...filters, search: '  REPOSICION PRIORITARIA  ' }));
    await component.applyFilters(new Event('submit'));
    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.items().map((movement) => movement.id)).toEqual(['movement-1']);
    expect(component.pagination.totalItems()).toBe(1);
  });

  it.each<[string, string[]]>([
    ['paracetamol', ['two', 'one', 'three', 'five']],
    ['med-001', ['two', 'one', 'three', 'five']],
    ['lote-1', ['four', 'two', 'one', 'three', 'five']],
    ['movimiento de prueba', ['four', 'two', 'one', 'three', 'five']],
    ['emergencia', ['four', 'one', 'five']],
  ])('encuentra por nombre, código, lote, motivo o destino: %s', async (search, ids) => {
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const component = TestBed.createComponent(History).componentInstance;
    component.model.update((filters) => ({ ...filters, search }));
    await component.applyFilters(new Event('submit'));
    expect(component.filtered().map((movement) => movement.id)).toEqual(ids);
  });

  it('combina búsqueda, tipo, área y fechas, conserva la URL y elimina la búsqueda al limpiar', async () => {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(
      '/historial?busqueda=MED-001&tipo=exit&area=a1&desde=2026-10-01&hasta=2026-10-31',
      History,
    );
    expect(component.model().search).toBe('MED-001');
    expect(component.pagination.items().map((movement) => movement.id)).toEqual(['one']);
    component.model.update((filters) => ({ ...filters, search: 'Emergencia', productId: 'p1' }));
    await component.applyFilters(new Event('submit'));
    expect(component.pagination.items().map((movement) => movement.id)).toEqual(['one']);
    const url = TestBed.inject(Router).url;
    expect(url).toContain('busqueda=Emergencia');
    expect(url).toContain('tipo=exit');
    expect(url).toContain('area=a1');
    expect(url).toContain('producto=p1');
    expect(url).toContain('desde=2026-10-01');
    expect(url).toContain('hasta=2026-10-31');
    await component.resetFilters();
    expect(component.model().search).toBe('');
    expect(component.filtered()).toHaveLength(5);
    expect(TestBed.inject(Router).url).toBe('/historial');
  });
});
