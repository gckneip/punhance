# Credit Card Entity Specification

## Purpose

The Credit Card entity represents a revolving line of credit that generates debt and monthly statements.

A credit card is not a bank account and does not hold money.

Instead, it tracks:

* Purchases
* Installments
* Available credit
* Statement closing dates
* Payment due dates
* Outstanding debt

---

# Responsibilities

The Credit Card entity must:

* Store card information
* Calculate current debt
* Calculate available credit
* Determine statement periods
* Associate purchases with statements
* Register payments

The Credit Card entity must NOT:

* Store income
* Hold balances like a checking account
* Store transaction categories

---

# Entity Definition

```python
class CreditCard:
    id: UUID
    name: str
    issuer: str
    credit_limit: Decimal
    closing_day: int
    due_day: int
    is_active: bool
```

---

# Fields

## id

Unique identifier.

Example:

```text
cc_001
```

---

## name

User-facing card name.

Examples:

```text
Nubank
Inter Black
Visa Infinite
```

---

## issuer

Institution responsible for the card.

Examples:

```text
Nubank
Banco Inter
Santander
```

---

## credit_limit

Maximum available credit.

Example:

```text
5000.00
```

---

## closing_day

Day of the month when the statement closes.

Example:

```text
10
```

Meaning:

Purchases after the 10th belong to the next statement.

---

## due_day

Day of the month when payment is due.

Example:

```text
17
```

---

## is_active

Indicates whether the card is currently usable.

Values:

```text
true
false
```

---

# Database Table

```sql
CREATE TABLE credit_cards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    credit_limit REAL NOT NULL,
    closing_day INTEGER NOT NULL,
    due_day INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

---

# Credit Card Transactions

Transactions performed using a credit card must reference the card.

Example:

```text
Expense
---------
Date: 2026-06-01
Amount: 45.90
Category: Food
Credit Card: Nubank
Description: Restaurant
```

The transaction generates debt.

It does NOT immediately affect any bank account.

---

# Installments

The system must support installment purchases.

Example:

```text
Notebook
R$ 3,000
10 installments
```

Stored as:

```text
300.00
per month
for 10 months
```

Each installment belongs to a statement.

---

# Credit Utilization

Formula:

```text
used_credit = sum(open_card_transactions)

available_credit = credit_limit - used_credit
```

Example:

```text
Limit: R$ 5,000

Open Purchases:
- 100
- 200
- 300

Used: 600
Available: 4,400
```

---

# Statement

A statement groups purchases into a billing cycle.

Example:

```text
Card: Nubank

Closing Day: 10

Period:
11/05 -> 10/06
```

Transactions in this interval belong to the same statement.

---

# Statement Entity

```python
class CreditCardStatement:
    id: UUID
    credit_card_id: UUID
    period_start: date
    period_end: date
    due_date: date
    total_amount: Decimal
    status: str
```

Status:

```text
OPEN
CLOSED
PAID
OVERDUE
```

---

# Payments

Paying a statement creates a transfer.

Example:

```text
Checking Account
      ↓
Credit Card Payment
      ↓
Nubank Statement
```

The payment:

* decreases bank account balance
* decreases card debt

---

# Future Features

## Multiple Cards

A user may own multiple cards.

Examples:

```text
Nubank
Inter
C6
```

---

## Rewards

Optional future support:

* Cashback
* Points
* Miles

---

## Virtual Cards

Optional future support:

* Temporary cards
* Online-only cards

---

# MVP Scope

Version 0.1 must support:

* Create card
* Register card purchases
* Register card payments
* View current debt
* View available credit

Version 0.1 does NOT require:

* Installments
* Rewards
* Miles
* Virtual cards
* Statement generation automation
* Bank synchronization

