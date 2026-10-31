import {
  afterNextRender,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  Injector,
  input,
  model,
  output,
  signal,
  viewChild,
} from '@angular/core';
import {
  CdkConnectedOverlay,
  CdkOverlayOrigin,
  ConnectedPosition,
  Overlay,
} from '@angular/cdk/overlay';
import { FormValueControl } from '@angular/forms/signals';
import { Icon } from '../icon/icon';

interface CalendarDay {
  iso: string;
  day: number;
  label: string;
  inMonth: boolean;
  disabled: boolean;
}

let nextDatePickerId = 0;

@Component({
  imports: [CdkConnectedOverlay, CdkOverlayOrigin, Icon],
  selector: 'app-date-picker',
  styleUrl: './date-picker.scss',
  templateUrl: './date-picker.html',
})
export class DatePicker implements FormValueControl<string> {
  readonly value = model('');
  readonly disabled = input(false);
  readonly readonly = input(false);
  readonly required = input(false);
  readonly invalid = input(false);
  readonly touched = input(false);
  readonly touch = output<void>();
  readonly label = input('Fecha');
  readonly inputId = input('');
  readonly min = input<string | undefined>();
  readonly max = input<string | undefined>();
  readonly minDate = input<string | undefined>();
  readonly maxDate = input<string | undefined>();
  readonly compact = input(false);

