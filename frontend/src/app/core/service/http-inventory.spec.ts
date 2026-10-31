import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { environment } from '../../../environments/environment';
import { InventorySnapshot } from '../interface/inventory';
import { MovementInput } from '../../movements/interface/movement';
import { ProductInput } from '../../products/interface/product';
import { createDemoSeed } from './demo-seed';
import { today } from './date-utils';
import { HttpInventory } from './http-inventory';

describe('HttpInventory: contrato HTTP preparado para FastAPI', () => {
  let http: HttpTestingController;
  let gateway: HttpInventory;
  const url = environment.apiUrl;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    gateway = TestBed.inject(HttpInventory);
  });
  afterEach(() => http.verify());

  const respondToSnapshot = (snapshot: InventorySnapshot) => {
    for (const endpoint of ['products', 'categories', 'lots', 'areas', 'movements'] as const) {
      const request = http.expectOne(`${url}/${endpoint}`);
      expect(request.request.method).toBe('GET');
      request.flush(snapshot[endpoint]);
    }
  };

  it('obtiene cinco recursos y devuelve categorías y datos actualizados en cada consulta', async () => {
    const initial = createDemoSeed();
    initial.categories = [
      {
        id: 'from-api',
        name: 'Categoría del servidor',
        description: 'Respuesta dinámica.',
        active: true,
      },
    ];
    const first = gateway.load();
    respondToSnapshot(initial);
    expect(await first).toEqual(initial);
    const updated = structuredClone(initial);
    updated.categories[0].name = 'Categoría actualizada';
    updated.lots[0].stock = 17;
    const second = gateway.load();
    respondToSnapshot(updated);
    const result = await second;
    expect(result.categories[0].name).toBe('Categoría actualizada');
    expect(result.lots[0].stock).toBe(17);
  });

  it('crea productos por POST y edita por PUT sin alterar los campos del formulario', async () => {
    const sample = createDemoSeed().products[0];
    const { id: _id, active: _active, ...input } = sample;
    const create = gateway.saveProduct(input);
    const post = http.expectOne(`${url}/products`);
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual(input);
    post.flush(sample);
    expect(await create).toEqual(sample);
    const changes: ProductInput = { ...input, name: 'Nombre actualizado' };
    const update = gateway.saveProduct(changes, 'p/1');
    const put = http.expectOne(`${url}/products/p%2F1`);
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual(changes);
    put.flush({ ...sample, ...changes });
    expect((await update).name).toBe('Nombre actualizado');
  });

  it('desactiva por PATCH y crea categorías usando la respuesta del servicio', async () => {
    const change = gateway.setProductActive('p-1', false);
    const patch = http.expectOne(`${url}/products/p-1/status`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ active: false });
    patch.flush(null);
    await expect(change).resolves.toBeUndefined();
    const input = { name: 'Nueva categoría', description: 'Material de muestra.' };
    const create = gateway.saveCategory(input);
    const post = http.expectOne(`${url}/categories`);
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual(input);
    post.flush({ ...input, id: 'category-api', active: true });
    expect(await create).toMatchObject({ ...input, id: 'category-api', active: true });
  });

  it('envía el lote y destino del movimiento y espera los saldos confirmados por la API', async () => {
    const response = createDemoSeed().movements[1];
    const input: MovementInput = {
      type: 'exit',
      productId: response.productId,
      quantity: response.quantity,
      date: response.date,
      reason: response.reason,
      lotId: response.lotId,
      areaId: response.areaId,
    };
    const pending = gateway.registerMovement(input);
    const request = http.expectOne(`${url}/movements`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(input);
    expect(request.request.body.stockAfter).toBeUndefined();
    request.flush(response);
    expect(await pending).toEqual(response);
  });

  it('propaga los errores de duplicado y validación que devuelva FastAPI', async () => {
    const { id: _id, active: _active, ...input } = createDemoSeed().products[0];
    const duplicate = gateway.saveProduct(input);
    const duplicateCheck = expect(duplicate).rejects.toMatchObject({
      status: 409,
      error: { detail: { field: 'code', message: 'El código ya existe.' } },
    });
    http
      .expectOne(`${url}/products`)
      .flush(
        { detail: { field: 'code', message: 'El código ya existe.' } },
        { status: 409, statusText: 'Conflict' },
      );
    await duplicateCheck;
    const movement: MovementInput = {
      type: 'exit',
      productId: 'p-1',
      quantity: 1000,
      date: today(),
      reason: 'Reposición',
      lotId: 'l-1',
      areaId: 'emergencia',
    };
    const invalid = gateway.registerMovement(movement);
    const detail = [{ loc: ['body', 'quantity'], msg: 'La cantidad supera las existencias.' }];
    const invalidCheck = expect(invalid).rejects.toMatchObject({ status: 422, error: { detail } });
    http
      .expectOne(`${url}/movements`)
      .flush({ detail }, { status: 422, statusText: 'Unprocessable Entity' });
    await invalidCheck;
  });
});
