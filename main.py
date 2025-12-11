# ==========================================================
# FINAL AND COMPLETE main.py (Includes ALL Endpoints)
# ==========================================================
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal
import sys

# Direct imports (assuming database.py, models.py, schemas.py are in the same directory)
from database import get_db, engine 
import models, schemas 


# Create the FastAPI app instance
app = FastAPI(title="Financial Ledger API")


# ==========================================================
# HELPER FUNCTIONS 
# ==========================================================

def calculate_account_balance(db: Session, account_id: int) -> Decimal:
    """Calculates the current balance by summing all ledger entries."""
    
    entries = db.query(models.LedgerEntry).filter(
        models.LedgerEntry.account_id == account_id
    ).all()
    
    balance = Decimal(0)
    
    for entry in entries:
        if entry.entry_type == 'credit':
            balance += entry.amount
        elif entry.entry_type == 'debit':
            balance -= entry.amount
    
    return balance


def create_new_account_in_db(db: Session, account: schemas.AccountCreate):
    """Handles database insertion and unique constraint check."""
    existing_account = db.query(models.Account).filter(
        models.Account.user_id == account.user_id,
        models.Account.currency == account.currency
    ).first()

    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account for user_id '{account.user_id}' with currency '{account.currency}' already exists."
        )

    db_account = models.Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return db_account


# ==========================================================
# ACCOUNT ENDPOINTS (Create, Read)
# ==========================================================

@app.post("/accounts/", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    """Creates a new financial account for a user."""
    new_account = create_new_account_in_db(db, account)
    setattr(new_account, 'current_balance', 0.0) 
    return new_account

@app.get("/accounts/{account_id}", response_model=schemas.AccountResponse)
def read_account(account_id: int, db: Session = Depends(get_db)):
    """Retrieves account details and calculates the current balance."""
    
    db_account = db.query(models.Account).filter(
        models.Account.id == account_id
    ).first()
    
    if db_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with ID {account_id} not found."
        )
    
    current_balance = calculate_account_balance(db, account_id)
    
    setattr(db_account, 'current_balance', float(current_balance)) 
    
    return db_account


# ==========================================================
# TRANSACTION ENDPOINTS (Transfer, Deposit, Withdrawal)
# ==========================================================

@app.post("/transfers/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(transfer: schemas.TransferCreate, db: Session = Depends(get_db)):
    """Executes a double-entry transfer between two accounts with concurrency control."""
    
    source_id = transfer.source_account_id
    dest_id = transfer.destination_account_id
    transfer_amount = Decimal(str(transfer.amount))

    try:
        with db.begin():
            # 1. Lock Accounts (SELECT FOR UPDATE)
            source_account = db.query(models.Account).filter(
                models.Account.id == source_id
            ).with_for_update().first()

            dest_account = db.query(models.Account).filter(
                models.Account.id == dest_id
            ).with_for_update().first()

            if not source_account or not dest_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source or Destination account not found.")

            if source_account.currency != transfer.currency or dest_account.currency != transfer.currency:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Currency mismatch.")

            # 2. Check Balance Integrity (Prevent Overdraft)
            current_source_balance = calculate_account_balance(db, source_id)
            if current_source_balance < transfer_amount:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient funds in source account.")

            # 3. Create Parent Transaction Record
            new_transaction = models.Transaction(
                type="transfer",
                status="completed",
                amount=transfer_amount,
                currency=transfer.currency,
                description=transfer.description
            )
            db.add(new_transaction)
            db.flush()
            # 4. Create Ledger Entries (Debit and Credit)
            debit_entry = models.LedgerEntry(
                transaction_id=new_transaction.id,
                account_id=source_id,
                entry_type="debit",
                amount=transfer_amount
            )
            credit_entry = models.LedgerEntry(
                transaction_id=new_transaction.id,
                account_id=dest_id,
                entry_type="credit",
                amount=transfer_amount
            )
            
            db.add_all([debit_entry, credit_entry])

            db.refresh(new_transaction)
            setattr(new_transaction, 'amount', float(new_transaction.amount)) 
            
            return new_transaction

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback() 
        print(f"Transfer failed unexpectedly: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during the transfer.")


@app.post("/deposits/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_deposit(deposit: schemas.TransferCreate, db: Session = Depends(get_db)):
    """Simulates a deposit into an account."""
    
    # Note: We reuse TransferCreate schema for simplicity, using destination_account_id
    dest_id = deposit.destination_account_id
    deposit_amount = Decimal(str(deposit.amount))

    try:
        with db.begin():
            # 1. Lock Destination Account
            dest_account = db.query(models.Account).filter(
                models.Account.id == dest_id
            ).with_for_update().first()

            if not dest_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination account not found.")

            # 2. Create Parent Transaction
            new_transaction = models.Transaction(
                type="deposit",
                status="completed",
                amount=deposit_amount,
                currency=deposit.currency,
                description=deposit.description
            )
            db.add(new_transaction)
            db.flush()
            # 3. Create Ledger Entry (Credit Only)
            credit_entry = models.LedgerEntry(
                transaction_id=new_transaction.id,
                account_id=dest_id,
                entry_type="credit",
                amount=deposit_amount
            )
            db.add(credit_entry)
            
            db.refresh(new_transaction)
            setattr(new_transaction, 'amount', float(new_transaction.amount)) 
            
            return new_transaction

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback() 
        print(f"Deposit failed unexpectedly: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@app.post("/withdrawals/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_withdrawal(withdrawal: schemas.TransferCreate, db: Session = Depends(get_db)):
    """Simulates a withdrawal from an account."""
    
    # Note: We reuse TransferCreate schema for simplicity, using source_account_id
    source_id = withdrawal.source_account_id
    withdrawal_amount = Decimal(str(withdrawal.amount))

    try:
        with db.begin():
            # 1. Lock Source Account
            source_account = db.query(models.Account).filter(
                models.Account.id == source_id
            ).with_for_update().first()

            if not source_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source account not found.")
            
            # 2. Check Balance Integrity
            current_source_balance = calculate_account_balance(db, source_id)
            if current_source_balance < withdrawal_amount:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient funds for withdrawal.")

            # 3. Create Parent Transaction
            new_transaction = models.Transaction(
                type="withdrawal",
                status="completed",
                amount=withdrawal_amount,
                currency=withdrawal.currency,
                description=withdrawal.description
            )
            db.add(new_transaction)
            db.flush()
            # 4. Create Ledger Entry (Debit Only)
            debit_entry = models.LedgerEntry(
                transaction_id=new_transaction.id,
                account_id=source_id,
                entry_type="debit",
                amount=withdrawal_amount
            )
            db.add(debit_entry)
            
            db.refresh(new_transaction)
            setattr(new_transaction, 'amount', float(new_transaction.amount)) 
            
            return new_transaction

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback() 
        print(f"Withdrawal failed unexpectedly: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")