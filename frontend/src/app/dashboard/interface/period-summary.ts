export interface PeriodSummary {
  movements: number;
  entries: number;
  exits: number;
  ranking: { productId: string; name: string; unit: string; quantity: number; percent: number }[];
  series: { date: string; label: string; entries: number; exits: number }[];
}
