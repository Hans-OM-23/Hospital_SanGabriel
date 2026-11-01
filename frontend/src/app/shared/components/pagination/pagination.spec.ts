import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Pagination } from './pagination';
import { By } from '@angular/platform-browser';
import { OverlayContainer } from '@angular/cdk/overlay';
import { SelectControl } from '../select-control/select-control';

describe('Pagination: navegación accesible y tamaño de página', () => {
  let fixture: ComponentFixture<Pagination>;

  const button = (selector: string) =>
    fixture.nativeElement.querySelector(selector) as HTMLButtonElement;
  const range = () =>
    (fixture.nativeElement.querySelector('[role="status"]') as HTMLElement)
      .textContent!.replace(/\s+/g, ' ')
      .trim();

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Pagination] }).compileComponents();
    fixture = TestBed.createComponent(Pagination);
    fixture.componentRef.setInput('totalItems', 12);
    fixture.componentRef.setInput('label', 'productos');
    fixture.componentRef.setInput('singularLabel', 'producto');
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('muestra el rango y solicita otra página al pulsar Siguiente o un número', () => {
    const change = vi.fn();
    fixture.componentInstance.pageChange.subscribe(change);
    expect(range()).toBe('Mostrando 1–5 de 12 productos');
    expect(button('.previous').disabled).toBe(true);
    expect(button('[aria-current="page"]').textContent?.trim()).toBe('1');
    expect(fixture.nativeElement.querySelector('nav').getAttribute('aria-label')).toBe(
      'Paginación de productos',
    );

    button('.next').click();
    button('[aria-label="Ir a la página 3"]').click();
    expect(change.mock.calls).toEqual([[2], [3]]);
  });

  it('muestra el nombre singular cuando solo hay una coincidencia', () => {
    fixture.componentRef.setInput('totalItems', 1);
    fixture.detectChanges();
    expect(range()).toBe('Mostrando 1–1 de 1 producto');
    expect(button('.previous').disabled).toBe(true);
    expect(button('.next').disabled).toBe(true);
  });

  it('actualiza la última página y bloquea Siguiente sin impedir volver', () => {
    const change = vi.fn();
    fixture.componentInstance.pageChange.subscribe(change);
    fixture.componentRef.setInput('page', 3);
    fixture.detectChanges();
    expect(range()).toBe('Mostrando 11–12 de 12 productos');
    expect(button('.next').disabled).toBe(true);
    button('.next').click();
    button('.previous').click();
    expect(change.mock.calls).toEqual([[2]]);
  });

  it('informa cero resultados y deshabilita todos los botones de navegación', () => {
    const change = vi.fn();
    fixture.componentInstance.pageChange.subscribe(change);
    fixture.componentRef.setInput('totalItems', 0);
    fixture.detectChanges();
    expect(range()).toBe('Mostrando 0 de 0 productos');
    const buttons = fixture.nativeElement.querySelectorAll(
      'nav button',
    ) as NodeListOf<HTMLButtonElement>;
    expect(Array.from(buttons).every((button) => button.disabled)).toBe(true);
    buttons.forEach((button) => button.click());
    expect(change).not.toHaveBeenCalled();
  });

  it('ofrece 5, 10 y 20 registros y emite el tamaño elegido como número', async () => {
    const change = vi.fn();
    fixture.componentInstance.pageSizeChange.subscribe(change);
    const select = fixture.debugElement.query(By.directive(SelectControl))
      .componentInstance as SelectControl;
    expect(select.options().map((option) => option.value)).toEqual(['5', '10', '20']);
    (fixture.nativeElement.querySelector('[role="combobox"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    await fixture.whenStable();
    const overlay = TestBed.inject(OverlayContainer).getContainerElement();
    const option = Array.from(overlay.querySelectorAll('[role="option"]')).find(
      (item) => item.textContent?.trim() === '10',
    ) as HTMLElement;
    option.click();
    await fixture.whenStable();
    expect(change.mock.calls).toEqual([[10]]);

    fixture.componentRef.setInput('pageSize', 10);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(select.value()).toBe('10');
    expect(range()).toBe('Mostrando 1–10 de 12 productos');
    expect(change).toHaveBeenCalledTimes(1);
  });

  it('sincroniza un cambio externo de tamaño sin emitir otro evento', async () => {
    const change = vi.fn();
    fixture.componentInstance.pageSizeChange.subscribe(change);
    fixture.componentRef.setInput('pageSize', 20);
    fixture.detectChanges();
    await fixture.whenStable();
    const select = fixture.debugElement.query(By.directive(SelectControl))
      .componentInstance as SelectControl;
    expect(select.value()).toBe('20');
    expect(change).not.toHaveBeenCalled();
  });

  it('acota los números visibles y conserva accesibles la página actual y los extremos', () => {
    fixture.componentRef.setInput('totalItems', 500);
    fixture.componentRef.setInput('page', 50);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('.page-number').length).toBe(5);
    expect(fixture.nativeElement.querySelectorAll('.ellipsis').length).toBe(2);
    expect(button('[aria-current="page"]').textContent?.trim()).toBe('50');
    expect(button('[aria-label="Ir a la página 1"]')).toBeTruthy();
    expect(button('[aria-label="Ir a la página 100"]')).toBeTruthy();
  });
});
