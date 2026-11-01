export interface Category {
  id: string;
  name: string;
  description: string;
  active: boolean;
}
export type CategoryInput = Pick<Category, 'name' | 'description'>;
