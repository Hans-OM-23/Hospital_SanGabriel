import { computed, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Product } from '../../interface/product';
import { ProductsService } from '../../service/products';
import { ProductList } from './product-list';

describe('ProductList: búsqueda y paginación conservando el catálogo', () => {
  const products = signal<Product[]>([]);
  const setActive = vi.fn(async (id: string, active: boolean) => {
    products.update((items) => items.map((item) => (item.id === id ? { ...item, active } : item)));
  });
  let fixture: ReturnType<typeof TestBed.createComponent<ProductList>>;
  let component: ProductList;

  beforeEach(async () => {
    products.set(
      Array.from({ length: 12 }, (_, index) => ({
        id: `p-${index + 1}`,
        code: `MED-${String(index + 1).padStart(3, '0')}`,
        name: `Insumo ${index + 1}`,
        description: 'Producto de prueba aislada',
        categoryId: index < 10 ? 'c-1' : 'c-2',
        unit: 'Unidad',
        unitPrice: 2,
        minStock: 1,
        tracksExpiration: false,
        expirationDate: null,
        active: true,
      })),
    );
    setActive.mockClear();
    await TestBed.configureTestingModule({
      imports: [ProductList],
      providers: [
        provideRouter([]),
        {
          provide: ProductsService,
          useValue: {
            products,
            categories: signal([
              { id: 'c-1', name: 'Medicamentos' },
              { id: 'c-2', name: 'Material médico' },
            ]),
            stock: () => 7,
            lots: () => [],
            setActive,
            inventory: {
              lowStock: computed(() => []),
              expiring: computed(() => []),
              movements: signal([]),
              warningDays: 730,
              categoryName: () => 'Categoría',
            },
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ProductList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('muestra páginas distintas y conserva los totales de todo el catálogo', async () => {
    expect(fixture.nativeElement.querySelectorAll('tbody > tr')).toHaveLength(5);
    const next = fixture.nativeElement.querySelector(
      'button[aria-label="Página siguiente"]',
    ) as HTMLButtonElement;
    next.click();
    fixture.detectChanges();
    expect(component.pagination.page()).toBe(2);
    expect(component.pagination.items().map((item) => item.id)).toEqual([
      'p-6',
      'p-7',
      'p-8',
      'p-9',
      'p-10',
    ]);
    expect(component.products()).toHaveLength(12);
    expect(component.activeCount()).toBe(12);
    expect(fixture.nativeElement.textContent).toContain('Mostrando 6–10 de 12 productos');
  });

  it('busca por código o nombre en todos los productos y reinicia la página', () => {
    component.changePage(2);
    component.filtersModel.update((filters) => ({ ...filters, search: 'med-012' }));
    fixture.detectChanges();
    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.items().map((item) => item.id)).toEqual(['p-12']);
    component.filtersModel.update((filters) => ({ ...filters, search: 'insumo 11' }));
    expect(component.pagination.items().map((item) => item.id)).toEqual(['p-11']);
  });

  it('combina categoría y estado antes de dividir resultados y admite búsquedas vacías', () => {
    component.changePage(3);
    component.filtersModel.set({ search: '', category: 'c-2', status: 'active' });
    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.items().map((item) => item.id)).toEqual(['p-11', 'p-12']);
    component.filtersModel.update((filters) => ({ ...filters, search: 'no existe' }));
    fixture.detectChanges();
    expect(component.pagination.items()).toEqual([]);
    expect(fixture.nativeElement.textContent).toContain('No encontramos productos');
    expect(
      fixture.nativeElement.querySelector('button[aria-label="Página siguiente"]').disabled,
    ).toBe(true);
  });

  it('mantiene la desactivación y ajusta la página si el último producto deja de coincidir', async () => {
    products.update((items) => items.slice(0, 11));
    component.changePage(3);
    const lastProduct = component.pagination.items()[0];
    component.confirmId.set(lastProduct.id);
    await component.toggleActive(lastProduct);
    fixture.detectChanges();
    expect(setActive).toHaveBeenCalledWith('p-11', false);
    expect(component.pagination.page()).toBe(2);
    expect(component.products()).toHaveLength(10);
    expect(component.confirmId()).toBeNull();
    component.filtersModel.set({ search: '', category: '', status: 'inactive' });
    expect(component.pagination.items().map((item) => item.id)).toEqual(['p-11']);
  });

  it('cierra detalles y confirmaciones al navegar o cambiar tamaño sin alterar registros', () => {
    component.selectedId.set('p-1');
    component.confirmId.set('p-1');
    component.changePage(2);
    expect(component.selectedId()).toBeNull();
    expect(component.confirmId()).toBeNull();
    component.selectedId.set('p-6');
    component.confirmId.set('p-6');
    component.changePageSize(10);
    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.items()).toHaveLength(10);
    expect(component.selectedId()).toBeNull();
    expect(component.confirmId()).toBeNull();
    expect(products()).toHaveLength(12);
  });
});
