# Audit Report — Post-Implementation Review

Generated after completing 5 bug fixes + 6 features.

---

## Bugs to Fix

### HIGH Priority

| # | Issue | Location | Description |
|---|-------|----------|-------------|
| 1 | **Crash on month 12** | `purchase_use_cases.py:64-74` | `first_due_date = date(year, month + 1, day)` raises ValueError when month=12 (13 is invalid). The `if month == 12` guard is dead code — exception thrown before it runs. Also crashes for day 29-31 when next month has fewer days. |
| 2 | **Dashboard row count mismatch** | `dashboard_widget.py:87-88` | `setRowCount(len(events))` but only fills first 20. Creates empty trailing rows. Fix: `setRowCount(min(len(events), 20))`. |

### MEDIUM Priority

| # | Issue | Location | Description |
|---|-------|----------|-------------|
| 3 | **"Current Balance" misleading** | `dashboard_widget.py:75` | Card title says "Current Balance" but shows monthly net. Should show actual account balance or rename to "Monthly Net". |
| 4 | **Card payment amount not validated** | `credit_card_use_cases.py:51-81` | `dto.amount` never cross-checked against sum of selected `dto.installment_ids`. |
| 5 | **Installment filters silently ignored** | `installment_use_cases.py:25-33` | When `credit_card_id` is set, status/date params are ignored. |
| 6 | **update_purchase ignores installment changes** | `purchase_use_cases.py:111-162` | Old installment plan/installments never deleted when count changes. |
| 7 | **Overdue installments not pre-checked** | `card_payment_dialog.py:73-74` | Only "pending" pre-checked, not "overdue". |
| 8 | **PurchaseDTO type annotations wrong** | `purchase_dto.py:52-53` | `event_date`/`description` typed non-optional but can be None. |
| 9 | **Duplicate InstallmentDTO** | `purchase_dto.py:64` + `installment_dto.py:6` | Same class in two files, imported differently. |
| 10 | **No error handling on DB init** | `main.py:30-31` | `get_connection()`/`create_tables()` can crash without user message. |

### LOW Priority

| # | Issue | Location | Description |
|---|-------|----------|-------------|
| 11 | Missing dialog validation | `account_dialog.py`, `category_dialog.py`, `counterparty_dialog.py`, `credit_card_dialog.py` | No validation that name fields are non-empty. |

---

## Missing Features

### MVP-Relevant (Per Specs)

| # | Feature | Spec Reference | Notes |
|---|---------|---------------|-------|
| 1 | **Edit/Delete UI** | Implicit in all specs | Use case methods exist (`delete_account`, `delete_category`, etc.) but no buttons or dialogs in the GUI. |
| 2 | **Spending by Product report** | `InvoiceDescription.md:250-264` | Aggregate purchase_items by product name across all purchases. |
| 3 | **Spending by Category (item-level)** | `InvoiceDescription.md:268-278` | Aggregate purchase_items by category_id (different from event-level Category Breakdown). |
| 4 | **Product Price History** | `InvoiceDescription.md:282-293` | Track unit_price per product over time (e.g., Milk Jan: R$5.50, Feb: R$5.80). |
| 5 | **Credit Card Statement entity** | `creditCardEspecification.md:258-276` | Statement with period_start, period_end, due_date, total_amount, status (OPEN/CLOSED/PAID/OVERDUE). |
| 6 | **Obligation View report** | `Installments.md:375-395` | Remaining debt summary, future obligations per card/purchase. |
| 7 | **Consumption View report** | `Installments.md:353-371` | Product-level spending analytics across purchases. |
| 8 | **Unused event types in UI** | `Installments.md:56-65` | LOAN_PAYMENT, INVESTMENT, REFUND defined in enum but never exposed in event creation dialog. |

### Future Features (Explicitly Deferred)

| Feature | Spec Reference |
|---------|---------------|
| Budgets | `Descripton.md:164-172` |
| Recurring Transactions | `Descripton.md:174-188` |
| Attachments/OCR | `Descripton.md:143-162`, `InvoiceDescription.md:298-325` |
| Credit Card Rewards | `creditCardEspecification.md:317-323` |
| Virtual Cards | `creditCardEspecification.md:328-333` |
| Investments | `FinancialEventisDescription.md:466` |
| Loan Management | `Installments.md:447` |

---

## Dead Code / Cleanup

### Unused Imports

| File | Import |
|------|--------|
| `main_window.py` | `QTextEdit`, `QHeaderView`, `Qt` |
| `category_breakdown_widget.py` | `QHeaderView`, `QComboBox`, `Qt` |
| `dashboard_widget.py` | `QHeaderView`, `Qt` |
| `account_summary_widget.py` | `QHeaderView` |
| `installments_widget.py` | `QHeaderView` |
| `card_payment_dialog.py` | `QHeaderView` |
| `purchase_dialog.py` | `Optional` |
| `category_dialog.py` | `Optional` |

### Unused Classes

| File | Class |
|------|-------|
| `purchase_dto.py:56-61` | `PurchaseDetailDTO` — defined but never imported or used |

---

## Hardcoded Values (Low Priority)

| Value | Location | Notes |
|-------|----------|-------|
| `"R$ "` prefix | Multiple presentation files | Should be configurable per currency |
| `999999` max spin values | All dialogs | Reasonable for now |
| `120` max installments | `purchase_dialog.py:60` | Arbitrary |
| `20` recent events | `dashboard_widget.py:88` | Hardcoded limit |
| `2000-01-01` default start date | `account_summary_widget.py:23` | Arbitrary |
| `1-28` day range | `credit_card_dialog.py:29,33` | Some cards use 29-31 |
| `900x600` window size | `main_window.py:63` | Hardcoded |

---

## Bonus Features (In Code, Not in Specs)

| Feature | Notes |
|---------|-------|
| Counterparty entity | Full CRUD, not mentioned in any spec |
| Multi-currency support | Currency selector on events, specs assume BRL only |
| update_purchase use case | Editing purchases, no spec mentions editing |
| Category Breakdown with income/expenses/net | Specs only describe expense-focused breakdown |
| Account Summary with date range | Specs say "display balances" without date filter |

---

## Summary

| Category | Count |
|----------|-------|
| HIGH bugs | 2 |
| MEDIUM bugs | 8 |
| LOW bugs | 1 |
| Missing MVP features | 8 |
| Future features (deferred) | 7 |
| Unused imports | 8 locations |
| Unused classes | 1 |
| Hardcoded values | 7 |
| Bonus features | 5 |
