import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { CategoryList } from './category-list';
import { CategoriesService } from '../../service/categories';
import { ApiError } from '../../../core/service/api-error';

describe('CategoryList: categorías dinámicas y validación', () => {
  const categories = signal([
    { id: 'c1', name: 'Medicamentos', description: 'Uso hospitalario', active: true },
  ]);
  const save = vi.fn();
  let component: CategoryList;

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
    component = TestBed.createComponent(CategoryList).componentInstance;
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
});
