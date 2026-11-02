import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, forkJoin } from 'rxjs';
import { InventoryGateway, InventorySnapshot } from '../interface/inventory';
import { Product, ProductInput, Lot } from '../../products/interface/product';
import { Category, CategoryInput } from '../../categories/interface/category';
import { HospitalArea, Movement, MovementInput } from '../../movements/interface/movement';
import { environment } from '../../../environments/environment';

/** Adaptador HTTP activo cuando useMock=false; coincide con las rutas FastAPI. */
@Injectable({ providedIn: 'root' })
export class HttpInventory extends InventoryGateway {
  private readonly http = inject(HttpClient);
  private readonly url = environment.apiUrl;
  override load(): Promise<InventorySnapshot> {
    return firstValueFrom(
      forkJoin({
        products: this.http.get<Product[]>(`${this.url}/products`),
        categories: this.http.get<Category[]>(`${this.url}/categories`),
        lots: this.http.get<Lot[]>(`${this.url}/lots`),
        areas: this.http.get<HospitalArea[]>(`${this.url}/areas`),
        movements: this.http.get<Movement[]>(`${this.url}/movements`),
      }),
    );
  }
  override saveProduct(input: ProductInput, id?: string): Promise<Product> {
    return firstValueFrom(
      id
        ? this.http.put<Product>(`${this.url}/products/${encodeURIComponent(id)}`, input)
        : this.http.post<Product>(`${this.url}/products`, input),
    );
  }
  override async setProductActive(id: string, active: boolean): Promise<void> {
    await firstValueFrom(
      this.http.patch(`${this.url}/products/${encodeURIComponent(id)}/status`, { active }),
    );
  }
  override saveCategory(input: CategoryInput): Promise<Category> {
    return firstValueFrom(this.http.post<Category>(`${this.url}/categories`, input));
  }
  override registerMovement(input: MovementInput): Promise<Movement> {
    return firstValueFrom(this.http.post<Movement>(`${this.url}/movements`, input));
  }
}
