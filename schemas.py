# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# --- Base Schemas (Used for Account Creation/Update) ---
class AccountBase(BaseModel):
    user_id: str = Field(..., max_length=50)
    account_type: str = Field(..., max_length=20) # e.g., 'checking', 'savings'
    currency: str = Field(..., max_length=3) # ISO 4217, e.g., 'USD'

# --- Account Creation Schema (Input) ---
class AccountCreate(AccountBase):
    # Inherits user_id, type, currency
    pass

# --- Account Response Schema (Output) ---
# This structure defines what the user sees after creating or retrieving an account
class AccountResponse(AccountBase):
    id: int
    status: str
    current_balance: float = 0.0 # Note: We'll keep it simple for display, but use Numeric in DB
    created_at: datetime
    updated_at: datetime

    class Config:
        # Allows ORM objects (SQLAlchemy models) to be converted directly to Pydantic models
        from_attributes = True

# schemas.py (Add these at the bottom)

# --- Transfer Input Schema ---
class TransferCreate(BaseModel):
    source_account_id: int
    destination_account_id: int
    amount: float = Field(..., gt=0) # Amount must be greater than zero
    currency: str = Field(..., max_length=3)
    description: Optional[str] = None

# --- Transaction Response Schema ---
class TransactionResponse(BaseModel):
    id: int
    type: str
    status: str
    amount: float
    currency: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True