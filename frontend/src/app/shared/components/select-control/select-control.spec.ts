import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { FormField, disabled, form, required } from '@angular/forms/signals';
import { SelectControl } from './select-control';
import { SelectOption } from '../../interface/select-option';

@Component({
  imports: [FormField, SelectControl],
  template: `
    <button type="button" id="before">Antes</button>
    <label for="category-picker">Categoría</label>
    <app-select-control
      [formField]="fields.category"
      [options]="options()"
      label="Categoría"
      inputId="category-picker"
      [searchable]="searchable()"
    />
    <button type="button" id="after">Después</button>
  `,
})
class SelectHarness {
  readonly model = signal({ category: '' });
  readonly blocked = signal(false);
  readonly searchable = signal(true);
  readonly options = signal<SelectOption[]>([
    { value: '', label: 'Todas las categorías' },
    { value: 'med', label: 'Medicación', description: 'Medicamentos de uso hospitalario' },
    { value: 'lab', label: 'Laboratorio', description: 'Material de análisis' },
    { value: 'clean', label: 'Limpieza', disabled: true, description: 'Categoría desactivada' },
  ]);
  readonly fields = form(this.model, (path) => {
    required(path.category);
    disabled(path.category, { when: () => this.blocked() });
  });
}

describe('SelectControl: selector accesible conectado con Signal Forms', () => {
  let fixture: ComponentFixture<SelectHarness>;
  let host: SelectHarness;
  const trigger = () => fixture.nativeElement.querySelector('.select-trigger') as HTMLButtonElement;
  const search = () => document.querySelector('.select-search') as HTMLInputElement;
  const options = () => Array.from(document.querySelectorAll<HTMLButtonElement>('.select-option'));
  const key = async (element: HTMLElement, value: string, shiftKey = false) => {
    element.dispatchEvent(
      new KeyboardEvent('keydown', { key: value, shiftKey, bubbles: true, cancelable: true }),
    );
    fixture.detectChanges();
    await fixture.whenStable();
  };
  const open = async () => {
    trigger().focus();
    trigger().click();
    fixture.detectChanges();
    await fixture.whenStable();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SelectHarness] }).compileComponents();
    fixture = TestBed.createComponent(SelectHarness);
    host = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('abre un panel fuera del contenedor y sincroniza la selección con el modelo del formulario', async () => {
    await open();
    expect(fixture.nativeElement.querySelector('.select-panel')).toBeNull();
    expect(document.querySelector('.select-panel')).toBeTruthy();
    expect(trigger().getAttribute('aria-expanded')).toBe('true');
    expect(document.activeElement).toBe(search());
    expect(options()[1].textContent).toContain('Medicamentos de uso hospitalario');
    options()[1].click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(host.model().category).toBe('med');
    expect(trigger().textContent).toContain('Medicación');
    expect(trigger().getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(trigger());
    expect(host.fields.category().dirty()).toBe(true);
  });

  it('busca sin distinguir tildes o mayúsculas y muestra un estado vacío comprensible', async () => {
    await open();
    search().value = 'MEDICACION';
    search().dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(options()).toHaveLength(1);
    expect(options()[0].textContent).toContain('Medicación');
    search().value = 'ANALISIS';
    search().dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(options()[0].textContent).toContain('Laboratorio');
    search().value = 'Sin coincidencia';
    search().dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    expect(options()).toHaveLength(0);
    expect(document.querySelector('.no-results')?.textContent).toContain('No hay coincidencias');
  });

  it('navega con flechas e inicio/final, omite opciones desactivadas y selecciona con Enter', async () => {
    await open();
    await key(search(), 'End');
    expect(search().getAttribute('aria-activedescendant')).toBe(options()[2].id);
    await key(search(), 'ArrowDown');
    expect(search().getAttribute('aria-activedescendant')).toBe(options()[0].id);
    await key(search(), 'Home');
    await key(search(), 'ArrowDown');
    await key(search(), 'Enter');
    expect(host.model().category).toBe('med');
    expect(document.querySelector('.select-panel')).toBeNull();
  });

  it('refleja cambios externos de valor y de opciones sin sobrescribir el modelo', async () => {
    host.model.set({ category: 'lab' });
    fixture.detectChanges();
    expect(trigger().textContent).toContain('Laboratorio');
    await open();
    host.options.set([{ value: 'lab', label: 'Laboratorio actualizado' }]);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(trigger().textContent).toContain('Laboratorio actualizado');
    expect(options()).toHaveLength(1);
    expect(options()[0].getAttribute('aria-selected')).toBe('true');
    expect(host.model().category).toBe('lab');
  });

  it('respeta la deshabilitación de Signal Forms y bloquea opciones no disponibles', async () => {
    await open();
    expect(options()[3].disabled).toBe(true);
    options()[3].click();
    expect(host.model().category).toBe('');
    host.blocked.set(true);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(trigger().disabled).toBe(true);
    expect(document.querySelector('.select-panel')).toBeNull();
    trigger().click();
    fixture.detectChanges();
    expect(trigger().getAttribute('aria-expanded')).toBe('false');
  });

  it('marca touched solo al abandonar el control, no al pasar del botón al buscador', async () => {
    await open();
    expect(host.fields.category().touched()).toBe(false);
    await key(search(), 'Tab');
    // The blur handler emits touch in a microtask after the overlay loses focus.
    fixture.detectChanges();
    await fixture.whenStable();
    expect(document.activeElement?.id).toBe('after');
    expect(host.fields.category().touched()).toBe(true);
    expect(trigger().getAttribute('aria-invalid')).toBe('true');
    expect(trigger().getAttribute('aria-required')).toBe('true');
  });

  it('permite Escape sin cambiar el valor y restaura el foco al botón vinculado a su label', async () => {
    await open();
    await key(search(), 'Escape');
    expect(host.model().category).toBe('');
    expect(document.activeElement).toBe(trigger());
    expect(trigger().id).toBe('category-picker');
    expect(trigger().getAttribute('aria-label')).toBe('Categoría');
    expect(host.fields.category().touched()).toBe(false);
  });

  it('funciona sin buscador usando Espacio y flechas sin enviar formularios', async () => {
    host.searchable.set(false);
    fixture.detectChanges();
    trigger().focus();
    await key(trigger(), ' ');
    expect(document.querySelector('.select-search')).toBeNull();
    expect(document.activeElement).toBe(trigger());
    await key(trigger(), 'ArrowDown');
    await key(trigger(), ' ');
    expect(host.model().category).toBe('med');
    expect(trigger().type).toBe('button');
  });

  it('impide abrir un control de solo lectura', async () => {
    const component = fixture.debugElement.query(By.directive(SelectControl))
      .componentInstance as SelectControl;
    const selectFixture = TestBed.createComponent(SelectControl);
    selectFixture.componentRef.setInput('readonly', true);
    selectFixture.detectChanges();
    const button = selectFixture.nativeElement.querySelector('button') as HTMLButtonElement;
    button.click();
    selectFixture.detectChanges();
    expect(button.getAttribute('aria-readonly')).toBe('true');
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(component.open()).toBe(false);
    selectFixture.destroy();
  });
});
