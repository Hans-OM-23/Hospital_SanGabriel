import { Product, ProductInput, Lot } from '../../products/interface/product';
import { Category, CategoryInput } from '../../categories/interface/category';
import { HospitalArea, Movement, MovementInput } from '../../movements/interface/movement';

export interface InventorySnapshot {
  products: Product[];
  categories: Category[];
  lots: Lot[];
  areas: HospitalArea[];
  movements: Movement[];
}

/** The only boundary that changes when the FastAPI service becomes available. */
export abstract class InventoryGateway {
  abstract load(): Promise<InventorySnapshot>;
  abstract saveProduct(input: ProductInput, id?: string): Promise<Product>;
  abstract setProductActive(id: string, active: boolean): Promise<void>;
  abstract saveCategory(input: CategoryInput): Promise<Category>;
  abstract registerMovement(input: MovementInput): Promise<Movement>;
}
