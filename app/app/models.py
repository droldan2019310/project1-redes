from pydantic import BaseModel, Field
from typing import List, Optional

# ---------- ODOO ----------
class OdooInvoiceLine(BaseModel):
    name: str
    sku: Optional[str] = None
    quantity: int = Field(ge=1)
    price_unit: float = Field(ge=0)
    tax_amount: float = Field(default=0, ge=0)
    subtotal: Optional[float] = Field(default=None, ge=0)

class OdooPartner(BaseModel):
    name: str
    vat: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[dict] = None  # calle/ciudad/estado/pais

class OdooInvoice(BaseModel):
    invoice_ref: str
    partner: OdooPartner
    currency: str
    invoice_lines: List[OdooInvoiceLine]
    total_expected: float = Field(ge=0)
    meta: Optional[dict] = None

# ---------- ZOHO ----------
class ZohoLineItem(BaseModel):
    item_id: Optional[str] = None   # en Zoho suele ser un ID numerico/string ya existente
    name: str
    rate: float = Field(ge=0)
    quantity: int = Field(ge=1)
    tax_amount: float = Field(default=0, ge=0)

class ZohoSalesOrder(BaseModel):
    reference_number: str
    customer_name: str
    customer_tax_id: Optional[str] = None
    currency_code: str
    line_items: List[ZohoLineItem]
    notes: Optional[str] = None
    shipping_address: Optional[dict] = None
    org_id: Optional[str] = None
    custom_fields: Optional[list] = None
