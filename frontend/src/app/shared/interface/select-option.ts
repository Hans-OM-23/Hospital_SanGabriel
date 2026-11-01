/** A selectable value supplied by the feature that owns the data. */
export interface SelectOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
}
