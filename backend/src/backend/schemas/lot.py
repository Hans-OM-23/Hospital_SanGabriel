"""Schema de lotes.

El contrato no expone un alta independiente de lotes: el lote se crea o
actualiza como parte de una entrada válida (``POST /movements``). Por eso solo
se define el modelo de respuesta. La creación del lote se resolverá en el
servicio a partir de ``lotNumber`` y ``expirationDate`` del movimiento.
"""

from __future__ import annotations

from backend.schemas.common import ApiResponse, Identifier, ISODate


class LotResponse(ApiResponse):
    """Lote tal como lo espera la interfaz Angular."""

    id: Identifier
    product_id: Identifier
    number: str
    expiration_date: ISODate | None
    stock: int


__all__ = ["LotResponse"]
