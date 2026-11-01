import { Component, computed, HostListener, inject, OnInit, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { DatePipe } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map, startWith } from 'rxjs';
import { AuthService } from '../../../auth/service/auth';
import { InventoryService } from '../../../core/service/inventory.service';
import { DemoInventory } from '../../../core/service/demo-inventory';
import { Icon } from '../../../shared/components/icon/icon';
import { environment } from '../../../../environments/environment';

@Component({
  imports: [RouterLink, RouterLinkActive, RouterOutlet, DatePipe, Icon],
  selector: 'app-shell',
  styleUrl: './shell.scss',
  templateUrl: './shell.html',
})
export class Shell implements OnInit {
  readonly auth = inject(AuthService);
  readonly inventory = inject(InventoryService);
  private readonly router = inject(Router);
  private readonly demo = inject(DemoInventory);
  readonly menuOpen = signal(false);
  readonly compact = signal(window.matchMedia('(max-width: 860px)').matches);
  readonly helpOpen = signal(false);
  readonly confirmReset = signal(false);
  readonly demoMode = environment.useMock;
  readonly url = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );
  readonly pageName = computed(
    () =>
      this.navItems.find((n) => n.path !== '/' && this.url().startsWith(n.path))?.name ??
      'Vista general',
  );
  readonly navItems = [
    { path: '/', name: 'Vista general', icon: 'dashboard', exact: true },
    { path: '/productos', name: 'Productos', icon: 'package', exact: false },
    { path: '/categorias', name: 'Categorías', icon: 'layers', exact: false },
    { path: '/movimientos', name: 'Entradas y salidas', icon: 'arrows', exact: false },
    { path: '/historial', name: 'Historial', icon: 'history', exact: false },
    { path: '/consultas', name: 'Consultas e indicadores', icon: 'chart', exact: false },
  ];
  async ngOnInit() {
    await this.refresh();
  }
  @HostListener('window:resize') onResize() {
    this.compact.set(window.matchMedia('(max-width: 860px)').matches);
  }
  @HostListener('window:keydown.escape') closeMenu() {
    this.menuOpen.set(false);
  }
  async refresh() {
    try {
      await this.inventory.refresh();
    } catch {
      /* The shared error panel provides retry. */
    }
  }
  async reset() {
    await this.demo.reset();
    await this.refresh();
    this.confirmReset.set(false);
    this.helpOpen.set(false);
  }
  async logout() {
    this.auth.logout();
    await this.router.navigateByUrl('/login');
  }
}
