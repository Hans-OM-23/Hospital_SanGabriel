import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { CategoryList } from './category-list';
import { CategoriesService } from '../../service/categories';
import { ApiError } from '../../../core/service/api-error';
import { Pagination } from '../../../shared/components/pagination/pagination';

describe('CategoryList: categorías dinámicas y validación', () => {
  const categories = signal([
    { id: 'c1', name: 'Medicamentos', description: 'Uso hospitalario', active: true },
  ]);
  const save = vi.fn();
  let component: CategoryList;
  let fixture: ComponentFixture<CategoryList>;

  const manyCategories = () =>
    Array.from({ length: 12 }, (_, index) => ({
      id: `c${index + 1}`,
      name: `Categoría ${index + 1}`,
      description: '',
      active: true,
    }));

  const paginationControl = () =>
    fixture.debugElement.query(By.directive(Pagination)).componentInstance as Pagination;

  beforeEach(async () => {
    save.mockReset().mockResolvedValue({ id: 'c2' });
    categories.set([
      { id: 'c1', name: 'Medicamentos', description: 'Uso hospitalario', active: true },
    ]);
    await TestBed.configureTestingModule({
      imports: [CategoryList],
      providers: [
        { provide: CategoriesService, useValue: { categories, save, productCount: () => 0 } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(CategoryList);
    component = fixture.componentInstance;
  });

  it('impide nombres vacíos y duplicados normalizados', async () => {
    component.model.set({ name: '   ', description: '' });
    await component.save(new Event('submit'));
    expect(save).not.toHaveBeenCalled();
    component.model.set({ name: ' medicamentos ', description: '' });
    expect(
      component.categoryForm
        .name()
        .errors()
        .some((error) => error.kind === 'duplicate'),
    ).toBe(true);
  });

  it('usa nuevas categorías desde el servicio sin listas fijas', () => {
    categories.update((values) => [
      ...values,
      { id: 'c2', name: 'Laboratorio', description: '', active: true },
    ]);
    component.filterModel.set({ search: 'LABORATORIO' });
    expect(component.categories().map((category) => category.id)).toEqual(['c2']);
  });

  it('registra una categoría válida y deja el formulario listo para otro registro', async () => {
    component.model.set({ name: ' Material médico ', description: ' Insumos de atención ' });
    await component.save(new Event('submit'));
    expect(save).toHaveBeenCalledWith({
      name: 'Material médico',
      description: 'Insumos de atención',
    });
    expect(component.model()).toEqual({ name: '', description: '' });
    expect(component.success()).toContain('registrada');
  });

  it('permite reintentar el registro sin editar datos después de un fallo del servicio', async () => {
    const draft = { name: 'Material médico', description: 'Insumos de atención' };
    component.model.set({ ...draft });
    save.mockRejectedValueOnce(new ApiError('El servicio no está disponible.'));
    await component.save(new Event('submit'));
    expect(component.error()).toBe('El servicio no está disponible.');
    expect(component.categoryForm().invalid()).toBe(true);
    expect(component.model()).toEqual(draft);
    await component.save(new Event('submit'));
    expect(save).toHaveBeenCalledTimes(2);
    expect(save).toHaveBeenNthCalledWith(2, draft);
    expect(component.success()).toContain('registrada');
    expect(component.error()).toBe('');
  });

  it('conserva visible el error de nombre duplicado devuelto por el servicio', async () => {
    component.model.set({ name: 'Material médico', description: '' });
    save.mockRejectedValueOnce(new ApiError('El nombre ya existe en el servicio.', 'name'));
    await component.save(new Event('submit'));
    expect(component.categoryForm.name().touched()).toBe(true);
    expect(
      component.categoryForm
        .name()
        .errors()
        .some((error) => error.kind === 'server' && error.message?.includes('ya existe')),
    ).toBe(true);
  });

  it('divide las categorías en páginas y busca en todos los registros desde la segunda página', async () => {
    categories.set(manyCategories());
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('.category-item')).toHaveLength(5);
    paginationControl().pageChange.emit(2);
    fixture.detectChanges();
    expect(component.pagination.page()).toBe(2);
    expect(fixture.nativeElement.querySelector('.category-item h3').textContent).toBe(
      'Categoría 6',
    );

    const search = fixture.nativeElement.querySelector(
      '.category-search input',
    ) as HTMLInputElement;
    search.value = 'Categoría 12';
    search.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.pagination.page()).toBe(1);
    expect(component.categories()).toHaveLength(1);
    expect(fixture.nativeElement.querySelectorAll('.category-item')).toHaveLength(1);
    expect(fixture.nativeElement.querySelector('.category-item h3').textContent).toBe(
      'Categoría 12',
    );
  });

  it('cambia el tamaño de página sin perder la búsqueda ni el borrador del formulario', () => {
    categories.set(manyCategories());
    component.filterModel.set({ search: 'Categoría' });
    component.model.set({ name: 'Nueva categoría', description: 'Borrador' });
    fixture.detectChanges();
    paginationControl().pageChange.emit(2);
    paginationControl().pageSizeChange.emit(10);
    fixture.detectChanges();

    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.pageSize()).toBe(10);
    expect(fixture.nativeElement.querySelectorAll('.category-item')).toHaveLength(10);
    expect(component.filterModel().search).toBe('Categoría');
    expect(component.model()).toEqual({ name: 'Nueva categoría', description: 'Borrador' });
  });

  it('registra después de paginar y muestra la página de la categoría nueva', async () => {
    categories.set(manyCategories());
    fixture.detectChanges();
    paginationControl().pageChange.emit(2);
    component.model.set({ name: 'Nueva categoría', description: 'Insumos' });
    save.mockImplementationOnce(async (input) => {
      const category = { ...input, id: 'c13', active: true };
      categories.update((values) => [...values, category]);
      return category;
    });

    await component.save(new Event('submit'));
    fixture.detectChanges();

    expect(component.pagination.page()).toBe(3);
    expect(component.pagination.totalItems()).toBe(13);
    expect(fixture.nativeElement.textContent).toContain('Nueva categoría');
    expect(component.model()).toEqual({ name: '', description: '' });
    expect(component.success()).toContain('registrada');
  });

  it('ajusta la página cuando se reducen las categorías disponibles', () => {
    categories.set(manyCategories());
    fixture.detectChanges();
    paginationControl().pageChange.emit(3);
    categories.update((values) => values.slice(0, 3));
    fixture.detectChanges();

    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.totalPages()).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.category-item')).toHaveLength(3);
  });

  it('conserva los controles y el estado vacío cuando no hay coincidencias', () => {
    categories.set(manyCategories());
    component.pagination.setPage(2);
    component.filterModel.set({ search: 'Sin coincidencias' });
    fixture.detectChanges();

    expect(component.pagination.page()).toBe(1);
    expect(component.pagination.totalItems()).toBe(0);
    expect(fixture.nativeElement.querySelector('.empty-state').textContent).toContain(
      'No encontramos categorías',
    );
    expect(paginationControl().totalItems()).toBe(0);
  });

  it('conserva la búsqueda y explica si oculta la categoría recién registrada', async () => {
    component.filterModel.set({ search: 'Medicamentos' });
    component.model.set({ name: 'Material médico', description: '' });
    save.mockImplementationOnce(async (input) => {
      const category = { ...input, id: 'c2', active: true };
      categories.update((values) => [...values, category]);
      return category;
    });

    await component.save(new Event('submit'));

    expect(component.filterModel().search).toBe('Medicamentos');
    expect(component.categories().map((category) => category.id)).toEqual(['c1']);
    expect(component.success()).toContain('no coincide con la búsqueda actual');
  });
});
