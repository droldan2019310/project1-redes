from sqlalchemy import text
from sqlalchemy.orm import Session

def fetch_order_by_id(db: Session, order_id: int):
    sql = text("""
        SELECT id, businessid, name_shipping, NIT, address_shipping, statusid, date_request,
               phone_shipping, email_shipping, city_shipping, region_shipping, weight,
               payment_method, sourceid, total, voided, metadata, delivery_time, created_by, updated_by,
               instagram_user, facebook_name, tiktok_user, guia, no_factura, guia_link, id_source,
               source_guia_id, source_name_id, status_shipping_id, status_payment_id, comment,
               shipping_method_id, created_at, updated_at
        FROM orders
        WHERE id = :id
        LIMIT 1
    """)
    return db.execute(sql, {"id": order_id}).mappings().first()

def fetch_order_items(db: Session, order_id: int):
    """
    Si aún no creaste la tabla order_items, devolverá lista vacía sin romper.
    Espera columnas: orderid, sku, name, qty, price, tax_amount (ajusta a tu esquema real)
    """
    try:
        sql = text("""
            SELECT orderid, sku, name, qty, price, tax_amount
            FROM order_items
            WHERE orderid = :id
        """)
        return list(db.execute(sql, {"id": order_id}).mappings())
    except Exception:
        return []

def fetch_order_tags(db: Session, order_id: int):
    """
    Opcional: si tienes tags por entidad_id_tbl=7
    """
    try:
        sql = text("""
            SELECT t.name AS tag_name
            FROM tag_entities te
            JOIN tags t ON t.id = te.tag_id
            WHERE te.entity_id_tbl = 7 AND te.entity_id = :id
        """)
        return [row["tag_name"] for row in db.execute(sql, {"id": order_id}).mappings()]
    except Exception:
        return []
