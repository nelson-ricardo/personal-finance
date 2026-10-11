# Graph Report - personal-budgeting  (2026-10-11)

## Corpus Check
- Corpus is ~38,143 words - fits in a single context window. You may not need a graph.

## Summary
- 984 nodes · 2343 edges · 73 communities (34 shown, 39 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 245 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Category Domain Tests
- Account Management & Balances
- Financed Transactions & Loans
- Financed Transactions & Loans
- Account Management & Balances
- Account Domain Tests
- Account Management & Balances
- Account Management & Balances
- Database Schema Migrations
- Account Domain Tests
- Financed Transactions & Loans
- Financed Transactions & Loans
- Category Domain Tests
- Category Domain Tests
- Account Domain Tests
- Frontend Linting & Code Style
- Database Schema Migrations
- Frontend Linting & Code Style
- Envelope Budgeting System
- Account Management & Balances
- Account Domain Tests
- Account Domain Tests
- Financed Transactions & Loans
- Envelope Budgeting System
- Account Domain Tests
- Budget Category Hierarchy
- Svelte 5 Runes & Best Practices
- Account Management & Balances
- Budget Category Hierarchy
- Account Domain Tests
- Budget Category Hierarchy
- Account Domain Tests
- Envelope Budgeting System
- Account Domain Tests
- Envelope Domain Tests
- Frontend Linting & Code Style
- Frontend Build & Config
- Account Domain Tests
- Account Domain Tests
- Account Domain Tests
- Envelope Domain Tests
- Financed Transactions & Loans
- Financed Transactions & Loans
- Category Domain Tests
- Frontend User Interface
- Envelope Domain Tests
- Financed Transactions & Loans
- Frontend User Interface
- Frontend User Interface
- Category Domain Tests
- Envelope Domain Tests
- Envelope Domain Tests
- Account Domain Tests
- Database Engine & Seeding
- Category Domain Tests
- Frontend User Interface
- Frontend User Interface
- Frontend Linting & Code Style
- Frontend Build & Config
- Frontend User Interface
- Frontend User Interface
- Frontend User Interface
- Backend Service API

## God Nodes (most connected - your core abstractions)
1. `EnvelopeBase` - 83 edges
2. `TransactionRequest` - 64 edges
3. `AccountBase` - 39 edges
4. `EnvelopeSplitRequest` - 35 edges
5. `get_or_create_account()` - 34 edges
6. `AccountCreate` - 30 edges
7. `TransactionUpdateRequest` - 29 edges
8. `Envelope` - 26 edges
9. `get_envelope_by_name()` - 26 edges
10. `FinancedTransaction` - 25 edges

## Surprising Connections (you probably didn't know these)
- `setup_test_database()` --calls--> `EnvelopeCategory`  [INFERRED]
  backend/tests/conftest.py → backend/src/budget_app/models/category.py
- `setup_test_database()` --calls--> `Envelope`  [INFERRED]
  backend/tests/conftest.py → backend/src/budget_app/models/envelope.py
- `EnvelopeTransfer` --uses--> `Transaction`  [INFERRED]
  backend/src/budget_app/schemas/envelope.py → backend/src/budget_app/models/transaction.py
- `get_or_create_account()` --calls--> `AccountBase`  [INFERRED]
  backend/tests/test_transaction_service.py → backend/src/budget_app/schemas/account.py
- `setup_test_database()` --calls--> `AccountCreate`  [INFERRED]
  backend/tests/conftest.py → backend/src/budget_app/schemas/account.py

## Import Cycles
- 3-file cycle: `backend/src/budget_app/repositories/__init__.py -> backend/src/budget_app/repositories/ledger_repo.py -> backend/src/budget_app/repositories/envelope_split_repo.py -> backend/src/budget_app/repositories/__init__.py`
- 3-file cycle: `backend/src/budget_app/models/__init__.py -> backend/src/budget_app/models/account.py -> backend/src/budget_app/repositories/account_repo.py -> backend/src/budget_app/models/__init__.py`

## Hyperedges (group relationships)
- **Svelte 5 AI Tooling Ecosystem** — frontend__gemini_agents_svelte_file_editor_agent, frontend__gemini_skills_svelte_code_writer_skill_tool, frontend_gemini_mcp_tools, frontend__gemini_skills_svelte_core_bestpractices_skill_guidelines [EXTRACTED 1.00]
- **Svelte 5 Template Syntax Modernization** — frontend__gemini_skills_svelte_core_bestpractices_references_snippet_declaration, frontend__gemini_skills_svelte_core_bestpractices_references_render_tag, frontend__gemini_skills_svelte_core_bestpractices_references_attach_directive, frontend__gemini_skills_svelte_core_bestpractices_references_each_keyed_blocks [EXTRACTED 1.00]
- **Svelte Async SSR & Hydration Lifecycle** — frontend__gemini_skills_svelte_core_bestpractices_references_await_expressions_feature, frontend__gemini_skills_svelte_core_bestpractices_references_hydratable_api, frontend__gemini_skills_svelte_core_bestpractices_references_await_expressions_fork_api [EXTRACTED 1.00]

## Communities (73 total, 39 thin omitted)

### Community 0 - "Category Domain Tests"
Cohesion: 0.06
Nodes (28): create_category(), delete_category(), get_categories(), get_categories_with_envelopes(), get_category(), update_category(), init_db(), EnvelopeCategory (+20 more)

### Community 1 - "Account Management & Balances"
Cohesion: 0.08
Nodes (24): health(), activate_account(), create_account(), delete_account(), get_account(), get_accounts(), update_account(), acct_payment() (+16 more)

### Community 2 - "Financed Transactions & Loans"
Cohesion: 0.08
Nodes (8): TestAddFinancedTransactionRoute, TestAddRegularTransactionRoute, TestDeleteTransactionRoute, TestGetTransactionByIdRoute, TestGetTransactionsRoute, TestInterestTransactionsRoute, TestPaymentsAndAdjustmentsRoutes, TestUpdateTransactionRoute

### Community 4 - "Account Management & Balances"
Cohesion: 0.11
Nodes (16): get_account_by_name(), get_balance_for_account(), get_balance_for_envelope(), get_envelope_by_id(), create_transaction(), activate_account(), add_interest_charge(), add_interest_earned() (+8 more)

### Community 5 - "Account Domain Tests"
Cohesion: 0.09
Nodes (8): base_setup(), TestCreateEnvelopeRoute, TestDeleteEnvelopeRoute, TestEnvelopeLifecycleRoutes, TestEnvelopeTransfersAndFundingRoutes, TestGetEnvelopeByNameRoute, TestGetEnvelopesRoute, TestUpdateEnvelopeRoute

### Community 6 - "Account Management & Balances"
Cohesion: 0.13
Nodes (13): Envelope, create_envelope(), delete_envelope(), get_envelope_by_name(), EnvelopeTransfer, activate_envelope(), add_to_cash(), assign_to_envelope() (+5 more)

### Community 7 - "Account Management & Balances"
Cohesion: 0.11
Nodes (6): EnvelopeSplitBase, EnvelopeSplitResponse, TransactionBase, TransactionDetailResponse, TransactionResponse, TransactionType

### Community 8 - "Database Schema Migrations"
Cohesion: 0.09
Nodes (9): render_item(), run_migrations_offline(), run_migrations_online(), Config, client(), db_engine(), ensure_test_database_exists(), session() (+1 more)

### Community 9 - "Account Domain Tests"
Cohesion: 0.11
Nodes (7): TestActivateAccountRoute, TestCreateAccountRoute, TestDeleteAccountRoute, TestGetAccountByNameRoute, TestGetAccountsRoute, TestHealthEndpoint, TestUpdateAccountRoute

### Community 11 - "Financed Transactions & Loans"
Cohesion: 0.10
Nodes (10): Transaction, get_or_create_envelope(), get_transaction_by_id(), get_transactions(), add_financed_transaction(), calculate_transaction_total(), delete_transaction(), get_transactions() (+2 more)

### Community 12 - "Financed Transactions & Loans"
Cohesion: 0.19
Nodes (4): FinancedTransaction, get_or_create_account(), TestAddFinancedTransaction, transaction_set_up()

### Community 13 - "Category Domain Tests"
Cohesion: 0.13
Nodes (6): TestCreateCategoryRoute, TestDeleteCategoryRoute, TestGetCategoriesRoute, TestGetCategoriesWithEnvelopesRoute, TestGetCategoryByNameRoute, TestUpdateCategoryRoute

### Community 14 - "Category Domain Tests"
Cohesion: 0.14
Nodes (6): EnvelopeBase, TestGetCategoriesWithEnvelopes, TestCreateEnvelope, TestEnvelopeCategoryIntegration, TestGetEnvelopesAndBalances, transfer_setup()

### Community 15 - "Account Domain Tests"
Cohesion: 0.23
Nodes (3): TransactionRequest, TransactionUpdateRequest, TestUpdateTransaction

### Community 16 - "Frontend Linting & Code Style"
Cohesion: 0.10
Nodes (21): devDependencies, eslint, eslint-config-prettier, @eslint/js, eslint-plugin-svelte, globals, prettier, prettier-plugin-svelte (+13 more)

### Community 17 - "Database Schema Migrations"
Cohesion: 0.14
Nodes (6): upgrade(), upgrade(), downgrade(), upgrade(), upgrade(), upgrade()

### Community 18 - "Frontend Linting & Code Style"
Cohesion: 0.12
Nodes (18): name, private, type, version, prettier, prettier-plugin-svelte, prettier-plugin-tailwindcss, svelte (+10 more)

### Community 19 - "Envelope Budgeting System"
Cohesion: 0.24
Nodes (11): activate_envelope(), add_income_to_cash(), assign_envelope(), create_envelope(), deactivate_envelope(), delete_envelope(), get_envelope(), get_envelopes() (+3 more)

### Community 20 - "Account Management & Balances"
Cohesion: 0.14
Nodes (3): AccountType, AccountWithBalance, SystemEnvelopeType

### Community 22 - "Account Domain Tests"
Cohesion: 0.17
Nodes (3): AccountBase, AccountUpdate, TestAccountLifecycleAndFiltering

### Community 26 - "Account Domain Tests"
Cohesion: 0.26
Nodes (3): AccountCreate, TestCreateAccount, TestStartingBalanceAndDerivedBalance

### Community 27 - "Budget Category Hierarchy"
Cohesion: 0.21
Nodes (4): CashIncomeRequest, EnvelopeAssignRequest, EnvelopeCreate, EnvelopeTransferRequest

### Community 28 - "Svelte 5 Runes & Best Practices"
Cohesion: 0.20
Nodes (11): Svelte Attach Directive ({@attach}), Async Svelte Await Expressions, Svelte Fork Preloading API, Svelte Function Bindings, Keyed Each Blocks, Svelte Hydratable API, Svelte Inspect Rune ($inspect), Svelte Render Tag ({@render}) (+3 more)

### Community 29 - "Account Management & Balances"
Cohesion: 0.20
Nodes (5): create_account(), get_account_by_id(), get_accounts(), get_accounts_with_balances(), has_non_starting_transactions()

### Community 30 - "Budget Category Hierarchy"
Cohesion: 0.20
Nodes (5): get_envelope_by_system_role(), get_envelopes(), get_envelopes_by_category(), get_system_envelope(), has_splits()

### Community 32 - "Budget Category Hierarchy"
Cohesion: 0.31
Nodes (4): EnvelopeWithBalance, get_active_envelopes_w_balance(), get_envelopes_and_balances(), get_inactive_envelopes_w_balance()

### Community 34 - "Envelope Budgeting System"
Cohesion: 0.25
Nodes (3): add_envelope_split(), EnvelopeSplitRequest, add_reg_transaction()

### Community 37 - "Frontend Linting & Code Style"
Cohesion: 0.22
Nodes (7): gitignorePath, eslint, eslint-config-prettier, @eslint/js, eslint-plugin-svelte, globals, typescript-eslint

### Community 38 - "Frontend Build & Config"
Cohesion: 0.22
Nodes (9): scripts, build, check, check:watch, dev, format, lint, prepare (+1 more)

### Community 46 - "Frontend User Interface"
Cohesion: 0.29
Nodes (6): compilerOptions, strict, types, extends, include, $app/tsconfig

### Community 50 - "Frontend User Interface"
Cohesion: 0.33
Nodes (5): mcpServers, svelte, $schema, args, command

### Community 57 - "Database Engine & Seeding"
Cohesion: 0.67
Nodes (3): PostgreSQL Database Service, PostgreSQL Data Volume, FastAPI Backend Application

### Community 60 - "Frontend User Interface"
Cohesion: 1.00
Nodes (3): Svelte File Editor Agent, Svelte Code Writer Skill, Svelte MCP Tools Suite

### Community 61 - "Frontend User Interface"
Cohesion: 0.67
Nodes (3): Frontend Gemini Project Configuration, Sveltekit Project Scaffolding CLI (sv), SvelteKit App Shell Template

## Knowledge Gaps
- **24 isolated node(s):** `budget_app`, `@sveltejs/vite-plugin-svelte`, `@tailwindcss/forms`, `@types/node`, `prettier` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 349 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EnvelopeBase` connect `Category Domain Tests` to `Category Domain Tests`, `Account Management & Balances`, `Account Management & Balances`, `Account Management & Balances`, `Database Schema Migrations`, `Financed Transactions & Loans`, `Category Domain Tests`, `Envelope Budgeting System`, `Account Management & Balances`, `Account Domain Tests`, `Account Domain Tests`, `Envelope Budgeting System`, `Budget Category Hierarchy`, `Account Domain Tests`, `Budget Category Hierarchy`, `Account Domain Tests`, `Account Domain Tests`, `Envelope Domain Tests`, `Account Domain Tests`, `Envelope Domain Tests`, `Financed Transactions & Loans`, `Envelope Domain Tests`, `Financed Transactions & Loans`, `Envelope Domain Tests`, `Account Domain Tests`, `Category Domain Tests`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `EnvelopeBase` (e.g. with `.test_delete_account_with_expense_transaction_raises_error()` and `.test_adjust_cash_balance_decrease_with_envelope()`) actually correct?**
  _`EnvelopeBase` has 56 INFERRED edges - model-reasoned connections that need verification._
- **What connects `budget_app`, `@sveltejs/vite-plugin-svelte`, `@tailwindcss/forms` to the rest of the system?**
  _24 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Category Domain Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.05879692446856626 - nodes in this community are weakly interconnected._
- **Why does `TestGetTransactions` connect `Financed Transactions & Loans` to `Financed Transactions & Loans`, `Account Domain Tests`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `TransactionRequest` (e.g. with `EnvelopeSplitRequest` and `.test_delete_account_with_expense_transaction_raises_error()`) actually correct?**
  _`TransactionRequest` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Should `Account Management & Balances` be split into smaller, more focused modules?**
  _Cohesion score 0.07918552036199095 - nodes in this community are weakly interconnected._