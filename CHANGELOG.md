# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-09-10

First release. Everything below shipped as part of this initial build.

### Added

- Core ledger: accounts, categories (with subcategories), counterparties, and financial events (income, expense, transfer, purchase, card payment, loan payment, investment, refund).
- Purchases with per-item categories, and automatic installment plans for credit card purchases.
- Credit cards, with per-card statement/installment tracking.
- Recurring events: create a recurring rule once and have future occurrences generated lazily, with the ability to confirm or skip each one.
- A fully customizable Dashboard with premade and custom widgets.
- Bidirectional HomeBank (`.xhb`) import/export: import a HomeBank file into this app (accounts, categories, payees, transactions, transfers, splits, scheduled transactions) via a preview step that shows counts and warnings before anything is written, or export this app's data into a `.xhb` file HomeBank can open directly.
- A Settings dialog, including a switchable Tabs/Sidebar navigation style.
- Icons throughout the main window (QtAwesome).
- Inline creation of a counterparty directly from the Add Purchase dialog.
- Editing of financial events and purchases (including per-item categories) from the Dashboard and Events tab, plus deleting events from the Dashboard.
- Automated release pipeline: tagged pushes (`vX.Y.Z`) build Linux and Windows binaries via GitHub Actions and publish them to a GitHub Release.

### Changed

- The toolbar's individual create buttons were consolidated into a single "+ Add" menu.
- Credit card purchases always get an installment plan now, not just split purchases.
- A purchase's item categories roll up into its financial event's category automatically.
- Installment plan rounding remainders can land on the first installment instead of always the last.
