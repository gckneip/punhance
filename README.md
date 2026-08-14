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

## 📥 Download

No need to clone the repo or install Python — grab a ready-to-run build from the [latest release](https://github.com/gckneip/punhance/releases/latest):

[![Download for Linux](https://img.shields.io/badge/Download-Linux-blue?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/gckneip/punhance/releases/latest/download/finance-manager-linux)
[![Download for Windows](https://img.shields.io/badge/Download-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/gckneip/punhance/releases/latest/download/finance-manager-windows.exe)

- **Linux:** download `finance-manager-linux`, then `chmod +x finance-manager-linux` and run it (`./finance-manager-linux`). GitHub doesn't preserve the executable bit on download, so this step is required.
- **Windows:** download `finance-manager-windows.exe` and run it. Since the executable isn't code-signed, Windows SmartScreen may show a warning the first time — click **More info → Run anyway**.

Builds are generated automatically for every tagged release via GitHub Actions (see [`.github/workflows/release.yml`](.github/workflows/release.yml)).

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

## 🚀 Running from Source

Prefer to run from source instead of the prebuilt binaries above? Here's how.

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
