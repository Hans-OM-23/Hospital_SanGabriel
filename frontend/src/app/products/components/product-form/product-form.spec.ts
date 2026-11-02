import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { ProductForm } from './product-form';
import { ProductsService } from '../../service/products';
import { Product } from '../../interface/product';
import { ApiError } from '../../../core/service/api-error';

describe('ProductForm: registro y validaciones del catálogo', () => {
  const existing: Product = {
    id: 'p1',
    code: 'MED-001',
    name: 'Producto existente',
    description: 'Descripción',
    categoryId: 'c1',
    unit: 'Unidad',
    unitPrice: 1,
    minStock: 2,
    tracksExpiration: false,
    expirationDate: null,
    active: true,
  };
  const valid = {
    code: ' med-002 ',
    name: ' Producto nuevo ',
    description: ' Descripción nueva ',
    categoryId: 'c1',
    unit: 'Unidad',
    unitPrice: 2.5,
    minStock: 0,
    tracksExpiration: false,
    expirationDate: '',
  };
  let service: {
    products: ReturnType<typeof signal<Product[]>>;
    categories: ReturnType<typeof signal<{ id: string; name: string; active: boolean }[]>>;
    inventory: {
      loading: ReturnType<typeof signal<boolean>>;
      lastRefresh: ReturnType<typeof signal<Date | null>>;
      movements: ReturnType<typeof signal<{ productId: string }[]>>;
      warningDays: number;
    };
    save: ReturnType<typeof vi.fn>;
  };
  let component: ProductForm;
  let fixture: ComponentFixture<ProductForm>;
  let params: BehaviorSubject<ReturnType<typeof convertToParamMap>>;

  beforeEach(async () => {
    service = {
      products: signal([existing]),
      categories: signal([{ id: 'c1', name: 'Medicamentos', active: true }]),
      inventory: {
        loading: signal(false),
        lastRefresh: signal<Date | null>(new Date()),
        movements: signal<{ productId: string }[]>([]),
        warningDays: 730,
      },
      save: vi.fn().mockResolvedValue({
        ...existing,
        ...valid,
        id: 'p2',
        code: 'MED-002',
        name: 'Producto nuevo',
        description: 'Descripción nueva',
        expirationDate: null,
      }),
    };
    params = new BehaviorSubject(convertToParamMap({}));
    await TestBed.configureTestingModule({
      imports: [ProductForm],
      providers: [
        provideRouter([]),
        { provide: ProductsService, useValue: service },
        { provide: ActivatedRoute, useValue: { paramMap: params.asObservable() } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ProductForm);
    component = fixture.componentInstance;
    component.model.set({ ...valid });
  });

  it('detecta código duplicado aunque cambien espacios y mayúsculas', () => {
    component.model.update((model) => ({ ...model, code: ' med-001 ' }));
    expect(component.productForm.code().invalid()).toBe(true);
    expect(
      component.productForm
        .code()
        .errors()
        .some((error) => error.kind === 'duplicate'),
    ).toBe(true);
  });

  it('bloquea unidad y control de vencimiento al editar un producto con movimientos', () => {
    service.inventory.movements.set([{ productId: 'p1' }]);
    params.next(convertToParamMap({ id: 'p1' }));
    fixture.detectChanges();
    expect(component.hasMovements()).toBe(true);
    expect(component.productForm.unit().disabled()).toBe(true);
    expect(component.productForm.tracksExpiration().disabled()).toBe(true);
    expect(fixture.nativeElement.querySelector('#product-unit').disabled).toBe(true);
    expect(fixture.nativeElement.querySelector('input[type="checkbox"]').disabled).toBe(true);
    expect(fixture.nativeElement.textContent).toContain(
      'La unidad de medida y el control de vencimiento no se pueden cambiar',
    );
  });

  it('permite elegir unidad y vencimiento al registrar un producto nuevo', () => {
    service.inventory.movements.set([{ productId: 'p1' }]);
    fixture.detectChanges();
    expect(component.hasMovements()).toBe(false);
    expect(component.productForm.unit().disabled()).toBe(false);
    expect(component.productForm.tracksExpiration().disabled()).toBe(false);
  });

  it('rechaza precio vacío, cero, negativo y stock mínimo decimal', () => {
    for (const unitPrice of [NaN, 0, -1]) {
      component.model.update((model) => ({ ...model, unitPrice }));
      expect(component.productForm.unitPrice().invalid()).toBe(true);
    }
    component.model.update((model) => ({ ...model, unitPrice: 2.5, minStock: 1.5 }));
    expect(component.productForm.minStock().invalid()).toBe(true);
    component.model.update((model) => ({ ...model, minStock: 0 }));
    expect(component.productForm.minStock().valid()).toBe(true);
  });

  it('exige vencimiento solo cuando el producto lo requiere', () => {
    expect(component.productForm.expirationDate().valid()).toBe(true);
    component.model.update((model) => ({ ...model, tracksExpiration: true }));
    expect(component.productForm.expirationDate().invalid()).toBe(true);
    component.model.update((model) => ({ ...model, expirationDate: '2028-02-30' }));
    expect(component.productForm.expirationDate().invalid()).toBe(true);
    component.model.update((model) => ({ ...model, expirationDate: '2028-02-29' }));
    expect(component.productForm.expirationDate().valid()).toBe(true);
  });

  it('impide enviar datos inválidos y orienta con los errores del formulario', async () => {
    component.model.update((model) => ({ ...model, unitPrice: 0 }));
    await component.save(new Event('submit'));
    expect(service.save).not.toHaveBeenCalled();
    expect(component.productForm.unitPrice().touched()).toBe(true);
    expect(component.successOpen()).toBe(false);
  });

  it('normaliza código y texto y registra sin existencias iniciales', async () => {
    await component.save(new Event('submit'));
    expect(service.save).toHaveBeenCalledWith(
      expect.objectContaining({
        code: 'MED-002',
        name: 'Producto nuevo',
        description: 'Descripción nueva',
        expirationDate: null,
      }),
      undefined,
    );
    expect(component.saved()).toBe(true);
    expect(component.model().code).toBe('');
    expect(component.successOpen()).toBe(true);
    expect(component.savedProduct()?.name).toBe('Producto nuevo');
  });

  it('muestra junto al código el error de duplicado devuelto por el servicio', async () => {
    service.save.mockRejectedValue(new ApiError('El código ya existe en el servicio.', 'code'));
    await component.save(new Event('submit'));
    expect(
      component.productForm
        .code()
        .errors()
        .some((error) => error.kind === 'server' && error.message?.includes('ya existe')),
    ).toBe(true);
    expect(component.saved()).toBe(false);
    expect(component.successOpen()).toBe(false);
  });

  it('permite reintentar los mismos datos después de un error general del servicio', async () => {
    service.save.mockRejectedValueOnce(new ApiError('El servicio no está disponible.'));
    await component.save(new Event('submit'));
    expect(component.error()).toBe('El servicio no está disponible.');
    expect(component.successOpen()).toBe(false);
    expect(component.productForm().invalid()).toBe(true);
    expect(component.model()).toEqual(valid);
    await component.save(new Event('submit'));
    expect(service.save).toHaveBeenCalledTimes(2);
    expect(service.save).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ code: 'MED-002', name: 'Producto nuevo', unitPrice: 2.5 }),
      undefined,
    );
    expect(component.saved()).toBe(true);
    expect(component.error()).toBe('');
  });

  it('espera la confirmación del servicio antes de abrir la alerta', async () => {
    let resolveSave!: (product: Product) => void;
    service.save.mockImplementationOnce(
      () =>
        new Promise<Product>((resolve) => {
          resolveSave = resolve;
        }),
    );
    const pending = component.save(new Event('submit'));
    expect(component.productForm().submitting()).toBe(true);
    expect(component.successOpen()).toBe(false);
    expect(component.saved()).toBe(false);
    resolveSave({ ...existing, id: 'p2', code: 'MED-002', name: 'Producto nuevo' });
    await pending;
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector('[role="dialog"]') as HTMLElement;
    expect(dialog).not.toBeNull();
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.textContent).toContain('Producto registrado');
    expect(dialog.textContent).toContain('Producto nuevo');
    expect(dialog.textContent).toContain('MED-002');
    expect(document.body.style.overflow).toBe('hidden');
    const continueButton = Array.from(dialog.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Seguir registrando'),
    )!;
    continueButton.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="dialog"]')).toBeNull();
    expect(document.body.style.overflow).not.toBe('hidden');
    expect(component.model().code).toBe('');
    expect(component.saved()).toBe(true);
  });

  it('al editar solo envía ProductInput, sin id ni active, a FastAPI', async () => {
    params.next(convertToParamMap({ id: 'p1' }));
    fixture.detectChanges();
    component.model.update((model) => ({ ...model, unitPrice: 96 }));
    service.save.mockResolvedValueOnce({ ...existing, unitPrice: 96 });
    await component.save(new Event('submit'));
    const [input, id] = service.save.mock.calls[0] as [Record<string, unknown>, string];
    expect(id).toBe('p1');
    expect(input['unitPrice']).toBe(96);
    expect(input).not.toHaveProperty('id');
    expect(input).not.toHaveProperty('active');
  });

  it('conserva los datos al editar y cierra la confirmación mediante Escape', async () => {
    params.next(convertToParamMap({ id: 'p1' }));
    fixture.detectChanges();
    component.model.update((model) => ({ ...model, name: 'Nombre corregido' }));
    service.save.mockResolvedValueOnce({ ...existing, name: 'Nombre corregido' });
    await component.save(new Event('submit'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="dialog"]').textContent).toContain(
      'Producto actualizado',
    );
    expect(component.model().name).toBe('Nombre corregido');
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    fixture.detectChanges();
    expect(component.successOpen()).toBe(false);
    expect(component.model().name).toBe('Nombre corregido');
  });
});
