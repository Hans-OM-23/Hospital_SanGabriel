import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormField, form, maxLength, required, submit, validate } from '@angular/forms/signals';
import { CategoriesService } from '../../service/categories';
import { FieldErrors } from '../../../shared/components/field-errors/field-errors';
import { Icon } from '../../../shared/components/icon/icon';
import { explainError } from '../../../core/service/api-error';
import { PaginationState } from '../../../shared/service/pagination-state';
import { Pagination } from '../../../shared/components/pagination/pagination';

@Component({
  selector: 'app-category-list',
  imports: [FormField, FieldErrors, Icon, Pagination],
  templateUrl: './category-list.html',
  styleUrl: './category-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CategoryList {
  readonly service = inject(CategoriesService);
  readonly filterModel = signal({ search: '' });
  readonly filters = form(this.filterModel);
  readonly model = signal({ name: '', description: '' });
  readonly error = signal('');
  readonly success = signal('');
  readonly categoryForm = form(this.model, (path) => {
    maxLength(path.name, 100, { message: 'El nombre admite hasta 100 caracteres.' });
    maxLength(path.description, 500, { message: 'La descripción admite hasta 500 caracteres.' });
    required(path.name, { message: 'Ingresa el nombre de la categoría.' });
    validate(path.name, ({ value }) => {
      if (!value()) return undefined;
      const name = value().trim().toLocaleLowerCase('es');
      if (!name) return { kind: 'required', message: 'El nombre no puede contener solo espacios.' };
      return this.service.categories().some((c) => c.name.trim().toLocaleLowerCase('es') === name)
        ? { kind: 'duplicate', message: 'Ya existe una categoría con este nombre.' }
        : undefined;
    });
  });
  readonly categories = computed(() => {
    const query = this.filterModel().search.trim().toLocaleLowerCase('es');
    return this.service
      .categories()
      .filter(
        (c) => !query || `${c.name} ${c.description}`.toLocaleLowerCase('es').includes(query),
      );
  });
  readonly pagination = new PaginationState(this.categories, this.filterModel);

  async save(event: Event) {
    event.preventDefault();
    if (this.categoryForm().submitting()) return;
    this.categoryForm().reset(structuredClone(this.model()));
    this.error.set('');
    this.success.set('');
    await submit(this.categoryForm, async () => {
      const input = this.model();
      try {
        const category = await this.service.save({
          name: input.name.trim(),
          description: input.description.trim(),
        });
        const index = this.categories().findIndex((item) => item.id === category.id);
        if (index >= 0) this.pagination.setPage(Math.floor(index / this.pagination.pageSize()) + 1);
        this.success.set(
          `Categoría «${input.name.trim()}» registrada. Ya está disponible para los productos.` +
            (index < 0 && this.filterModel().search.trim()
              ? ' No aparece en el listado porque no coincide con la búsqueda actual.'
              : ''),
        );
        this.categoryForm().reset({ name: '', description: '' });
        return undefined;
      } catch (error) {
        const apiError = explainError(error);
        if (apiError.field === 'name')
          return [{ fieldTree: this.categoryForm.name, kind: 'server', message: apiError.message }];
        this.error.set(apiError.message);
        return [{ fieldTree: this.categoryForm, kind: 'server', message: apiError.message }];
      }
    });
  }
}
