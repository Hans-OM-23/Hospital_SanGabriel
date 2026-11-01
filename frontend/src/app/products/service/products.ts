import { inject, Injectable } from '@angular/core';
import { InventoryService } from '../../core/service/inventory.service';
import { ProductInput } from '../interface/product';

@Injectable({ providedIn: 'root' })
export class ProductsService {
  readonly inventory = inject(InventoryService);
  readonly products = this.inventory.products;
  readonly categories = this.inventory.categories;
  stock(id: string) {
    return this.inventory.stock(id);
  }
  lots(id: string) {
    return this.inventory.productLots(id);
  }
  save(input: ProductInput, id?: string) {
    return this.inventory.saveProduct(input, id);
  }
  setActive(id: string, active: boolean) {
    return this.inventory.setProductActive(id, active);
  }
}
