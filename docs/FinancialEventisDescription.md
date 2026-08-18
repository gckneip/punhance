# Domain Model v2 - Financial Events, Expenses, Purchases and Installments

## Design Goals

The model must support:

* Bank accounts
* Credit cards
* Income
* Expenses
* Transfers
* Grocery invoices
* Utility bills
* Rent
* Installments
* Product-level analytics

while remaining simple enough for a single-user desktop application.

---

# Core Domain

The system revolves around Financial Events.

```text
FinancialEvent
├── Income
├── Expense
├── Purchase
└── Transfer
```

Only four event types exist in the MVP.

---

# FinancialEvent

Represents any event that affects the user's finances.

## Entity

```python
class FinancialEvent:
    id: UUID
    event_type: EventType
    event_date: date
    description: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

## Event Types

```text
INCOME
EXPENSE
PURCHASE
TRANSFER
```

---

# Income

Represents money entering the system.

Examples:

* Salary
* Bonus
* Refund
* Interest

## Additional Fields

```python
amount: Decimal
account_id: UUID
category_id: UUID
```

Examples:

```text
Salary
Freelance Payment
Investment Yield
```

---

# Expense

Represents a non-itemized expense.

Examples:

* Rent
* Electricity
* Water
* Internet
* Insurance
* Taxes

````

## Additional Fields

```python
amount: Decimal
payment_method: PaymentMethod
category_id: UUID
account_id: UUID | None
credit_card_id: UUID | None
````

Examples:

```text
Rent
Electricity Bill
Internet Subscription
```

No invoice exists.

No item breakdown exists.

---

# Purchase

Represents itemized consumption.

Examples:

* Supermarket
* Pharmacy
* Electronics
* Pet Shop

A purchase may contain:

```text
Invoice
Installment Plan
```

## Additional Fields

```python
total_amount: Decimal
payment_method: PaymentMethod
account_id: UUID | None
credit_card_id: UUID | None
```

---

# Transfer

Represents money movement.

Examples:

* Checking → Savings
* Checking → Investment Account
* Checking → Credit Card Payment

## Additional Fields

```python
source_account_id: UUID
destination_account_id: UUID
amount: Decimal
```

Transfers do not create income or expenses.

---

# Categories

Categories classify Income and Expense records.

## Examples

```text
Income
├── Salary
├── Bonus
└── Investments

Housing
├── Rent
├── Electricity
├── Water
└── Internet

Transport
├── Fuel
├── Parking
└── Uber

Food
├── Grocery
├── Restaurant
└── Coffee
```

---

# Credit Cards

Credit cards are independent entities.

They represent debt, not money.

## Entity

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

# Invoice

Invoices exist only for Purchase events.

## Relationship

```text
Purchase
    │
    ▼
Invoice
    │
    ├── InvoiceItem
    ├── InvoiceItem
    └── InvoiceItem
```

---

# Invoice

```python
class Invoice:
    id: UUID
    purchase_id: UUID
    merchant_name: str
    invoice_date: date
    total_amount: Decimal
```

---

# Invoice Item

Represents an individual product.

## Entity

```python
class InvoiceItem:
    id: UUID
    invoice_id: UUID
    product_name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total_price: Decimal
    category_id: UUID
```

---

# Product Categories

Product categories are independent from expense categories.

## Examples

```text
Food
├── Milk
├── Bread
├── Cheese

Cleaning
├── Soap
├── Detergent
```

These categories exist solely for analytics.

---

# Installment Plans

Installments belong to Purchases.

A Purchase may:

```text
Have no installment plan

or

Generate an installment plan
```

---

# Installment Plan

```python
class InstallmentPlan:
    id: UUID
    purchase_id: UUID
    total_amount: Decimal
    installment_count: int
```

---

# Installment

Represents a future obligation.

```python
class Installment:
    id: UUID
    installment_plan_id: UUID
    installment_number: int
    amount: Decimal
    due_date: date
    status: InstallmentStatus
```

## Status

```text
PENDING
PAID
OVERDUE
CANCELLED
```

---

# Consumption vs Payment

The system separates:

## Consumption

"What did I buy?"

Source:

```text
Invoice Items
```

Examples:

```text
Milk
Bread
Coffee
```

---

## Payment

"What do I owe?"

Source:

```text
Installments
Credit Card Statements
```

Examples:

```text
Notebook
7 installments remaining
```

These are different concepts and must never be merged.

---

# Credit Card Statements

Future Feature

Statements are generated from:

```text
Installments
+
Card Purchases
```

Statement data should be derived, not manually entered.

---

# MVP Tables

```text
financial_events
accounts
credit_cards
categories

purchases
expenses
income
transfers

invoices
invoice_items

installment_plans
installments
```

---

# MVP Features

Must Support:

* Accounts
* Credit Cards
* Categories
* Income
* Expenses
* Purchases
* Invoices
* Invoice Items
* Installments
* Transfers

Must Not Support Yet:

* OCR
* Automatic statement generation
* Investments
* Loans
* Recurring expenses
* Budgeting
* Multi-user support
* Cloud synchronization

```
```

