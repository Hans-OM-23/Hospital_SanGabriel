import { inject, Injectable } from '@angular/core';
import { InventoryService } from '../../core/service/inventory.service';
import { MovementInput } from '../interface/movement';

@Injectable({ providedIn: 'root' })
export class MovementsService {
  readonly inventory = inject(InventoryService);
  readonly entryReasons = ['Compra', 'Donación', 'Devolución'];

  register(input: MovementInput) {
    return this.inventory.registerMovement(input);
  }
}
