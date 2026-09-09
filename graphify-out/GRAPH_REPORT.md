# Graph Report - personal-budgeting  (2026-09-09)

## Corpus Check
- Corpus is ~25,001 words - fits in a single context window. You may not need a graph.

## Summary
- 647 nodes · 1551 edges · 51 communities (21 shown, 10 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 228 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Transaction Schemas & Payloads
- Account & Transaction Core Models
- Transaction Query Services
- Transaction Reporting Tests
- Envelope Lifecycle & Transfers
- Category Repository & Queries
- Category Schemas & Requests
- Database Models & Relationships
- Category Service Tests
- Envelope Service Operations
- Envelope Update Tests
- Account Service Tests
- Envelope Base Schemas & Tests
- Financed Transaction Tests
- Envelope Allocation Tests
- Account Lifecycle Tests
- Database Session & Engine
- Account Schemas & Requests
- Test Configuration & Fixtures
- Account Balance Adjustment Tests
- Envelope Service Integration Tests
- Envelope Deactivation Tests
- Envelope Deletion Tests
- Interest Adjustment Tests
- Debt Payment Tests
- Alembic Migration Environment
- Envelope Activation Tests
- Model Validator Utilities
- Docker Compose Database Services
- Graphify Rules & Workflows
- Budget App Package Root

## God Nodes (most connected - your core abstractions)
1. `EnvelopeBase` - 78 edges
2. `TransactionRequest` - 60 edges
3. `AccountBase` - 37 edges
4. `get_or_create_account()` - 34 edges
5. `EnvelopeSplitRequest` - 32 edges
6. `TransactionUpdateRequest` - 27 edges
7. `AccountCreate` - 25 edges
8. `get_account_by_name()` - 24 edges
9. `Envelope` - 23 edges
10. `Transaction` - 23 edges

## Surprising Connections (you probably didn't know these)
- `get_or_create_account()` --calls--> `AccountBase`  [INFERRED]
  tests/test_transaction_service.py → src/budget_app/schemas/account.py
- `transfer_setup()` --calls--> `EnvelopeBase`  [INFERRED]
  tests/test_envelope_service.py → src/budget_app/schemas/envelope.py
- `get_or_create_envelope()` --calls--> `EnvelopeBase`  [INFERRED]
  tests/test_transaction_service.py → src/budget_app/schemas/envelope.py
- `setup_test_database()` --calls--> `Config`  [INFERRED]
  tests/conftest.py → src/budget_app/schemas/envelope.py
- `transfer_setup()` --calls--> `EnvelopeSplitRequest`  [INFERRED]
  tests/test_envelope_service.py → src/budget_app/schemas/envelope_split.py

## Import Cycles
- 3-file cycle: `src/budget_app/repositories/__init__.py -> src/budget_app/repositories/ledger_repo.py -> src/budget_app/repositories/envelope_split_repo.py -> src/budget_app/repositories/__init__.py`
- 3-file cycle: `src/budget_app/models/__init__.py -> src/budget_app/models/account.py -> src/budget_app/repositories/account_repo.py -> src/budget_app/models/__init__.py`
- 3-file cycle: `src/budget_app/models/envelope.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/envelope.py`
- 3-file cycle: `src/budget_app/models/transaction.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/transaction.py`
- 4-file cycle: `src/budget_app/models/envelope.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/category.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/envelope.py`
- 4-file cycle: `src/budget_app/models/transaction.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/category.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/transaction.py`
- 4-file cycle: `src/budget_app/models/envelope.py -> src/budget_app/models/envelope_split.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/envelope.py`
- 5-file cycle: `src/budget_app/models/envelope.py -> src/budget_app/models/envelope_split.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/category.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/envelope.py`
- 5-file cycle: `src/budget_app/models/envelope.py -> src/budget_app/models/envelope_split.py -> src/budget_app/models/transaction.py -> src/budget_app/schemas/__init__.py -> src/budget_app/schemas/envelope.py -> src/budget_app/models/envelope.py`

## Communities (51 total, 10 thin omitted)

### Community 0 - "Transaction Schemas & Payloads"
Cohesion: 0.06
Nodes (21): EnvelopeSplitRequest, Request payload for specifying an envelope split with an envelope name., FinancedTransaction, Payload for modifying an existing transaction. All fields are optional; only…, Payload for creating a regular transaction with envelope splits. Attributes:…, Payload for creating a financed installment transaction. Attributes: term:…, TransactionRequest, TransactionUpdateRequest (+13 more)

### Community 1 - "Account & Transaction Core Models"
Cohesion: 0.07
Nodes (67): setter, Account, Decimal, Database table representing a financial account (Cash, Credit Card, or Loan).…, Derived balance accessor computing from transactions or returning cached/in-…, Database table representing a master transaction. Encapsulates merchant, dates,…, Backward-compatible alias for splits., Transaction (+59 more)

### Community 2 - "Transaction Query Services"
Cohesion: 0.06
Nodes (39): get_transaction_by_id(), get_transactions(), date, Session, Fetches a single Transaction by its primary key ID. Args: session: Active…, Queries transactions from the database based on the provided filters. Args:…, EnvelopeSplitBase, EnvelopeSplitResponse (+31 more)

### Community 3 - "Transaction Reporting Tests"
Cohesion: 0.06
Nodes (16): Default fetch excludes transfers and limits dates to 3rd through 28th., Split cash transaction ($20 Fun + $20 Groceries) should report total $40., CC tx ($30 + $70) reports total $100, filtering out balancing entry., Financed tx (+1200, -1200) reports positive financed total $1200., Filtering by envelope returns all transactions touching that envelope., Filtering by CC Payment envelope excludes regular CC expenses., Filtering by account returns only transactions using that payment method., Custom date_from and date_to captures transactions including out-of-range. (+8 more)

### Community 4 - "Envelope Lifecycle & Transfers"
Cohesion: 0.12
Nodes (32): Personal Budgeting Application. A zero-based envelope budgeting system built…, get_envelope_by_name(), Fetches an envelope by its unique name. Args: session: Active SQLModel database…, EnvelopeTransfer, Response object returned after executing a transfer between two envelopes.…, activate_envelope(), add_to_cash(), assign_to_envelope() (+24 more)

### Community 5 - "Category Repository & Queries"
Cohesion: 0.12
Nodes (29): EnvelopeCategory, Database table representing an envelope category group. Groups budgeting…, count_envelopes_in_category(), create_category(), delete_category(), get_categories(), get_category_by_id(), get_category_by_name() (+21 more)

### Community 6 - "Category Schemas & Requests"
Cohesion: 0.13
Nodes (22): Envelope category database table model., InterestChargeRequest, Request payload for logging an interest charge on a debt account., EnvelopeCategoryBase, EnvelopeCategoryCreate, EnvelopeCategoryResponse, EnvelopeCategoryWithEnvelopes, SQLModel (+14 more)

### Community 7 - "Database Models & Relationships"
Cohesion: 0.15
Nodes (15): Envelope database table model., EnvelopeSplit, EnvelopeSplit database table model., Database table representing an individual envelope split allocation. Each…, Database ORM models package. Defines SQLModel database entities: - Account:…, Backward-compatible aliases for envelope split models., Transaction database table model., Envelope repository for database operations on the Envelope entity. (+7 more)

### Community 8 - "Category Service Tests"
Cohesion: 0.09
Nodes (7): EnvelopeCategoryUpdate, Payload for updating an envelope category., Unit tests for category_service., TestCreateCategory, TestDeleteCategory, TestGetCategory, TestUpdateCategory

### Community 9 - "Envelope Service Operations"
Cohesion: 0.13
Nodes (19): Envelope, Database table representing a budgeting category envelope. Holds allocated…, Backward-compatible alias for splits., create_envelope(), delete_envelope(), get_balance_for_envelope(), get_envelope_by_id(), get_envelopes() (+11 more)

### Community 10 - "Envelope Update Tests"
Cohesion: 0.19
Nodes (4): EnvelopeUpdate, SQLModel, Payload for updating an envelope's name, note, or category., TestUpdateEnvelopeInfo

### Community 11 - "Account Service Tests"
Cohesion: 0.18
Nodes (4): AccountCreate, Schema for creating a new account with an optional starting balance., TestCreateAccount, TestStartingBalanceAndDerivedBalance

### Community 12 - "Envelope Base Schemas & Tests"
Cohesion: 0.19
Nodes (5): EnvelopeBase, Base schema defining properties for a budgeting envelope category., TestGetCategoriesWithEnvelopes, TestCreateEnvelope, TestGetEnvelopesAndBalances

### Community 13 - "Financed Transaction Tests"
Cohesion: 0.23
Nodes (3): FinancedTransactionUpdateRequest, Payload for modifying an existing financed installment transaction. All fields…, TestUpdateFinancedTransaction

### Community 14 - "Envelope Allocation Tests"
Cohesion: 0.15
Nodes (3): parametrize, TestAddToCash, TestTransferBetweenEnvelopes

### Community 15 - "Account Lifecycle Tests"
Cohesion: 0.22
Nodes (5): AccountBase, AccountUpdate, Base schema for financial accounts. Contains foundational fields applicable…, Schema for updating account details., TestAccountLifecycleAndFiltering

### Community 16 - "Database Session & Engine"
Cohesion: 0.21
Nodes (9): get_session(), Session, Database engine configuration and session provider. Loads database connection…, Yields a database session context and automatically closes it when finished.…, init_db(), Session, Database initialization and seeding script. Creates essential system records if…, Initializes the database with required default categories, envelopes, and… (+1 more)

### Community 17 - "Account Schemas & Requests"
Cohesion: 0.24
Nodes (10): AccountType, BalanceAdjustmentRequest, InterestEarnedRequest, Enum, SQLModel, str, Account data schemas and enumerations., Request payload for logging interest earned on a cash account. (+2 more)

### Community 18 - "Test Configuration & Fixtures"
Cohesion: 0.24
Nodes (10): Config, db_engine(), ensure_test_database_exists(), fixture, Connect to default PostgreSQL server to ensure the test database specified in…, Session-wide setup: 1. Ensures the test database exists in the PostgreSQL…, create a single SQLModel engine for the test session, Main fixture Creates an outer SQL Transaction for every test function. All… (+2 more)

### Community 20 - "Envelope Service Integration Tests"
Cohesion: 0.18
Nodes (4): fixture, TestEnvelopeCategoryIntegration, TestGetSingleEnvelopeWithBalance, transfer_setup()

### Community 25 - "Alembic Migration Environment"
Cohesion: 0.33
Nodes (6): Prevents linter errors by rendering SQLModel AutoString as sa.String()., Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, render_item(), run_migrations_offline(), run_migrations_online()

## Knowledge Gaps
- **5 isolated node(s):** `budget_app`, `PostgreSQL Database Service`, `PostgreSQL Data Volume`, `Graphify Agent Consultation Rules`, `Graphify Agent Workflow`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 252 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EnvelopeBase` connect `Envelope Base Schemas & Tests` to `Transaction Schemas & Payloads`, `Account & Transaction Core Models`, `Transaction Query Services`, `Envelope Lifecycle & Transfers`, `Category Schemas & Requests`, `Database Models & Relationships`, `Category Service Tests`, `Envelope Service Operations`, `Envelope Update Tests`, `Envelope Allocation Tests`, `Account Lifecycle Tests`, `Database Session & Engine`, `Account Balance Adjustment Tests`, `Envelope Service Integration Tests`, `Envelope Deactivation Tests`, `Envelope Deletion Tests`, `Envelope Activation Tests`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `TestGetTransactions` connect `Transaction Reporting Tests` to `Transaction Schemas & Payloads`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `TransactionRequest` connect `Transaction Schemas & Payloads` to `Account & Transaction Core Models`, `Transaction Query Services`, `Envelope Lifecycle & Transfers`, `Category Schemas & Requests`, `Database Models & Relationships`, `Financed Transaction Tests`, `Account Lifecycle Tests`, `Envelope Service Integration Tests`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 54 inferred relationships involving `EnvelopeBase` (e.g. with `.test_delete_account_with_expense_transaction_raises_error()` and `.test_adjust_cash_balance_decrease_with_envelope()`) actually correct?**
  _`EnvelopeBase` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `TransactionRequest` (e.g. with `EnvelopeSplitRequest` and `.test_delete_account_with_expense_transaction_raises_error()`) actually correct?**
  _`TransactionRequest` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `AccountBase` (e.g. with `.test_activate_account()` and `.test_delete_account_no_transactions_success()`) actually correct?**
  _`AccountBase` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `EnvelopeSplitRequest` (e.g. with `TransactionRequest` and `TransactionUpdateRequest`) actually correct?**
  _`EnvelopeSplitRequest` has 9 INFERRED edges - model-reasoned connections that need verification._