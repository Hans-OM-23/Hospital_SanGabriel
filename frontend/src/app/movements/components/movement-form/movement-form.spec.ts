import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { offsetDate, today } from '../../../core/service/date-utils';
import { InventoryService } from '../../../core/service/inventory.service';
import { ApiError } from '../../../core/service/api-error';
import { Movement } from '../../interface/movement';
import { MovementForm } from './movement-form';

describe('MovementForm: reglas de entradas y salidas', () => {
  let fixture: ComponentFixture<MovementForm>;
  let component: MovementForm;
  const product = {
    id: 'p1',
    code: 'MED-01',
    name: 'Paracetamol',
    description: '',
    categoryId: 'c1',
    unit: 'Unidad',
    unitPrice: 1,
    minStock: 2,
    tracksExpiration: true,
    expirationDate: null,
    active: true,
  };
  const lots = [
    { id: 'expired', productId: 'p1', number: 'VENCIDO', stock: 3, expirationDate: offsetDate(-1) },
    { id: 'valid', productId: 'p1', number: 'VIGENTE', stock: 5, expirationDate: offsetDate(50) },
  ];
  const result: Movement = {
    id: 'mov1',
    type: 'entry',
    productId: 'p1',
    quantity: 2,
    date: today(),
    reason: 'Compra',
    stockBefore: 8,
    stockAfter: 10,
    lotId: 'new',
    lotNumber: 'NUEVO',
    expirationDate: offsetDate(100),
    areaId: null,
  };
  const registerMovement = vi.fn().mockResolvedValue(result);

  beforeEach(async () => {
    registerMovement.mockReset().mockResolvedValue(result);
    await TestBed.configureTestingModule({
      imports: [MovementForm],
      providers: [
        provideRouter([]),
        {
          provide: InventoryService,
          useValue: {
            activeProducts: signal([product]),
            areas: signal([{ id: 'emergency', name: 'Emergencia' }]),
            productLots: () => lots,
            stock: () => 8,
            productName: () => product.name,
            registerMovement,
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(MovementForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
    component.model.update((draft) => ({ ...draft, productId: 'p1' }));
    fixture.detectChanges();
  });

  it.each(['', '0', '-2', '1.5', 'abc', '9007199254740992'])(
    'rechaza la cantidad inválida "%s"',
    (quantity) => {
      component.model.update((draft) => ({ ...draft, quantity }));
      expect(component.movementForm.quantity().invalid()).toBe(true);
    },
  );

  it('muestra errores junto a los campos después de un envío inválido', async () => {
    await component.save(new Event('submit'));
    fixture.detectChanges();
    expect(registerMovement).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Ingresa una cantidad.');
    expect(fixture.nativeElement.textContent).toContain('Ingresa el número de lote.');
  });

  it('exige el vencimiento de una entrada que lo requiere', () => {
    expect(component.movementForm.expirationDate().invalid()).toBe(true);
    component.model.update((draft) => ({ ...draft, expirationDate: offsetDate(100) }));
    expect(component.movementForm.expirationDate().valid()).toBe(true);
  });

  it('rechaza una fecha de movimiento futura', () => {
    component.model.update((draft) => ({ ...draft, date: offsetDate(1) }));
    expect(component.movementForm.date().invalid()).toBe(true);
  });

  it('exige un lote manual, bloquea lotes vencidos y limita la cantidad al saldo de ese lote', () => {
    component.model.update((draft) => ({ ...draft, type: 'exit' }));
    fixture.detectChanges();
    expect(component.model().lotId).toBe('');
    expect(component.movementForm.lotId().invalid()).toBe(true);
    component.model.update((draft) => ({ ...draft, lotId: 'expired', quantity: '1' }));
    expect(
      component.movementForm
        .lotId()
        .errors()
        .some((error) => error.kind === 'expired'),
    ).toBe(true);
    component.model.update((draft) => ({ ...draft, lotId: 'valid', quantity: '6' }));
    expect(
      component.movementForm
        .quantity()
        .errors()
        .some((error) => error.kind === 'stock'),
    ).toBe(true);
    expect(component.movementForm.areaId().invalid()).toBe(true);
    component.model.update((draft) => ({
      ...draft,
      quantity: '5',
      areaId: 'emergency',
      reason: 'Atención de pacientes',
    }));
    expect(component.movementForm().valid()).toBe(true);
  });

  it('confirma una entrada válida con sus saldos y el enlace al historial', async () => {
    component.model.update((draft) => ({
      ...draft,
      quantity: '2',
      reason: 'Compra',
      lotNumber: 'NUEVO',
      expirationDate: offsetDate(100),
    }));
    await component.save(new Event('submit'));
    fixture.detectChanges();
    expect(registerMovement).toHaveBeenCalledWith(
      expect.objectContaining({ quantity: 2, productId: 'p1', lotNumber: 'NUEVO' }),
    );
    expect(component.success()?.stockAfter).toBe(10);
    expect(fixture.nativeElement.textContent).toContain('8 → 10');
    expect(
      fixture.nativeElement.querySelector('a[href="/historial?movimiento=mov1"]'),
    ).toBeTruthy();
  });

  it('permite reintentar el movimiento sin editar datos después de un fallo del servicio', async () => {
    component.model.update((draft) => ({
      ...draft,
      quantity: '2',
      reason: 'Compra',
      lotNumber: 'NUEVO',
      expirationDate: offsetDate(100),
    }));
    const before = structuredClone(component.model());
    registerMovement.mockRejectedValueOnce(new ApiError('El servicio no está disponible.'));
    await component.save(new Event('submit'));
    expect(component.error()).toBe('El servicio no está disponible.');
    expect(component.movementForm().invalid()).toBe(true);
    expect(component.model()).toEqual(before);
    await component.save(new Event('submit'));
    expect(registerMovement).toHaveBeenCalledTimes(2);
    expect(registerMovement).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        quantity: 2,
        productId: 'p1',
        lotNumber: 'NUEVO',
        expirationDate: offsetDate(100),
      }),
    );
    expect(component.success()).toEqual(result);
    expect(component.error()).toBe('');
  });
});
