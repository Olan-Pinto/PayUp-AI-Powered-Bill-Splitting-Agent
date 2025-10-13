from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT NOW()"))
    print("Connected to Supabase Postgres at:", result.scalar())