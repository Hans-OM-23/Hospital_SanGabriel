import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { OverlayContainer } from '@angular/cdk/overlay';
import { disabled, FormField, form, readonly, required, validate } from '@angular/forms/signals';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { isDate, today } from '../../../core/service/date-utils';
import { DatePicker } from './date-picker';

@Component({
  imports: [DatePicker, FormField],
  template: `
    <label for="test-date">Fecha de vencimiento</label>
    <app-date-picker
      inputId="test-date"
      label="Fecha de vencimiento"
      [formField]="dateForm.date"
      [minDate]="minimum()"
      [maxDate]="maximum()"
    />
    <button id="outside" type="button">Continuar</button>
  `,
})
class DateFormHarness {
  readonly model = signal({ date: '2028-02-15' });
  readonly unavailable = signal(false);
  readonly readOnly = signal(false);
  readonly minimum = signal<string | undefined>(undefined);
  readonly maximum = signal<string | undefined>(undefined);
  readonly dateForm = form(this.model, (path) => {
    required(path.date, { message: 'Selecciona una fecha.' });
    disabled(path.date, () => this.unavailable());
    readonly(path.date, () => this.readOnly());
    validate(path.date, ({ value }) =>
      value() && !isDate(value())
        ? { kind: 'date', message: 'Ingresa una fecha válida.' }
        : undefined,
    );
  });
}

