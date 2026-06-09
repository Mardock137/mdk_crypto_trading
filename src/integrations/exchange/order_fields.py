"""Nomi dei campi nei dizionari ordine restituiti da Binance.

Fonte unica di verita': se Binance rinomina un campo, si aggiorna solo qui.
"""
from __future__ import annotations

# Chiavi dei dizionari ordine
ORDER_TYPE = "type"
ORDER_LIST_ID = "orderListId"
STOP_PRICE = "stopPrice"
ORIG_QTY = "origQty"
ORDER_PRICE = "price"
AGE_HOURS = "age_hours"
ORDER_ID = "orderId"
CLIENT_ORDER_ID = "clientOrderId"

# Valori del campo ORDER_TYPE
TYPE_LIMIT_MAKER = "LIMIT_MAKER"
TYPE_STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"

# Chiavi candidate per identificare un ordine (fallback in ordine di priorita')
ORDER_ID_LOOKUP_KEYS = (ORDER_ID, "order_id", "id")
