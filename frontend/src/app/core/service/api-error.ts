import { HttpErrorResponse } from '@angular/common/http';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly field: string | null = null,
  ) {
    super(message);
  }
}

export function explainError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof HttpErrorResponse) {
    const detail = error.error?.detail;
    if (Array.isArray(detail)) {
      return new ApiError(
        detail.map((item) => `${item.loc?.at(-1) ?? 'Dato'}: ${item.msg}`).join('. '),
        detail[0]?.loc?.at(-1) ?? null,
      );
    }
    if (typeof detail === 'object' && detail)
      return new ApiError(
        detail.message ?? 'No se pudo completar la operación.',
        detail.field ?? null,
      );
    if (typeof detail === 'string') return new ApiError(detail);
    return new ApiError(
      error.status === 0
        ? 'No se pudo contactar al servicio. Intenta actualizar nuevamente.'
        : 'El servicio no pudo completar la operación. Inténtalo nuevamente.',
    );
  }
  return error instanceof Error
    ? new ApiError(error.message)
    : new ApiError('No se pudo completar la operación.');
}
