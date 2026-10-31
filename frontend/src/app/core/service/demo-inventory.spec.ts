import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MovementInput } from '../../movements/interface/movement';
import { ProductInput } from '../../products/interface/product';
import { DemoInventory } from './demo-inventory';
import { offsetDate, today } from './date-utils';

const storageKey = 'san-gabriel.inventory.v1';

describe('DemoInventory: reglas de existencias y trazabilidad', () => {
  let gateway: DemoInventory;
  const entry = (changes: Partial<MovementInput> = {}): MovementInput => ({
    type: 'entry',
    productId: 'p-1',
    quantity: 5,
    date: today(),
    reason: 'Compra',
    lotNumber: 'PAR-026',
    expirationDate: offsetDate(180),
    ...changes,
  });
  const exit = (changes: Partial<MovementInput> = {}): MovementInput => ({
    type: 'exit',
    productId: 'p-1',
    quantity: 7,
    date: today(),
    reason: 'Reposición de insumos',
    lotId: 'l-1',
    areaId: 'emergencia',
    ...changes,
  });

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 31, 12));
    localStorage.removeItem(storageKey);
    gateway = new DemoInventory();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    localStorage.removeItem(storageKey);
  });

  it('persiste entradas y salidas junto con sus saldos, lote y destino', async () => {
    const initial = await gateway.load();
    const incoming = await gateway.registerMovement(entry());
    expect(incoming).toMatchObject({
      type: 'entry',
      quantity: 5,
      stockBefore: 40,
      stockAfter: 45,
      lotId: 'l-1',
      lotNumber: 'PAR-026',
      areaId: null,
    });
    const outgoing = await gateway.registerMovement(exit());
    expect(outgoing).toMatchObject({
      type: 'exit',
      quantity: 7,
      stockBefore: 45,
      stockAfter: 38,
      lotId: 'l-1',
      lotNumber: 'PAR-026',
      areaId: 'emergencia',
    });

    // Una instancia nueva debe recuperar tanto el saldo como el historial completo.
    const reloaded = await new DemoInventory().load();
    expect(reloaded.lots.find((lot) => lot.id === 'l-1')?.stock).toBe(38);
    expect(reloaded.movements).toHaveLength(initial.movements.length + 2);
    expect(reloaded.movements.slice(-2)).toEqual([incoming, outgoing]);
    expect(initial.lots.find((lot) => lot.id === 'l-1')?.stock).toBe(40);
  });

  it('rechaza una salida superior al saldo del lote aunque el producto tenga más existencias', async () => {
    const smallLot = await gateway.registerMovement(
      entry({ lotNumber: 'PAR-PEQUENO', expirationDate: offsetDate(60), quantity: 1 }),
    );
    const before = await gateway.load();
    expect(
      before.lots.filter((lot) => lot.productId === 'p-1').reduce((sum, lot) => sum + lot.stock, 0),
    ).toBe(41);
    await expect(
      gateway.registerMovement(exit({ lotId: smallLot.lotId, quantity: 2 })),
    ).rejects.toMatchObject({
      field: 'quantity',
      message: expect.stringContaining('solo dispone de 1'),
    });
    expect(await gateway.load()).toEqual(before);
  });

  it('bloquea el lote vencido y conserva sus existencias e historial', async () => {
    const before = await gateway.load();
    await expect(
      gateway.registerMovement(exit({ productId: 'p-3', lotId: 'l-3', quantity: 1 })),
    ).rejects.toMatchObject({ field: 'lotId', message: expect.stringContaining('vencido') });
    expect(await gateway.load()).toEqual(before);
  });

  it.each([0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, Number.MAX_SAFE_INTEGER + 1])(
    'rechaza una cantidad inválida (%s) en ambos tipos de movimiento',
    async (quantity) => {
      const before = await gateway.load();
      for (const input of [entry({ quantity }), exit({ quantity })]) {
        await expect(gateway.registerMovement(input)).rejects.toMatchObject({ field: 'quantity' });
      }
      expect(await gateway.load()).toEqual(before);
    },
  );

  it('rechaza códigos duplicados normalizando espacios y mayúsculas', async () => {
    const before = await gateway.load();
    const { id: _id, active: _active, ...source } = before.products[0];
    const input: ProductInput = { ...source, code: '  med-001  ', name: 'Otro producto' };
    await expect(gateway.saveProduct(input)).rejects.toMatchObject({ field: 'code' });
    expect(await gateway.load()).toEqual(before);
    await expect(
      gateway.saveProduct({ ...source, code: ' med-001 ' }, 'p-1'),
    ).resolves.toMatchObject({ code: 'MED-001', id: 'p-1' });
  });

  it('desactiva conservando lotes e historial e impide nuevos movimientos', async () => {
    const before = await gateway.load();
    await gateway.setProductActive('p-1', false);
    const after = await gateway.load();
    expect(after.products).toHaveLength(before.products.length);
    expect(after.products.find((product) => product.id === 'p-1')?.active).toBe(false);
    expect(after.lots).toEqual(before.lots);
    expect(after.movements).toEqual(before.movements);
    await expect(gateway.registerMovement(exit())).rejects.toMatchObject({ field: 'productId' });
    await expect(gateway.registerMovement(entry())).rejects.toMatchObject({ field: 'productId' });
  });

  it('impide cambiar la unidad o el control de vencimiento de productos con historial', async () => {
    const before = await gateway.load();
    const { id, active: _active, ...input } = before.products[0];
    await expect(gateway.saveProduct({ ...input, unit: 'Caja' }, id)).rejects.toMatchObject({
      field: 'unit',
    });
    await expect(
      gateway.saveProduct({ ...input, tracksExpiration: false }, id),
    ).rejects.toMatchObject({ field: 'tracksExpiration' });
    expect(await gateway.load()).toEqual(before);
  });

  it('rechaza reutilizar el número de lote con otro vencimiento', async () => {
    const before = await gateway.load();
    await expect(
      gateway.registerMovement(entry({ lotNumber: ' par-026 ', expirationDate: offsetDate(181) })),
    ).rejects.toMatchObject({
      field: 'expirationDate',
      message: expect.stringContaining('otro vencimiento'),
    });
    expect(await gateway.load()).toEqual(before);
  });

  it('una escritura fallida no cambia el saldo ni crea historial, tampoco en memoria', async () => {
    await gateway.reset();
    const before = await gateway.load();
    const write = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Sin espacio', 'QuotaExceededError');
    });
    await expect(gateway.registerMovement(entry())).rejects.toThrow('No se pudieron guardar');
    write.mockRestore();
    expect(await gateway.load()).toEqual(before);
    localStorage.removeItem(storageKey);
    expect(await gateway.load()).toEqual(before);
  });
});
