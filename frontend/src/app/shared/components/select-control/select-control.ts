import {
  Component,
  ChangeDetectorRef,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  model,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { FormValueControl } from '@angular/forms/signals';
import { ConnectedPosition, Overlay, OverlayModule } from '@angular/cdk/overlay';
import { Icon } from '../icon/icon';
import { SelectOption } from '../../interface/select-option';

let nextSelectId = 0;

@Component({
  imports: [OverlayModule, Icon],
  selector: 'app-select-control',
  styleUrl: './select-control.scss',
  templateUrl: './select-control.html',
})
export class SelectControl implements FormValueControl<string> {
  readonly value = model('');
  readonly options = input<readonly SelectOption[]>([]);
  readonly label = input('Seleccionar opción');
  readonly inputId = input('');
  readonly placeholder = input('Selecciona una opción');
  readonly searchable = input(true);
  readonly compact = input(false);
  readonly disabled = input(false);
  readonly readonly = input(false);
  readonly required = input(false);
  readonly invalid = input(false);
  readonly touched = input(false);
  readonly touch = output<void>();

  private readonly document = inject(DOCUMENT);
  private readonly changeDetector = inject(ChangeDetectorRef);
  private readonly host = inject(ElementRef<HTMLElement>);
  private readonly generatedId = `select-control-${++nextSelectId}`;
  private readonly trigger = viewChild<ElementRef<HTMLButtonElement>>('trigger');
  private readonly search = viewChild<ElementRef<HTMLInputElement>>('search');
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');
  readonly scrollStrategy = inject(Overlay).scrollStrategies.reposition();
  readonly controlId = computed(() => this.inputId() || this.generatedId);
  readonly listId = computed(() => `${this.controlId()}-list`);
  readonly open = signal(false);
  readonly query = signal('');
  readonly activeIndex = signal(-1);
  readonly panelWidth = signal(280);
  readonly selected = computed(() =>
    this.options().find((option) => option.value === this.value()),
  );
  readonly filteredOptions = computed(() => {
    const query = this.normalize(this.query().trim());
    return this.options().filter(
      (option) =>
        !query || this.normalize(`${option.label} ${option.description ?? ''}`).includes(query),
    );
  });
  readonly activeId = computed(() =>
    this.open() && this.activeIndex() >= 0 ? `${this.listId()}-option-${this.activeIndex()}` : null,
  );
  readonly positions: ConnectedPosition[] = [
    { originX: 'start', originY: 'bottom', overlayX: 'start', overlayY: 'top', offsetY: 7 },
    { originX: 'start', originY: 'top', overlayX: 'start', overlayY: 'bottom', offsetY: -7 },
  ];

  constructor() {
    effect(() => {
      if (this.disabled() || this.readonly()) this.open.set(false);
    });
    effect(() => {
      // Keep the active descendant valid when options arrive or filters change.
      const options = this.filteredOptions();
      const current = this.activeIndex();
      if (!options[current] || options[current]?.disabled) {
        this.activeIndex.set(options.findIndex((option) => !option.disabled));
      }
    });
  }

  focus(options?: FocusOptions): void {
    this.trigger()?.nativeElement.focus(options);
  }

  toggle(): void {
    if (this.open()) this.close(true);
    else this.show();
  }

  private show(edge?: 'first' | 'last'): void {
    if (this.disabled() || this.readonly()) return;
    this.query.set('');
    const options = this.options();
    const selectedIndex = options.findIndex(
      (option) => option.value === this.value() && !option.disabled,
    );
    const first = options.findIndex((option) => !option.disabled);
    const last = this.lastEnabledIndex(options);
    this.activeIndex.set(
      edge === 'last'
        ? last
        : edge === 'first'
          ? first
          : selectedIndex >= 0
            ? selectedIndex
            : first,
    );
    const width = this.trigger()?.nativeElement.getBoundingClientRect().width ?? 280;
    const viewport = this.document.defaultView?.innerWidth ?? 1024;
    this.panelWidth.set(Math.min(Math.max(width, this.compact() ? 175 : 250), viewport - 24));
    this.open.set(true);
  }

  onAttached(): void {
    // The portal's input becomes available after its view has been rendered.
    queueMicrotask(() => {
      if (!this.open()) return;
      if (this.searchable()) this.search()?.nativeElement.focus();
      this.scrollActiveIntoView();
    });
  }

  close(restoreFocus = false): void {
    this.open.set(false);
    if (restoreFocus) this.focus();
  }

  onOutsideClick(): void {
    this.close(true);
  }

  onQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.activeIndex.set(this.filteredOptions().findIndex((option) => !option.disabled));
  }

  choose(option: SelectOption): void {
    if (option.disabled || this.disabled() || this.readonly()) return;
    this.value.set(option.value);
    this.close(true);
  }

  onKeydown(event: KeyboardEvent): void {
    if (this.disabled() || this.readonly()) return;
    const key = event.key;
    const fromSearch = event.target === this.search()?.nativeElement;
    if (key === 'Tab') {
      if (this.open()) {
        this.close(false);
        if (fromSearch) {
          event.preventDefault();
          this.focusAdjacent(event.shiftKey);
        }
      }
      return;
    }
    if (key === 'Escape' && this.open()) {
      event.preventDefault();
      event.stopPropagation();
      this.close(true);
      return;
    }
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      event.preventDefault();
      if (!this.open()) this.show(key === 'ArrowUp' ? 'last' : undefined);
      else this.moveActive(key === 'ArrowDown' ? 1 : -1);
    } else if ((key === 'Home' || key === 'End') && this.open()) {
      event.preventDefault();
      const options = this.filteredOptions();
      this.activeIndex.set(
        key === 'Home'
          ? options.findIndex((option) => !option.disabled)
          : this.lastEnabledIndex(options),
      );
      this.scrollActiveIntoView();
    } else if (key === 'Enter' || (key === ' ' && !fromSearch)) {
      event.preventDefault();
      if (!this.open()) this.show();
      else {
        const option = this.filteredOptions()[this.activeIndex()];
        if (option) this.choose(option);
      }
    }
  }

  onFocusOut(): void {
    // Moving from the trigger to the overlay is still interaction with one control.
    queueMicrotask(() => {
      const active = this.document.activeElement;
      if (
        active &&
        (this.host.nativeElement.contains(active) || this.panel()?.nativeElement.contains(active))
      )
        return;
      this.close(false);
      this.touch.emit();
      // The blur check runs after the DOM event; refresh FormField's host bindings
      // even when no surrounding template directly reads the touched state.
      this.changeDetector.markForCheck();
    });
  }

  private moveActive(direction: 1 | -1): void {
    const options = this.filteredOptions();
    if (!options.length) return;
    let index = this.activeIndex();
    for (let step = 0; step < options.length; step++) {
      index = (index + direction + options.length) % options.length;
      if (!options[index].disabled) {
        this.activeIndex.set(index);
        this.scrollActiveIntoView();
        return;
      }
    }
  }

  private scrollActiveIntoView(): void {
    queueMicrotask(() => {
      if (!this.open()) return;
      const id = this.activeId();
      if (id) this.document.getElementById(id)?.scrollIntoView?.({ block: 'nearest' });
    });
  }

  private focusAdjacent(backward: boolean): void {
    const trigger = this.trigger()?.nativeElement;
    const focusable = Array.from(
      this.document.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]',
      ),
    ).filter(
      (element) =>
        !this.panel()?.nativeElement.contains(element) &&
        !element.closest('[hidden], [inert]') &&
        element.getAttribute('aria-hidden') !== 'true' &&
        this.document.defaultView?.getComputedStyle(element).display !== 'none',
    );
    const index = trigger ? focusable.indexOf(trigger) : -1;
    const next = focusable[index + (backward ? -1 : 1)];
    if (next) next.focus();
    else trigger?.focus();
  }

  private normalize(value: string): string {
    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLocaleLowerCase('es');
  }

  private lastEnabledIndex(options: readonly SelectOption[]): number {
    for (let index = options.length - 1; index >= 0; index--) {
      if (!options[index].disabled) return index;
    }
    return -1;
  }
}
