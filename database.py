from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine without statement caching
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "application_name": "bill_splitter",
            "jit": "off"
        },
        "command_timeout": 60,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)

sync_database_url = DATABASE_URL.replace('+asyncpg', '+psycopg2')
sync_engine = create_engine(sync_database_url, poolclass=NullPool)

engine.sync_engine = sync_engine

# Create session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False  
)
