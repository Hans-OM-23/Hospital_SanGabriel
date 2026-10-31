import { Component, input } from '@angular/core';

@Component({
  imports: [],
  selector: 'app-field-errors',
  styleUrl: './field-errors.scss',
  templateUrl: './field-errors.html',
})
export class FieldErrors {
  readonly field = input.required<{
    touched(): boolean;
    invalid(): boolean;
    errors(): readonly { message?: string }[];
  }>();
}