describe('DatePicker: fechas locales y calendario accesible con Signal Forms', () => {
  let fixture: ComponentFixture<DateFormHarness>;
  let harness: DateFormHarness;
  let overlay: HTMLElement;

  const textbox = () => fixture.nativeElement.querySelector('#test-date') as HTMLInputElement;
  const calendarButton = () =>
    fixture.nativeElement.querySelector('.calendar-toggle') as HTMLButtonElement;
  const day = (iso: string) => overlay.querySelector(`[data-date="${iso}"]`) as HTMLButtonElement;
  const write = async (text: string) => {
    textbox().value = text;
    textbox().dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    await fixture.whenStable();
  };
  const open = async () => {
    calendarButton().click();
    fixture.detectChanges();
    await fixture.whenStable();
  };
  const keydown = async (element: HTMLElement, key: string, shiftKey = false) => {
    element.dispatchEvent(
      new KeyboardEvent('keydown', { key, shiftKey, bubbles: true, cancelable: true }),
    );
    fixture.detectChanges();
    await fixture.whenStable();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [DateFormHarness] }).compileComponents();
    fixture = TestBed.createComponent(DateFormHarness);
    harness = fixture.componentInstance;
    overlay = TestBed.inject(OverlayContainer).getContainerElement();
    fixture.detectChanges();
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('muestra ISO como día/mes/año y asocia la etiqueta al textbox real', async () => {
    expect(textbox().value).toBe('15/02/2028');
    expect(textbox().getAttribute('aria-label')).toBe('Fecha de vencimiento');
    const label = fixture.nativeElement.querySelector('label') as HTMLLabelElement;
    expect(label.control).toBe(textbox());
    expect(textbox().required).toBe(true);

    harness.model.set({ date: '2032-12-31' });
    fixture.detectChanges();
    await fixture.whenStable();
    expect(textbox().value).toBe('31/12/2032');
  });

  it.each([
    ['29/02/2028', '2028-02-29', true],
    ['29/02/2000', '2000-02-29', true],
    ['29/02/1900', '1900-02-29', false],
    ['30/02/2028', '2028-02-30', false],
    ['31/04/2028', '2028-04-31', false],
    ['31/12/2045', '2045-12-31', true],
  ])('interpreta %s sin corregir silenciosamente la fecha', async (text, iso, valid) => {
    await write(text);
    expect(harness.model().date).toBe(iso);
    expect(textbox().value).toBe(text);
    expect(harness.dateForm.date().valid()).toBe(valid);
  });

  it('conserva una fecha incompleta y el formulario puede explicar el error', async () => {
    await write('29/0');
    expect(harness.model().date).toBe('29/0');
    expect(textbox().value).toBe('29/0');
    expect(
      harness.dateForm
        .date()
        .errors()
        .some((error) => error.kind === 'date'),
    ).toBe(true);
  });

  it('acepta ocho dígitos desde el teclado numérico móvil y añade los separadores', async () => {
    await write('29022028');
    expect(harness.model().date).toBe('2028-02-29');
    expect(textbox().value).toBe('29/02/2028');
    expect(harness.dateForm.date().valid()).toBe(true);
  });

  it('muestra el mes seleccionado, semana desde lunes y devuelve el ISO del día elegido', async () => {
    await open();
    expect(overlay.querySelector('[role="dialog"]')?.getAttribute('aria-label')).toBe(
      'Elegir fecha de vencimiento',
    );
    expect(Array.from(overlay.querySelectorAll('th'), (th) => th.textContent?.trim())).toEqual([
      'L',
      'M',
      'X',
      'J',
      'V',
      'S',
      'D',
    ]);
    expect(day('2028-02-15').classList.contains('selected')).toBe(true);
    expect(overlay.querySelectorAll('.day-button[tabindex="0"]').length).toBe(1);
    day('2028-02-29').click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(harness.model().date).toBe('2028-02-29');
    expect(textbox().value).toBe('29/02/2028');
    expect(overlay.querySelector('[role="dialog"]')).toBeNull();
    expect(document.activeElement).toBe(textbox());
  });

  it('sincroniza el selector de mes al abrir y al navegar con las flechas', async () => {
    harness.model.set({ date: '2026-10-31' });
    fixture.detectChanges();
    await fixture.whenStable();
    await open();
    const month = () => overlay.querySelector('[aria-label="Mes"]') as HTMLSelectElement;
    expect(month().value).toBe('9');
    expect(month().selectedOptions[0]?.textContent?.trim()).toBe('Octubre');
    expect(overlay.querySelector('[role="grid"]')?.getAttribute('aria-label')).toBe(
      'Octubre de 2026',
    );

    (overlay.querySelector('[aria-label="Mes siguiente"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(month().value).toBe('10');
    expect(month().selectedOptions[0]?.textContent?.trim()).toBe('Noviembre');
    expect(overlay.querySelector('[role="grid"]')?.getAttribute('aria-label')).toBe(
      'Noviembre de 2026',
    );

    (overlay.querySelector('[aria-label="Mes anterior"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(month().value).toBe('9');
    expect(month().selectedOptions[0]?.textContent?.trim()).toBe('Octubre');
  });

  it('deshabilita días fuera de min/max y no permite seleccionarlos', async () => {
    harness.minimum.set('2028-02-10');
    harness.maximum.set('2028-02-20');
    fixture.detectChanges();
    await fixture.whenStable();
    await open();
    expect(day('2028-02-09').disabled).toBe(true);
    expect(day('2028-02-10').disabled).toBe(false);
    expect(day('2028-02-20').disabled).toBe(false);
    expect(day('2028-02-21').disabled).toBe(true);
    day('2028-02-21').click();
    expect(harness.model().date).toBe('2028-02-15');
    day('2028-02-20').click();
    expect(harness.model().date).toBe('2028-02-20');
  });

  it('navega por flechas, inicio/fin de semana y meses, y selecciona con Enter', async () => {
    await keydown(textbox(), 'ArrowDown');
    await keydown(day('2028-02-15'), 'ArrowRight');
    expect(document.activeElement).toBe(day('2028-02-16'));
    await keydown(day('2028-02-16'), 'Home');
    expect(document.activeElement).toBe(day('2028-02-14'));
    await keydown(day('2028-02-14'), 'End');
    expect(document.activeElement).toBe(day('2028-02-20'));
    await keydown(day('2028-02-20'), 'PageDown');
    expect(document.activeElement).toBe(day('2028-03-20'));
    await keydown(day('2028-03-20'), 'Enter');
    expect(harness.model().date).toBe('2028-03-20');
  });

  it('permite escribir un año lejano y cambiar el mes sin múltiples clics', async () => {
    await open();
    const year = overlay.querySelector('[aria-label="Año"]') as HTMLInputElement;
    year.value = '2070';
    year.dispatchEvent(new Event('change', { bubbles: true }));
    fixture.detectChanges();
    await fixture.whenStable();
    const month = overlay.querySelector('[aria-label="Mes"]') as HTMLSelectElement;
    month.value = '11';
    month.dispatchEvent(new Event('change', { bubbles: true }));
    fixture.detectChanges();
    await fixture.whenStable();
    day('2070-12-31').click();
    expect(harness.model().date).toBe('2070-12-31');
  });

  it('Hoy usa la fecha local y Limpiar activa la validación obligatoria', async () => {
    await open();
    (overlay.querySelector('.today-button') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(harness.model().date).toBe(today());
    await open();
    (overlay.querySelector('.clear-button') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(harness.model().date).toBe('');
    expect(
      harness.dateForm
        .date()
        .errors()
        .some((error) => error.kind === 'required'),
    ).toBe(true);
  });

  it('cierra con Escape y devuelve el foco sin marcar touched por moverse dentro del calendario', async () => {
    await open();
    expect(harness.dateForm.date().touched()).toBe(false);
    await keydown(day('2028-02-15'), 'Escape');
    expect(overlay.querySelector('[role="dialog"]')).toBeNull();
    expect(document.activeElement).toBe(textbox());
    expect(harness.dateForm.date().touched()).toBe(false);
    (fixture.nativeElement.querySelector('#outside') as HTMLButtonElement).focus();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(harness.dateForm.date().touched()).toBe(true);
  });

  it('cierra al hacer clic fuera del calendario', async () => {
    await open();
    const backdrop = overlay.querySelector('.cdk-overlay-backdrop') as HTMLElement;
    expect(backdrop).toBeTruthy();
    backdrop.click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(overlay.querySelector('[role="dialog"]')).toBeNull();
  });

  it('Tab desde el último control del calendario continúa en el siguiente campo del formulario', async () => {
    await open();
    const last = overlay.querySelector('.today-button') as HTMLButtonElement;
    last.focus();
    await keydown(last, 'Tab');
    expect(document.activeElement).toBe(fixture.nativeElement.querySelector('#outside'));
    expect(overlay.querySelector('[role="dialog"]')).toBeNull();
    expect(harness.dateForm.date().touched()).toBe(true);
  });

  it('Shift+Tab desde el primer control regresa al textbox de fecha', async () => {
    await open();
    const first = overlay.querySelector('[aria-label="Mes anterior"]') as HTMLButtonElement;
    first.focus();
    await keydown(first, 'Tab', true);
    expect(document.activeElement).toBe(textbox());
    expect(overlay.querySelector('[role="dialog"]')).toBeNull();
    expect(harness.dateForm.date().touched()).toBe(false);
  });

  it('respeta disabled y readonly de Signal Forms sin permitir abrir ni modificar', async () => {
    harness.unavailable.set(true);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(textbox().disabled).toBe(true);
    expect(calendarButton().disabled).toBe(true);
    calendarButton().click();
    expect(overlay.querySelector('[role="dialog"]')).toBeNull();
    harness.unavailable.set(false);
    harness.readOnly.set(true);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(textbox().readOnly).toBe(true);
    expect(calendarButton().disabled).toBe(true);
    await write('01/01/2040');
    expect(harness.model().date).toBe('2028-02-15');
  });
});
