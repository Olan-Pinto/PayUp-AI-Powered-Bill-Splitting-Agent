# from sqlalchemy import create_engine, text
# from dotenv import load_dotenv
# import os

# # Load .env
# load_dotenv()
# DATABASE_URL = os.getenv("DATABASE_URL")
# # Create SQLAlchemy engine
# engine = create_engine(DATABASE_URL)

# # Test connection
# with engine.connect() as conn:
#     result = conn.execute(text("SELECT NOW()"))
#     print("Connected to Supabase Postgres at:", result.scalar())

#     result = conn.execute(text("""
#         SELECT table_name 
#         FROM information_schema.tables
#         WHERE table_schema = 'public'
#         ORDER BY table_name;
#     """))
#     tables = [row[0] for row in result]
#     print("Tables in database:", tables)


import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test_async_connection():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT NOW()"))
        print("Connected to Supabase Postgres at:", result.scalar())

        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]
        print("Tables in database:", tables)

    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(test_async_connection())