  private readonly generatedId = `date-picker-${++nextDatePickerId}`;
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly injector = inject(Injector);
  private readonly textbox = viewChild<ElementRef<HTMLInputElement>>('textbox');
  private readonly overlay = viewChild(CdkConnectedOverlay);
  readonly id = computed(() => this.inputId() || this.generatedId);
  readonly calendarId = computed(() => `${this.id()}-calendar`);
  readonly open = signal(false);
  readonly focusedDate = signal(localISO(new Date()));
  readonly viewDate = signal(monthStart(new Date()));
  readonly displayValue = computed(() => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(this.value());
    return match ? `${match[3]}/${match[2]}/${match[1]}` : this.value();
  });
  readonly months = [
    'Enero',
    'Febrero',
    'Marzo',
    'Abril',
    'Mayo',
    'Junio',
    'Julio',
    'Agosto',
    'Septiembre',
    'Octubre',
    'Noviembre',
    'Diciembre',
  ];
  readonly weekdays = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
  readonly weekdayNames = [
    'Lunes',
    'Martes',
    'Miércoles',
    'Jueves',
    'Viernes',
    'Sábado',
    'Domingo',
  ];
  readonly heading = computed(
    () => `${this.months[this.viewDate().getMonth()]} de ${this.viewDate().getFullYear()}`,
  );
  readonly todayISO = signal(localISO(new Date()));
  readonly todayDisabled = computed(() => !this.allowed(this.todayISO()));
  readonly positions: ConnectedPosition[] = [
    { originX: 'start', originY: 'bottom', overlayX: 'start', overlayY: 'top', offsetY: 8 },
    { originX: 'start', originY: 'top', overlayX: 'start', overlayY: 'bottom', offsetY: -8 },
    { originX: 'end', originY: 'bottom', overlayX: 'end', overlayY: 'top', offsetY: 8 },
    { originX: 'end', originY: 'top', overlayX: 'end', overlayY: 'bottom', offsetY: -8 },
  ];
  readonly scrollStrategy = inject(Overlay).scrollStrategies.reposition();
  readonly weeks = computed(() => {
    const month = this.viewDate();
    const start = monthStart(month);
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    const days: CalendarDay[] = Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start);
      date.setDate(date.getDate() + index);
      const iso = localISO(date);
      return {
        iso,
        day: date.getDate(),
        label: new Intl.DateTimeFormat('es-PE', { dateStyle: 'full' }).format(date),
        inMonth: date.getMonth() === month.getMonth(),
        disabled: date.getFullYear() < 1 || date.getFullYear() > 9999 || !this.allowed(iso),
      };
    });
    return Array.from({ length: 6 }, (_, index) => days.slice(index * 7, index * 7 + 7));
  });

  constructor() {
    effect(() => {
      if (this.disabled() || this.readonly()) this.open.set(false);
    });
  }

  focus(options?: FocusOptions): void {
    this.textbox()?.nativeElement.focus(options);
  }

  onInput(event: Event): void {
    if (this.disabled() || this.readonly()) return;
    const raw = (event.target as HTMLInputElement).value;
    // Numeric keyboards on phones may not include a slash key.
    const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(raw) ?? /^(\d{2})(\d{2})(\d{4})$/.exec(raw);
    // Preserve invalid dates so the owning Signal Form can explain the error.
    this.value.set(match && Number(match[3]) > 0 ? `${match[3]}-${match[2]}-${match[1]}` : raw);
  }

  showCalendar(): void {
    if (this.disabled() || this.readonly()) return;
    this.todayISO.set(localISO(new Date()));
    const selected = parseISO(this.value()) ?? new Date();
    const date = this.clampDate(selected);
    this.focusedDate.set(localISO(date));
    this.viewDate.set(monthStart(date));
    this.open.set(true);
    this.focusCalendarDay();
  }

  toggleCalendar(): void {
    if (this.open()) this.close();
    else this.showCalendar();
  }

  close(returnFocus = true): void {
    if (returnFocus) this.focus({ preventScroll: true });
    this.open.set(false);
  }

  onBackdrop(): void {
    const active = this.host.nativeElement.ownerDocument.activeElement;
    if (active instanceof HTMLElement && this.contains(active)) active.blur();
    this.close(false);
  }

  onFocusOut(event: FocusEvent): void {
    const next = event.relatedTarget;
    if (next instanceof Node && this.contains(next)) return;
    this.touch.emit();
    this.close(false);
  }

  onInputKeydown(event: KeyboardEvent): void {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.showCalendar();
    } else if (event.key === 'Escape' && this.open()) {
      event.preventDefault();
      this.close();
    }
  }

  onOverlayKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      this.close();
    } else if (event.key === 'Tab') {
      const panel = this.overlay()?.overlayRef?.overlayElement;
      const controls = panel ? this.focusableElements(panel) : [];
      if (event.shiftKey && event.target === controls[0]) {
        event.preventDefault();
        this.close();
      } else if (!event.shiftKey && event.target === controls.at(-1)) {
        event.preventDefault();
        this.focusNextControl();
        this.close(false);
      }
    }
  }

  selectDate(iso: string): void {
    if (this.disabled() || this.readonly() || !this.allowed(iso)) return;
    this.value.set(iso);
    this.close();
  }

  clear(): void {
    if (this.disabled() || this.readonly()) return;
    this.value.set('');
    this.close();
  }

  changeMonth(event: Event): void {
    const month = Number((event.target as HTMLSelectElement).value);
    const date = monthStart(this.viewDate());
    date.setMonth(month);
    this.setView(date);
  }

  changeYear(event: Event): void {
    const target = event.target as HTMLInputElement;
    const year = Number(target.value);
    if (/^\d{1,4}$/.test(target.value) && year >= 1 && year <= 9999) {
      const date = monthStart(this.viewDate());
      date.setFullYear(year);
      this.setView(date);
    }
    target.value = String(this.viewDate().getFullYear());
  }

  navigateMonth(offset: number): void {
    const date = monthStart(this.viewDate());
    date.setMonth(date.getMonth() + offset);
    if (date.getFullYear() >= 1 && date.getFullYear() <= 9999) this.setView(date);
  }

  onDayKeydown(event: KeyboardEvent, iso: string): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.selectDate(iso);
      return;
    }
    const date = parseISO(iso)!;
    let handled = true;
    switch (event.key) {
      case 'ArrowLeft':
        date.setDate(date.getDate() - 1);
        break;
      case 'ArrowRight':
        date.setDate(date.getDate() + 1);
        break;
      case 'ArrowUp':
        date.setDate(date.getDate() - 7);
        break;
      case 'ArrowDown':
        date.setDate(date.getDate() + 7);
        break;
      case 'Home':
        date.setDate(date.getDate() - ((date.getDay() + 6) % 7));
        break;
      case 'End':
        date.setDate(date.getDate() + (6 - ((date.getDay() + 6) % 7)));
        break;
      case 'PageUp':
        shiftMonth(date, event.shiftKey ? -12 : -1);
        break;
      case 'PageDown':
        shiftMonth(date, event.shiftKey ? 12 : 1);
        break;
      default:
        handled = false;
    }
    if (!handled) return;
    event.preventDefault();
    const next = this.clampDate(date);
    this.focusedDate.set(localISO(next));
    this.viewDate.set(monthStart(next));
    this.focusCalendarDay();
  }

  private setView(date: Date): void {
    this.viewDate.set(date);
    const preferred = new Date(date);
    const focused = parseISO(this.focusedDate());
    const lastDay = new Date(date);
    lastDay.setMonth(lastDay.getMonth() + 1, 0);
    preferred.setDate(Math.min(focused?.getDate() ?? 1, lastDay.getDate()));
    const available = this.weeks()
      .flat()
      .find((day) => day.inMonth && !day.disabled);
    this.focusedDate.set(
      this.allowed(localISO(preferred)) ? localISO(preferred) : (available?.iso ?? ''),
    );
  }

  private allowed(iso: string): boolean {
    const min = this.minDate() ?? this.min();
    const max = this.maxDate() ?? this.max();
    return (
      !!parseISO(iso) &&
      (!min || !parseISO(min) || iso >= min) &&
      (!max || !parseISO(max) || iso <= max)
    );
  }

  private clampDate(date: Date): Date {
    const min = parseISO(this.minDate() ?? this.min() ?? '');
    const max = parseISO(this.maxDate() ?? this.max() ?? '');
    if (date.getFullYear() < 1) return parseISO('0001-01-01')!;
    if (date.getFullYear() > 9999) return parseISO('9999-12-31')!;
    if (min && date < min) return min;
    if (max && date > max) return max;
    return date;
  }

  private contains(node: Node): boolean {
    return (
      this.host.nativeElement.contains(node) ||
      !!this.overlay()?.overlayRef?.overlayElement.contains(node)
    );
  }

  private focusableElements(container: ParentNode): HTMLElement[] {
    const document = this.host.nativeElement.ownerDocument;
    return Array.from(
      container.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]',
      ),
    ).filter(
      (element) =>
        element.tabIndex >= 0 &&
        !element.closest('[hidden], [inert]') &&
        element.getAttribute('aria-hidden') !== 'true' &&
        document.defaultView?.getComputedStyle(element).display !== 'none',
    );
  }

  private focusNextControl(): void {
    const host = this.host.nativeElement;
    const panel = this.overlay()?.overlayRef?.overlayElement;
    const controls = this.focusableElements(host.ownerDocument).filter(
      (element) => !panel?.contains(element),
    );
    const lastLocal = controls.filter((element) => host.contains(element)).at(-1);
    const index = lastLocal ? controls.indexOf(lastLocal) : -1;
    const next = index >= 0 ? controls[index + 1] : null;
    if (next) next.focus();
    else {
      const active = host.ownerDocument.activeElement;
      if (active instanceof HTMLElement) active.blur();
    }
  }

  private focusCalendarDay(): void {
    afterNextRender(
      () => {
        if (!this.open()) return;
        const pane = this.overlay()?.overlayRef?.overlayElement;
        pane
          ?.querySelector<HTMLButtonElement>(`[data-date="${this.focusedDate()}"]`)
          ?.focus({ preventScroll: true });
      },
      { injector: this.injector },
    );
  }
}

function localISO(date: Date): string {
  return `${String(date.getFullYear()).padStart(4, '0')}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function parseISO(iso: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match || Number(match[1]) < 1) return null;
  const date = new Date(0);
  date.setHours(12, 0, 0, 0);
  date.setFullYear(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return localISO(date) === iso ? date : null;
}

function monthStart(date: Date): Date {
  const first = new Date(date);
  first.setHours(12, 0, 0, 0);
  first.setDate(1);
  return first;
}

function shiftMonth(date: Date, offset: number): void {
  const day = date.getDate();
  date.setDate(1);
  date.setMonth(date.getMonth() + offset);
  const last = new Date(date);
  last.setMonth(last.getMonth() + 1, 0);
  date.setDate(Math.min(day, last.getDate()));
}
