import { inject, Injectable } from '@angular/core';
import { InventoryService } from '../../core/service/inventory.service';
import { CategoryInput } from '../interface/category';

@Injectable({ providedIn: 'root' })
export class CategoriesService {
  private readonly inventory = inject(InventoryService);
  readonly categories = this.inventory.categories;
  readonly products = this.inventory.products;
  save(input: CategoryInput) {
    return this.inventory.saveCategory(input);
  }
  productCount(id: string) {
    return this.products().filter((product) => product.categoryId === id).length;
  }
}
