# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-09-17

### Added

- Localization: full English, Portuguese (pt_BR), and Spanish (es) translations across the UI.
- Calendar view with day/week/month modes and a per-day projected balance.
- Product spending analysis with a per-product detail view, plus per-item product tracking on purchases.
- Reusable dashboard widget templates and additional chart widget types.
- A reusable date-range selector shared across the analytics screens.
- Multi-report dashboard tabs.
- Theme customization: premade themes and custom JSON themes, with a restart prompt when the theme changes.
- Chart forecasting: line charts can extrapolate future months, drawn as a dashed forecast tail.
- Hover tooltips on bar and line charts (matching the pie chart) that show each bar's / point's value.

### Changed

- Reworked credit-card debt tracking.
- General UI polish across dialogs and the main window.

### Fixed

- Account Summary and the Dashboard now agree: internal transfers between your own accounts are no longer counted as income or expenses (they still move account balances).
- Credit-card purchases are no longer double-counted (the purchase plus its later card-bill payment) in the Dashboard/Account Summary expense and balance figures.
- The category breakdown/pie no longer includes transfers or credit-card bill payments, which shrinks the misleading "no category" slice and removes double-counting.
- The counterparty breakdown no longer creates phantom zero-value rows for transfers.

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
