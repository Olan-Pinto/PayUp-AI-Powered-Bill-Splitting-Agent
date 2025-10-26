from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# --- FIX: ensure asyncpg disables statement caching ---
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,  # some versions use this name
}

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True  # helps recover from Supabase idle timeouts
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()
