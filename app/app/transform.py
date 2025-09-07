# app/app/transform.py
from typing import Mapping, Sequence

def build_odoo_invoice(order: Mapping, items: Sequence[Mapping]) -> dict:
    """Payload genérico para crear factura en Odoo (ajusta a tu endpoint/SDK real)."""
    currency = order.get("currency") or order.get("region_shipping") or "GTQ"
    lines = []
    for it in items:
        qty = int(it.get("qty", 0))
        price = float(it.get("price", 0))
        tax = float(it.get("tax_amount", 0) or 0)
        lines.append({
            "name": it.get("name"),
            "sku": it.get("sku"),
            "quantity": qty,
            "price_unit": price,
            "tax_amount": tax,
            "subtotal": round(qty * price, 2),
        })

    payload = {
        "invoice_ref": str(order["id"]),
        "partner": {
            "name": order.get("name_shipping") or "",
            "vat": order.get("NIT") or "",
            "email": order.get("email_shipping") or "",
            "phone": order.get("phone_shipping") or "",
            "address": {
                "street": order.get("address_shipping") or "",
                "city": order.get("city_shipping") or "",
                "state": order.get("region_shipping") or "",
                "country": "GT",  # ajusta si tienes país
            }
        },
        "currency": currency,
        "invoice_lines": lines,
        "total_expected": float(order.get("total") or 0),
        "meta": {
            "source": "MCP",
            "shipping_method_id": order.get("shipping_method_id"),
        },
    }
    return payload

def build_zoho_sales_order(order: Mapping, items: Sequence[Mapping], org_id: str) -> dict:
    """Payload genérico para Zoho Books/Inventory Sales Order."""
    currency = order.get("currency") or "GTQ"
    lines = []
    for it in items:
        qty = int(it.get("qty", 0))
        price = float(it.get("price", 0))
        tax = float(it.get("tax_amount", 0) or 0)
        lines.append({
            "item_id": it.get("sku"),                # ojo: en Zoho suele ser ID del ítem, luego mapea
            "name": it.get("name"),
            "rate": price,
            "quantity": qty,
            "tax_amount": tax
        })

    payload = {
        "reference_number": str(order["id"]),
        "customer_name": order.get("name_shipping") or "",
        "customer_tax_id": order.get("NIT") or "",
        "currency_code": currency,
        "line_items": lines,
        "notes": order.get("comment") or "",
        "shipping_address": {
            "address": order.get("address_shipping") or "",
            "city": order.get("city_shipping") or "",
            "state": order.get("region_shipping") or "",
            "country": "Guatemala"  # ajusta
        },
        "org_id": org_id,
        "custom_fields": [
            {"label": "phone", "value": order.get("phone_shipping") or ""},
            {"label": "email", "value": order.get("email_shipping") or ""},
        ],
    }
    return payload
