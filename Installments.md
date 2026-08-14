# Financial Event & Installment Architecture

## Motivation

The original Transaction model becomes overloaded as the application grows.

A single transaction may represent:

* An expense
* An income
* A transfer
* A credit card purchase
* An invoice
* A card payment
* An installment

These concepts have different responsibilities.

To keep the domain clean, the system introduces the Financial Event abstraction.

---

# Core Principle

A Financial Event is any occurrence that affects the user's financial situation.

Examples:

* Salary received
* Grocery purchase
* Credit card payment
* Bank transfer
* Loan payment
* Investment purchase

Everything in the system begins as a Financial Event.

---

# Financial Event Entity

```python
class FinancialEvent:
    id: UUID
    event_type: EventType
    event_date: date
    description: str
    created_at: datetime
    updated_at: datetime
```

---

# Event Types

```text
INCOME
EXPENSE
TRANSFER
PURCHASE
CARD_PAYMENT
LOAN_PAYMENT
INVESTMENT
REFUND
```

New event types may be added in the future.

---

# Database Table

```sql
CREATE TABLE financial_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

---

# Purchase Event

Represents the acquisition of goods or services.

Examples:

* Supermarket purchase
* Pharmacy purchase
* Electronics purchase

A Purchase Event may contain:

* Invoice
* Installment Plan

A Purchase Event does not directly represent payment.

---

# Purchase Entity

```python
class Purchase:
    id: UUID
    financial_event_id: UUID
    total_amount: Decimal
    payment_method: PaymentMethod
```

---

# Payment Methods

```text
CASH
DEBIT_CARD
CREDIT_CARD
PIX
BANK_TRANSFER
```

---

# Database Table

```sql
CREATE TABLE purchases (
    id TEXT PRIMARY KEY,
    financial_event_id TEXT NOT NULL UNIQUE,
    total_amount REAL NOT NULL,
    payment_method TEXT NOT NULL,
    FOREIGN KEY(financial_event_id)
        REFERENCES financial_events(id)
);
```

---

# Invoice Relationship

```text
FinancialEvent
      │
      ▼
Purchase
      │
      ▼
Invoice
      │
      ├── Item
      ├── Item
      └── Item
```

The invoice represents what was purchased.

The purchase represents the financial action.

---

# Installment Philosophy

Installments represent future obligations created by a purchase.

A purchase may:

```text
Have no installments

or

Generate an installment plan
```

---

# Installment Plan

Represents how a purchase is divided.

Example:

Notebook
R$ 3,000

10 installments

````

---

# Installment Plan Entity

```python
class InstallmentPlan:
    id: UUID
    purchase_id: UUID
    total_amount: Decimal
    installment_count: int
    created_at: datetime
````

---

# Database Table

```sql
CREATE TABLE installment_plans (
    id TEXT PRIMARY KEY,
    purchase_id TEXT NOT NULL,
    total_amount REAL NOT NULL,
    installment_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(purchase_id)
        REFERENCES purchases(id)
);
```

---

# Installment Entity

Represents a single future obligation.

Example:

1/10
2/10
3/10

Each installment is independently tracked.

---

# Installment Entity Definition

```python
class Installment:
    id: UUID
    installment_plan_id: UUID
    installment_number: int
    amount: Decimal
    due_date: date
    status: InstallmentStatus
```

---

# Installment Status

```text
PENDING
PAID
OVERDUE
CANCELLED
```

---

# Database Table

```sql
CREATE TABLE installments (
    id TEXT PRIMARY KEY,
    installment_plan_id TEXT NOT NULL,
    installment_number INTEGER NOT NULL,
    amount REAL NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(installment_plan_id)
        REFERENCES installment_plans(id)
);
```

---

# Example

Purchase:

```text
Notebook
R$ 3,000
```

Installment Plan:

```text
10 installments
```

Generated records:

```text
1/10 -> R$ 300
2/10 -> R$ 300
3/10 -> R$ 300
...
10/10 -> R$ 300
```

---

# Credit Card Integration

A purchase may reference a credit card.

```python
class Purchase:
    ...
    credit_card_id: UUID | None
```

Example:

```text
Purchase
│
├── Credit Card: Nubank
├── Invoice
└── Installment Plan
```

---

# Card Statements

Statements are generated from installments.

Example:

Statement June

Contains:

Notebook 1/10
Phone 3/12
TV 5/8

````

The statement total equals the sum of all installments belonging to that billing cycle.

---

# Reporting Model

The application supports two independent views.

## Consumption View

Based on invoice items.

Example:

```text
Milk
Bread
Coffee
````

Questions answered:

* How much milk was purchased?
* How much was spent on food?
* Which products are becoming more expensive?

---

## Obligation View

Based on installments.

Example:

```text
Remaining Debt

Notebook
7 installments left

TV
2 installments left
```

Questions answered:

* How much debt remains?
* What will I owe next month?
* Which cards have the largest commitments?

---

# Accounting Principle

Consumption and payment are separate concepts.

Example:

```text
Purchase Date:
2026-06-01

Milk:
R$ 20
```

Consumption occurred in June.

Even if payment happens in:

```text
July
August
September
```

The item remains attributed to June consumption.

This distinction must be preserved throughout the system.

---

# MVP Scope

Version 0.1 must support:

* Financial Events
* Purchases
* Invoices
* Invoice Items
* Credit Cards
* Installment Plans
* Installments

Version 0.1 does not require:

* Automatic statement generation
* OCR
* Cashback
* Rewards
* Loan management
* Investments
* Multi-currency support

```
```

