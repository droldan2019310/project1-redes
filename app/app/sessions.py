# app/app/sessions.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any

def create_session(db: Session, title: Optional[str] = None) -> int:
    sql = text("INSERT INTO mcp_sessions (title) VALUES (:title)")
    db.execute(sql, {"title": title})
    db.commit()
    # Recupera el id (MySQL: LAST_INSERT_ID)
    row = db.execute(text("SELECT LAST_INSERT_ID() AS id")).mappings().first()
    return int(row["id"])

def append_message(db: Session, session_id: int, role: str, content: Dict[str, Any]) -> None:
    sql = text("""
        INSERT INTO mcp_messages (session_id, role, content)
        VALUES (:sid, :role, CAST(:content AS JSON))
    """)
    db.execute(sql, {"sid": session_id, "role": role, "content": json_dumps(content)})
    db.commit()

def get_history(db: Session, session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    sql = text("""
        SELECT role, content, created_at
        FROM mcp_messages
        WHERE session_id = :sid
        ORDER BY id ASC
        LIMIT :lim
    """)
    rows = db.execute(sql, {"sid": session_id, "lim": limit}).mappings().all()
    return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"].isoformat()} for r in rows]

def clear_session(db: Session, session_id: int) -> None:
    db.execute(text("DELETE FROM mcp_messages WHERE session_id = :sid"), {"sid": session_id})
    db.commit()

# Util pequeño para serializar con decimales/fechas si vienen:
import json, datetime, decimal
def json_dumps(obj):
    def _default(o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return str(o)
    return json.dumps(obj, default=_default, ensure_ascii=False)
