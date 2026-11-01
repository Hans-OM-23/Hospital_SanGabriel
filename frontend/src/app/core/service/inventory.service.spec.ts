import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { InventoryGateway } from '../interface/inventory';
import { ApiError } from './api-error';
import { offsetDate, today } from './date-utils';
import { DemoInventory } from './demo-inventory';
import { createDemoSeed } from './demo-seed';
import { InventoryService } from './inventory.service';

const storageKey = 'san-gabriel.inventory.v1';

describe('InventoryService: datos actualizados e indicadores', () => {
  let gateway: DemoInventory;
  let inventory: InventoryService;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 31, 12));
    localStorage.removeItem(storageKey);
    gateway = new DemoInventory();
    TestBed.configureTestingModule({
      providers: [{ provide: InventoryGateway, useValue: gateway }],
    });
    inventory = TestBed.inject(InventoryService);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    localStorage.removeItem(storageKey);
  });

  it('calcula indicadores con los tres productos del ejemplo y un plazo de 730 días', async () => {
    await inventory.refresh();
    expect(inventory.warningDays).toBe(730);
    expect(inventory.activeProducts()).toHaveLength(3);
    expect(inventory.lowStock().map((product) => product.id)).toEqual(['p-2', 'p-3']);
    expect(inventory.expiring().map((product) => product.id)).toEqual(['p-1']);
    expect(inventory.expired().map((product) => product.id)).toEqual(['p-3']);
    expect(inventory.inventoryValue()).toBe(157);
    expect(inventory.lastRefresh()).toBeInstanceOf(Date);
    expect(inventory.loading()).toBe(false);
  });

  it('incluye el día 730, excluye el 731 y los lotes sin saldo, y cuenta cada producto una vez', async () => {
    const snapshot = createDemoSeed();
    snapshot.lots = [
      { id: 'far', productId: 'p-1', number: 'FAR', expirationDate: offsetDate(731), stock: 1 },
      { id: 'edge', productId: 'p-1', number: 'EDGE', expirationDate: offsetDate(730), stock: 1 },
      { id: 'near', productId: 'p-1', number: 'NEAR', expirationDate: offsetDate(1), stock: 1 },
      { id: 'today', productId: 'p-1', number: 'TODAY', expirationDate: today(), stock: 1 },
      {
        id: 'gloves',
        productId: 'p-2',
        number: 'GLOVES',
        expirationDate: offsetDate(731),
        stock: 4,
      },
      { id: 'empty', productId: 'p-2', number: 'EMPTY', expirationDate: offsetDate(10), stock: 0 },
      {
        id: 'alcohol',
        productId: 'p-3',
        number: 'ALCOHOL',
        expirationDate: offsetDate(-1),
        stock: 2,
      },
      { id: 'undated', productId: 'p-1', number: 'UNDATED', expirationDate: null, stock: 1 },
    ];
    vi.spyOn(gateway, 'load').mockResolvedValue(snapshot);
    await inventory.refresh();
    expect(inventory.expiring().map((product) => product.id)).toEqual(['p-1']);
    expect(inventory.expired().map((product) => product.id)).toEqual(['p-3']);
    expect(inventory.productLots('p-1').map((lot) => lot.id)).toEqual([
      'today',
      'near',
      'edge',
      'far',
      'undated',
    ]);
    expect(snapshot.lots[0].id).toBe('far');
  });

  it('refresca existencias, historial e indicadores después de registrar una operación', async () => {
    await inventory.refresh();
    const initialCount = inventory.movements().length;
    const movement = await inventory.registerMovement({
      type: 'exit',
      productId: 'p-1',
      quantity: 20,
      date: today(),
      reason: 'Reposición de insumos',
      lotId: 'l-1',
      areaId: 'emergencia',
    });
    expect(inventory.stock('p-1')).toBe(20);
    expect(inventory.movements()).toHaveLength(initialCount + 1);
    expect(inventory.movements().at(-1)).toEqual(movement);
    expect(inventory.lowStock().some((product) => product.id === 'p-1')).toBe(true);
    expect(inventory.inventoryValue()).toBe(147);
    await inventory.refresh();
    expect(inventory.stock('p-1')).toBe(20);
    expect(inventory.movements().at(-1)?.stockAfter).toBe(20);
  });

  it('excluye productos desactivados de las alertas y permite consultar sus movimientos', async () => {
    await inventory.refresh();
    const historical = inventory.movements().filter((movement) => movement.productId === 'p-3');
    await inventory.setProductActive('p-3', false);
    expect(inventory.activeProducts()).toHaveLength(2);
    expect(inventory.expired()).toHaveLength(0);
    expect(inventory.lowStock().map((product) => product.id)).toEqual(['p-2']);
    expect(inventory.products().find((product) => product.id === 'p-3')?.active).toBe(false);
    expect(inventory.movements().filter((movement) => movement.productId === 'p-3')).toEqual(
      historical,
    );
    expect(inventory.stock('p-3')).toBe(2);
    expect(inventory.productName('p-3')).toBe('Alcohol al 70 %');
  });

  it('conserva la última consulta válida y muestra el error cuando falla la actualización', async () => {
    await inventory.refresh();
    const before = {
      products: inventory.products(),
      lots: inventory.lots(),
      movements: inventory.movements(),
    };
    const load = vi
      .spyOn(gateway, 'load')
      .mockRejectedValueOnce(new ApiError('El servicio no está disponible.'));
    await expect(inventory.refresh()).rejects.toThrow('El servicio no está disponible.');
    expect(inventory.error()).toBe('El servicio no está disponible.');
    expect(inventory.loading()).toBe(false);
    expect(inventory.products()).toEqual(before.products);
    expect(inventory.lots()).toEqual(before.lots);
    expect(inventory.movements()).toEqual(before.movements);
    load.mockRestore();
    await inventory.refresh();
    expect(inventory.error()).toBe('');
  });

  it('conserva el éxito del registro si falla la consulta posterior y evita sugerir otro registro', async () => {
    await inventory.refresh();
    const initialCount = inventory.movements().length;
    const write = vi.spyOn(gateway, 'registerMovement');
    // El primer load pertenece al registro local; el segundo es el refresco posterior.
    const savedLoad = gateway.load.bind(gateway);
    vi.spyOn(gateway, 'load')
      .mockImplementationOnce(savedLoad)
      .mockRejectedValueOnce(new ApiError('Falló la consulta posterior.'));
    const pending = inventory.registerMovement({
      type: 'exit',
      productId: 'p-1',
      quantity: 2,
      date: today(),
      reason: 'Reposición de insumos',
      lotId: 'l-1',
      areaId: 'emergencia',
    });
    await expect(pending).resolves.toMatchObject({ stockBefore: 40, stockAfter: 38 });
    expect(write).toHaveBeenCalledTimes(1);
    expect(inventory.error()).toContain('La operación se guardó');
    expect(inventory.error()).toMatch(/no repitas/i);
    expect(inventory.stock('p-1')).toBe(40);
    expect(inventory.movements()).toHaveLength(initialCount);
    expect(inventory.loading()).toBe(false);
    // Actualizar recupera el saldo sin volver a enviar la operación.
    vi.mocked(gateway.load).mockRestore();
    await inventory.refresh();
    expect(inventory.stock('p-1')).toBe(38);
    expect(inventory.movements()).toHaveLength(initialCount + 1);
    expect(write).toHaveBeenCalledTimes(1);
    expect(inventory.error()).toBe('');
  });
});
