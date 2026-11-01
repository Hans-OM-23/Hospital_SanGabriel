export type MovementType = 'entry' | 'exit';
export interface HospitalArea {
  id: string;
  name: string;
}
export interface MovementInput {
  type: MovementType;
  productId: string;
  quantity: number;
  date: string;
  reason: string;
  lotId?: string;
  lotNumber?: string;
  expirationDate?: string | null;
  areaId?: string | null;
}
export interface Movement {
  id: string;
  type: MovementType;
  productId: string;
  quantity: number;
  date: string;
  reason: string;
  stockBefore: number;
  stockAfter: number;
  lotId: string;
  lotNumber: string;
  expirationDate: string | null;
  areaId: string | null;
}
