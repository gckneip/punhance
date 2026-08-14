# Personal Finance Manager

## Goal

A desktop application for managing personal finances using:

* Python
* PySide6
* SQLite

The application should be lightweight, local-first, and designed for a single user.

Data must remain entirely under the user's control and be easily portable between machines.

---

# Core Features

## Transactions

The user can record:

* Expenses
* Income
* Transfers between accounts

Each transaction contains:

| Field       | Type                    |
| ----------- | ----------------------- |
| id          | UUID                    |
| date        | Date                    |
| amount      | Decimal                 |
| description | Text                    |
| category_id | FK                      |
| account_id  | FK                      |
| type        | expense/income/transfer |
| notes       | Text                    |
| created_at  | Timestamp               |
| updated_at  | Timestamp               |

---

## Categories

User-defined categories.

Examples:

* Food
* Transport
* Housing
* Health
* Entertainment
* Salary
* Investments

Categories may have:

* Name
* Color
* Parent category (optional)

Examples:

Food
├── Restaurant
├── Groceries
└── Coffee

---

## Accounts

Represents where money is stored.

Examples:

* Cash
* Checking Account
* Savings Account
* Credit Card
* Investment Account

Fields:

| Field           | Type    |
| --------------- | ------- |
| id              | UUID    |
| name            | Text    |
| type            | Text    |
| initial_balance | Decimal |

---

## Dashboard

Main screen displaying:

* Current balance
* Monthly income
* Monthly expenses
* Savings rate
* Recent transactions

---

## Reports

### Monthly Report

Displays:

* Income
* Expenses
* Net result

### Category Breakdown

Displays:

* Total spent per category
* Percentage per category

### Account Summary

Displays balances for all accounts.

---

## Search

Search transactions by:

* Date range
* Category
* Account
* Description

---

# Future Features

## Attachments

Allow receipts and invoices.

Examples:

* PDF
* JPG
* PNG

Store files outside SQLite.

Example:

data/
├── finance.db
└── attachments/

---

## Budgets

User can define monthly budgets.

Example:

Food -> R$ 800

The system warns when spending approaches the limit.

---

## Recurring Transactions

Examples:

* Rent
* Salary
* Subscriptions

Rules:

* Monthly
* Weekly
* Yearly

Generated automatically.

---

# Database Design

## categories

```sql
CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    parent_id TEXT
);
```

## accounts

```sql
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    initial_balance REAL NOT NULL
);
```

## transactions

```sql
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    category_id TEXT,
    account_id TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY(category_id) REFERENCES categories(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);
```

---

# Application Architecture

Use a simplified Onion Architecture.

```text
src/

├── application/
│   ├── use_cases/
│   └── dto/
│
├── domain/
│   ├── entities/
│   ├── repositories/
│   └── services/
│
├── infrastructure/
│   ├── database/
│   ├── repositories/
│   └── config/
│
├── presentation/
│   ├── windows/
│   ├── dialogs/
│   ├── widgets/
│   └── viewmodels/
│
└── main.py
```

Rules:

* Domain knows nothing about PySide.
* Domain knows nothing about SQLite.
* Presentation never executes SQL directly.
* Repositories are responsible for persistence.

---

# MVP

Version 0.1 must support only:

* Create account
* Create category
* Create transaction
* List transactions
* Monthly summary

No charts.
No attachments.
No budgets.
No recurring transactions.

The application is considered successful when it can completely replace a spreadsheet used for tracking personal expenses.

