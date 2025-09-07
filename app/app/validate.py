# app/app/validate.py
from typing import Mapping, Sequence

class ValidationError(Exception): ...

def validate_items_present(items: Sequence[Mapping]):
    if not items:
        raise ValidationError("La orden no tiene items.")

def validate_basic_totals(order: Mapping, items: Sequence[Mapping], tolerance: float = 0.05):
    total_items = 0.0
    for it in items:
        qty = int(it.get("qty", 0))
        price = float(it.get("price", 0))
        tax = float(it.get("tax_amount", 0) or 0)
        total_items += qty * price + tax
    doc_total = float(order.get("total") or 0)
    if abs(total_items - doc_total) > tolerance:
        raise ValidationError(f"Total no cuadra: líneas={total_items:.2f} vs orden={doc_total:.2f}")

def validate_customer(order: Mapping):
    if not (order.get("name_shipping") and order.get("address_shipping")):
        raise ValidationError("Faltan datos del cliente/dirección.")
