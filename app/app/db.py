import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

MYSQL_URL = (
    f"mysql+pymysql://{os.environ['MYSQL_USER']}:{os.environ['MYSQL_PASSWORD']}"
    f"@{os.environ['MYSQL_HOST']}:{os.environ.get('MYSQL_PORT','3306')}/{os.environ['MYSQL_DB']}?charset=utf8mb4"
)

engine = create_engine(MYSQL_URL, pool_pre_ping=True, pool_size=5, max_overflow=10, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
