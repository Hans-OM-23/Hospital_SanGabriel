export interface Product {
  id: string;
  code: string;
  name: string;
  description: string;
  categoryId: string;
  unit: string;
  unitPrice: number;
  minStock: number;
  tracksExpiration: boolean;
  expirationDate: string | null;
  active: boolean;
}

export type ProductInput = Omit<Product, 'id' | 'active'>;

export interface Lot {
  id: string;
  productId: string;
  number: string;
  expirationDate: string | null;
  stock: number;
}
