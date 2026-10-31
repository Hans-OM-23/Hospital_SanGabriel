import { Component, computed, input } from '@angular/core';

@Component({
  imports: [],
  selector: 'app-icon',
  styleUrl: './icon.scss',
  templateUrl: './icon.html',
})
export class Icon {
  readonly name = input('box');
  readonly paths = computed(() => ICONS[this.name()] ?? ICONS['box']);
}

const ICONS: Record<string, string[]> = {
  power: ['M12 2v10', 'M5 5a9 9 0 1 0 14 0'],
  'log-in': ['M15 3h6v18h-6 M3 12h13m-5-5 5 5-5 5'],
  'alert-circle': ['M12 8v5 M12 17h.01', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  'eye-off': [
    'm3 3 18 18 M10 5a13 13 0 0 1 12 7 18 18 0 0 1-4 5 M6 6a19 19 0 0 0-4 6s3.5 7 10 7a13 13 0 0 0 5-1 M10 10a3 3 0 0 0 4 4',
  ],
  dashboard: ['M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z'],
  grid: ['M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z'],
  box: ['m12 3 9 5v8l-9 5-9-5V8z', 'm3 8 9 5 9-5 M12 13v8 M7.5 5.5l9 5'],
  package: ['m12 3 9 5v8l-9 5-9-5V8z', 'm3 8 9 5 9-5 M12 13v8 M7.5 5.5l9 5'],
  layers: ['m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5'],
  categories: ['m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5'],
  arrows: ['M4 7h15m-4-4 4 4-4 4 M20 17H5m4-4-4 4 4 4'],
  'arrow-down-up': ['M4 7h15m-4-4 4 4-4 4 M20 17H5m4-4-4 4 4 4'],
  history: ['M3 11a9 9 0 1 1 2.5 7 M3 4v7h7 M12 7v5l3 2'],
  chart: ['M4 3v18h17 M8 16v-5 M13 16V7 M18 16v-8'],
  search: ['M21 21l-5-5', 'M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0'],
  plus: ['M12 5v14 M5 12h14'],
  'chevron-down': ['m6 9 6 6 6-6'],
  'chevron-right': ['m9 5 7 7-7 7'],
  'arrow-right': ['M4 12h16m-6-6 6 6-6 6'],
  'arrow-left': ['M20 12H4m6-6-6 6 6 6'],
  'arrow-down': ['M12 4v16m-6-6 6 6 6-6'],
  'arrow-up': ['M12 20V4m-6 6 6-6 6 6'],
  'arrow-down-left': ['M18 6 6 18 M6 6v12h12'],
  'arrow-up-right': ['M6 18 18 6 M6 6h12v12'],
  logout: ['M9 4H4v16h5 M10 12h11m-5-5 5 5-5 5'],
  help: ['M9 9a3 3 0 1 1 4 3c-1 .5-1 1-1 2 M12 17h.01', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  info: ['M12 11v6 M12 7h.01', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  bell: ['M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4'],
  menu: ['M4 6h16 M4 12h16 M4 18h16'],
  close: ['m6 6 12 12 M6 18 18 6'],
  check: ['m5 12 4 4L19 6'],
  alert: ['m12 3 10 18H2z M12 9v5 M12 17h.01'],
  clock: ['M12 6v6l4 2', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  refresh: ['M20 7a9 9 0 0 0-15-2L2 8 M2 3v5h5 M4 17a9 9 0 0 0 15 2l3-3 M22 21v-5h-5'],
  eye: ['M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12', 'M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
  edit: ['m15 4 5 5 M4 16l12-12a3 3 0 0 1 4 4L8 20H4z'],
  shield: ['m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z', 'm8 12 3 3 5-6'],
  mail: ['M3 5h18v14H3z M3 6l9 7 9-7'],
  lock: ['M5 10h14v11H5z M8 10V6a4 4 0 0 1 8 0v4 M12 14v3'],
  calendar: ['M3 5h18v16H3z M3 10h18 M7 3v4 M17 3v4'],
  download: ['M12 3v12m-5-5 5 5 5-5 M4 16v5h16v-5'],
  user: ['M20 21v-2a8 8 0 0 0-16 0v2', 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0'],
  filter: ['M3 5h18l-7 8v6l-4 2v-8z'],
};
