import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InventoryService } from '../../../core/service/inventory.service';
import { History } from './history';

describe('History: consulta combinada y validación de fechas', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [History],
      providers: [
        provideRouter([{ path: 'historial', component: History }]),
        {
          provide: InventoryService,
          useValue: {
            products: signal([]),
            areas: signal([]),
            loading: signal(false),
            movements: signal([
              { id: 'one', productId: 'p1', type: 'exit', areaId: 'a1', date: '2026-10-02' },
              { id: 'two', productId: 'p1', type: 'exit', areaId: 'a2', date: '2026-10-02' },
              { id: 'three', productId: 'p1', type: 'entry', areaId: null, date: '2026-10-01' },
              { id: 'four', productId: 'p2', type: 'exit', areaId: 'a1', date: '2026-10-02' },
              { id: 'five', productId: 'p1', type: 'exit', areaId: 'a1', date: '2026-09-01' },
            ]),
            productName: (id: string) => id,
            areaName: (id: string | null) => id ?? 'Almacén central',
          },
        },
      ],
    });
  });

  it('combina producto, tipo, área y rango de fechas en la misma consulta', async () => {
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const component = TestBed.createComponent(History).componentInstance;
    component.model.set({
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
});
