# 💰 Finance Manager

A desktop personal finance manager built with **Python** and **PySide6 (Qt)**, backed by a local **SQLite** database. Track accounts, credit cards, installment purchases, and monthly spending — all running offline on your machine.

## ✨ Features

- **Dashboard** — quick overview of the month, with a fast entry shortcut (`Ctrl+K`)
- **Accounts** — manage multiple accounts and see balances at a glance
- **Credit Cards** — track cards, limits, and statements
- **Installment Purchases** — split purchases into installment plans and follow them over time
- **Categories & Counterparties** — organize transactions by category and who they were with
- **Monthly Summary & Category Breakdown** — visual breakdown of income and expenses
- **Financial Events** — a unified ledger of income, expenses, and transfers

## 🏗️ Architecture

The project follows a **Clean Architecture** style, split into four layers:

```
src/
├── domain/          # Entities, repository interfaces, and business rules
├── application/      # Use cases and DTOs orchestrating the domain
├── infrastructure/    # SQLite repositories, schema, and configuration
└── presentation/      # PySide6 windows, dialogs, and widgets
```

This keeps business logic independent of the UI framework and the storage engine, making each layer easy to test and evolve on its own.

## 🚀 Getting Started

### Requirements

- Python 3.10+
- Linux/macOS/Windows with Qt-compatible display

### Run it

The included launcher script sets up a virtual environment and installs dependencies automatically:

```bash
./finance-manager
```

### Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python src/main.py
```

Your data is stored locally in `~/.finance_manager/finance.db` — nothing leaves your machine.

## 📚 Project Docs

Design notes and specifications used while building the domain model:

- [`Descripton.md`](Descripton.md) — overall description of transactions and events
- [`FinancialEventisDescription.md`](FinancialEventisDescription.md) — financial event model
- [`InvoiceDescription.md`](InvoiceDescription.md) — purchases with multiple items
- [`Installments.md`](Installments.md) — installment plan logic
- [`creditCardEspecification.md`](creditCardEspecification.md) — credit card behavior
- [`AUDIT.md`](AUDIT.md) — post-implementation review and fixes

## 🧰 Tech Stack

- **Python 3**
- **PySide6** (Qt for Python) — desktop UI
- **SQLite** — local, file-based storage

## 🤝 Contributing

This is a personal project, but issues and suggestions are welcome!
