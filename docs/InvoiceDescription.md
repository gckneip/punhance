# Invoice / Receipt Specification

## Goal

Allow a single financial transaction to contain multiple purchased items.

This enables:

* Accurate grocery tracking
* Product-level statistics
* Category-level spending analysis
* Future price history analysis

Example:

Transaction Total:
R$ 35.00

Items:

* Milk
* Bread
* Coffee

The system should know:

* R$ 10 spent on milk
* R$ 5 spent on bread
* R$ 20 spent on coffee

even though they belong to one payment.

---

# Relationship Model

```text
Account/Credit Card
        │
        ▼
Transaction
        │
        ▼
Invoice
        │
        ├── InvoiceItem
        ├── InvoiceItem
        └── InvoiceItem
```

---

# Transaction

Represents the financial event.

Example:

```text
2026-06-01

Supermarket XYZ

Total:
R$ 120.00
```

Only one transaction exists.

---

# Invoice

Represents the receipt associated with a transaction.

One transaction may have:

```text
0 invoices
or
1 invoice
```

Examples:

Invoice:

* Grocery store receipt
* Pharmacy receipt

No invoice:

* Salary
* Rent
* Bank transfer
* Credit card payment

---

# Invoice Entity

```python
class Invoice:
    id: UUID
    transaction_id: UUID
    merchant_name: str
    invoice_date: date
    total_amount: Decimal
    notes: str | None
```

---

# Database Table

```sql
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL UNIQUE,
    merchant_name TEXT,
    invoice_date TEXT NOT NULL,
    total_amount REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY(transaction_id)
        REFERENCES transactions(id)
);
```

---

# Invoice Item

Represents a purchased product.

Example:

Milk 2L
Bread
Coffee Beans

---

# Invoice Item Entity

```python
class InvoiceItem:
    id: UUID
    invoice_id: UUID
    name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total_price: Decimal
    category_id: UUID
```

---

# Database Table

```sql
CREATE TABLE invoice_items (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    category_id TEXT,
    FOREIGN KEY(invoice_id)
        REFERENCES invoices(id),
    FOREIGN KEY(category_id)
        REFERENCES categories(id)
);
```

---

# Units

Examples:

```text
UNIT
KG
G
L
ML
BOX
PACK
```

Examples:

Milk:
2 L

Bananas:
1.2 KG

Eggs:
12 UNIT

````

---

# Categories

Invoice items may belong to categories.

Example:

```text
Food
├── Milk
├── Bread
└── Cheese

Cleaning
├── Soap
└── Detergent
````

A category is attached to the item, not the invoice.

---

# Validation

The sum of all invoice items must equal the invoice total.

Formula:

```text
SUM(invoice_items.total_price)
=
invoice.total_amount
```

The application should warn when values differ.

---

# Statistics

The system must support:

## Spending by Product

Example:

```text
Milk
R$ 230.00

Bread
R$ 180.00

Coffee
R$ 350.00
```

---

## Spending by Category

Example:

```text
Food
R$ 2,000

Cleaning
R$ 500
```

---

## Product Price History

Example:

Milk

Jan: R$ 5.50
Feb: R$ 5.80
Mar: R$ 6.20
Apr: R$ 5.90

````

---

# Future Features

## Receipt Attachment

Store:

- PDF
- PNG
- JPG

linked to an invoice.

---

## OCR Import

User uploads:

```text
receipt.jpg
````

System extracts:

* Product names
* Quantities
* Prices

and automatically creates invoice items.

---

# MVP Scope

Version 0.1

Must support:

* Create invoice
* Add invoice items
* Associate invoice with transaction
* Categorize items
* Product spending reports

Does not require:

* OCR
* Barcode scanning
* Automatic category detection
* Price history charts
* Attachments

