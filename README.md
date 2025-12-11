# Financial-Ledger-API-with-Double-Entry-Bookkeeping-23MH1A05M4
# Financial API:
This is a robust, production-ready Financial Ledger API built using FastAPI and SQLAlchemy. It implements core banking principles, including Double-Entry Bookkeeping and strict adherence to ACID properties, to ensure transactional integrity and prevent common issues like race conditions and overdrafts.
# 🚀 Project Setup and Run Instructions
A Docker-based setup is highly recommended for quickly launching the PostgreSQL database and the application service together.

**Prerequisites**
- Docker and Docker Compose
- (Optional: Python 3.11+ for local setup)
  
**Option 1: Docker Compose (Recommended)**
1. Create .env file: Create a file named .env in the root directory to store database credentials.
```
# Example .env content
POSTGRES_USER=app_user
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=financial_ledger_db
DATABASE_URL=postgresql+psycopg2://app_user:strong_password@db:5432/financial_ledger_db
```
2. Run Services: Build and start the services (FastAPI and PostgreSQL):
```
docker-compose up --build
```
3. Access API: The application will be running at: http://localhost:8000
- Interactive Docs (Swagger UI): http://localhost:8000/docs
**Option 2: Local Setup**
1. Install Dependencies:
```
pip install -r requirements.txt
```
2. Start PostgreSQL:
- Ensure a PostgreSQL instance is running and accessible using the `DATABASE_URL` from your `.env` file.
3. Create Database Tables: Run the models file once to initialize the schema:
```
python models.py
```
4. Start Server:
```
uvicorn main:app --reload
```
# ⚙️ Design Decisions and Architecture
The application is built around three core database tables (`Account`, `Transaction`, `LedgerEntry`) that collectively enforce financial integrity.

**1. Implementation of Double-Entry Bookkeeping:**
- The Ledger is the Source of Truth: The Account table stores only metadata (`ID`, `user_id`, `currency`). The financial state is managed by the immutable LedgerEntry table.
  
 **Transaction Immutability:** Every financial event (transfer, deposit, withdrawal) generates a parent Transaction record and one or two associated LedgerEntry records. Once written, these records are never modified, creating a permanent, auditable log.
 
 **Balance:** A transfer between two accounts always results in one Debit entry (money leaving the source) and one Credit entry (money entering the destination). This ensures the sum of all entries in the ledger is always zero, maintaining the fundamental accounting equation.

**2. Strategy for Ensuring ACID Properties:**
- ACID (Atomicity, Consistency, Isolation, Durability) is guaranteed for all state-changing financial operations (/transfers/, /deposits/, /withdrawals/).
  
**Atomicity & Durability:**
- All steps of a transaction (balance check, creating Transaction, creating LedgerEntry records) are enclosed within a single database transaction block using SQLAlchemy's with db.begin():.
- If any step fails (e.g., an overdraft check or a database error), the entire transaction is automatically rolled back, ensuring no partial writes occur (Atomicity). Once the block completes, changes are permanently written to disk (Durability).
  
**Rationale for Transaction Isolation Level (Concurrency Control):** We achieve a high level of isolation using SELECT FOR UPDATE within the transaction block. Before checking the source account balance, we lock the relevant Account rows.
  
**Goal:** This prevents race conditions where two simultaneous withdrawal attempts might both check the old balance before either one commits its ledger entries. By locking the row, the second attempt is forced to wait until the first completes, ensuring the second check sees the new, accurate balance.
  
**3. Balance Calculation and Negative Balance Prevention:**

**Balance Calculation:** The current balance is not a stored column. It is computed dynamically using the helper function calculate_account_balance.

- It retrieves all LedgerEntry records for a given account_id.

- It sums the amount column, adding entries with entry_type='credit' and subtracting entries with entry_type='debit'.

**Negative Balance Prevention (Consistency):**
- Immediately before creating any debit entry (/transfers/, /withdrawals/), the system calculates the current_source_balance.
- An explicit check is performed: if current_source_balance < transfer_amount:.
- If the check fails, an HTTPException(status_code=403, detail="Insufficient funds in source account.") is raised. This automatically triggers the transaction rollback, preventing the invalid ledger entry from ever being written and enforcing the business rule (Consistency).

# 🖼️ Supporting Artifacts
**1. Database Schema Diagram (ERD)**

![WhatsApp Image 2025-12-10 at 15 00 09_dc6388e2](https://github.com/user-attachments/assets/a236cf8c-8193-404c-93be-392c8316d531)
