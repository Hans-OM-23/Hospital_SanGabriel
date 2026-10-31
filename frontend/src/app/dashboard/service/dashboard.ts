import { inject, Injectable } from '@angular/core';
import { InventoryService } from '../../core/service/inventory.service';
import { PeriodSummary } from '../interface/period-summary';
import { offsetDate } from '../../core/service/date-utils';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  readonly inventory = inject(InventoryService);
  summarize(from: string, to: string): PeriodSummary {
    const movements = this.inventory.movements().filter((m) => m.date >= from && m.date <= to);
    const outputs = new Map<string, number>();
    for (const m of movements.filter((m) => m.type === 'exit'))
      outputs.set(m.productId, (outputs.get(m.productId) ?? 0) + m.quantity);
    const ranking = [...outputs]
      .map(([productId, quantity]) => ({
        productId,
        name: this.inventory.productName(productId),
        unit: this.inventory.products().find((p) => p.id === productId)?.unit ?? '',
        quantity,
        percent: 0,
      }))
      .sort((a, b) => b.quantity - a.quantity)
      .slice(0, 5);
    const max = ranking[0]?.quantity ?? 1;
    ranking.forEach((p) => (p.percent = Math.round((p.quantity / max) * 100)));
    const days =
      Math.floor(
        (new Date(`${to}T12:00:00`).getTime() - new Date(`${from}T12:00:00`).getTime()) / 86400000,
      ) + 1;
    const bucketDays = Math.max(1, Math.ceil(days / 7));
    const series: PeriodSummary['series'] = [];
    for (let i = 0; i < 7; i++) {
      const start = offsetDate(i * bucketDays, from);
      if (start > to) break;
      const end = offsetDate(bucketDays - 1, start);
      const bucket = movements.filter((m) => m.date >= start && m.date <= end);
      series.push({
        date: start,
        label: new Intl.DateTimeFormat('es-PE', {
          day: '2-digit',
          month: 'short',
          ...(days > 365 ? { year: '2-digit' as const } : {}),
        }).format(new Date(`${start}T12:00:00`)),
        entries: bucket.filter((m) => m.type === 'entry').length,
        exits: bucket.filter((m) => m.type === 'exit').length,
      });
    }
    return {
      movements: movements.length,
      entries: movements.filter((m) => m.type === 'entry').length,
      exits: movements.filter((m) => m.type === 'exit').length,
      ranking,
      series,
    };
  }
}
