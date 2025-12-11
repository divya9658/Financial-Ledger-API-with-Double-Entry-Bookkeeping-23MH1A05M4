# models.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
# Note the leading dot for relative import: .database
from database import Base, engine 

# --- Utility Function ---
# Call this once to create all tables in the database
def create_all_tables(engine):
    Base.metadata.create_all(bind=engine)

# ----------------------------------------------------
# 1. Account Model
# ----------------------------------------------------
class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    account_type = Column(String(20), nullable=False)
    currency = Column(String(3), nullable=False) # ISO 4217 code, e.g., USD
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        UniqueConstraint(user_id, currency, name="uq_user_currency"),
        CheckConstraint('LENGTH(currency) = 3', name='currency_length_check'),
    )

    ledger_entries = relationship("LedgerEntry", back_populates="account")

# ----------------------------------------------------
# 2. Transaction Model (Parent operation)
# ----------------------------------------------------
class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False) 
    status = Column(String(20), default="pending", nullable=False) 
    amount = Column(Numeric(19, 4), nullable=False)
    currency = Column(String(3), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    ledger_entries = relationship("LedgerEntry", back_populates="transaction")


# ----------------------------------------------------
# 3. Ledger_Entry Model (The Immutable Financial Record)
# ----------------------------------------------------
class LedgerEntry(Base):
    __tablename__ = "ledger_entry"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transaction.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False, index=True)
    
    entry_type = Column(String(10), nullable=False) # 'debit' or 'credit'
    
    amount = Column(Numeric(19, 4), nullable=False)
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        CheckConstraint('amount > 0', name='positive_ledger_amount'),
    )

    transaction = relationship("Transaction", back_populates="ledger_entries")
    account = relationship("Account", back_populates="ledger_entries")

# models.py (at the very bottom of the file)
if __name__ == "__main__":
    print("Attempting to create database tables...")
    # Since we are running models.py directly here, we need to change the import.
    # TEMPORARY FIX FOR DIRECT EXECUTION (we will undo this later)
    from database import engine 

    # Call the function to create tables
    create_all_tables(engine)
    print("Database tables created successfully!")