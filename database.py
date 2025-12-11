# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Load the connection string from the .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the SQLAlchemy Engine
engine = create_engine(DATABASE_URL)

# Create a session local class for interacting with the DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your ORM models
Base = declarative_base()

# Dependency function to manage database session lifecycle
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()