import { TestBed } from '@angular/core/testing';
import { InventoryGateway } from '../../core/interface/inventory';
import { DemoInventory } from '../../core/service/demo-inventory';
import { InventoryService } from '../../core/service/inventory.service';
import { offsetDate, today } from '../../core/service/date-utils';
import { DashboardService } from './dashboard';

describe('Consultas por periodo', () => {
  let dashboard: DashboardService;
  let inventory: InventoryService;
  beforeEach(async () => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [{ provide: InventoryGateway, useClass: DemoInventory }],
    });
    dashboard = TestBed.inject(DashboardService);
    inventory = TestBed.inject(InventoryService);
    await inventory.refresh();
  });
  afterEach(() => localStorage.clear());

  it('incluye los límites del periodo y actualiza el ranking tras registrar otra salida', async () => {
    const initial = dashboard.summarize(offsetDate(-2), today());
    expect(initial.movements).toBe(1);
    expect(initial.exits).toBe(1);
    expect(initial.ranking[0]).toMatchObject({ productId: 'p-1', quantity: 10, unit: 'Tableta' });
    await inventory.registerMovement({
      type: 'exit',
      productId: 'p-1',
      quantity: 3,
      date: today(),
      reason: 'Reposición',
      areaId: 'laboratorio',
      lotId: 'l-1',
    });
    const updated = dashboard.summarize(offsetDate(-2), today());
    expect(updated.exits).toBe(2);
    expect(updated.ranking[0].quantity).toBe(13);
    expect(updated.series.reduce((sum, bucket) => sum + bucket.exits, 0)).toBe(2);
  });

  it('muestra consultas vacías sin alterar el inventario actual', () => {
    const stock = inventory.stock('p-1');
    const empty = dashboard.summarize(offsetDate(-100), offsetDate(-90));
    expect(empty.movements).toBe(0);
    expect(empty.ranking).toEqual([]);
    expect(inventory.stock('p-1')).toBe(stock);
    expect(inventory.activeProducts()).toHaveLength(3);
  });

  it('conserva todos los movimientos y claves únicas en periodos de varios años', () => {
    const summary = dashboard.summarize(offsetDate(-2555), today());
    expect(summary.movements).toBe(inventory.movements().length);
    expect(summary.series.reduce((sum, bucket) => sum + bucket.entries + bucket.exits, 0)).toBe(
      summary.movements,
    );
    expect(new Set(summary.series.map((bucket) => bucket.date)).size).toBe(summary.series.length);
  });
});
