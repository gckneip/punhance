# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added

- Top-level mode switch: a "Finance / Investments" toggle at the top of the window swaps between the finance menus (dashboard, events, calendar, accounts, etc.) and a dedicated set of investment menus, keeping each domain's navigation focused.
- Investments mode has four tabs: "Painel" (the customizable analytics dashboard), "Carteira" (holdings management), "Predições" (a full predictions screen), and "Indicadores" (economic indicators with latest-value cards and a history chart).
- Predictions screen: a wider, standalone take on the projection widget — side-by-side cards for invested-now, total invested at the horizon (current plus scheduled contributions), total projected value, and projected gain (value minus invested), an interactive value-projection chart (portfolio total or per asset, with period and asset selectors), a per-holding projected-income table with monthly/annual scheduled investment and an income-by-asset pie, upcoming maturities, value at maturity, and savings-goal ETAs, all on one page.
- Finance events can be investments in a specific holding: the event dialog now offers an "Investment" type with a selector of registered holdings. Logging one debits the account and records a matching contribution on the chosen holding (its value grows); editing or deleting the event keeps that contribution in sync.
- Context-aware primary action: the toolbar's "+ Add" button becomes "Investir" in Investments mode, with Invest / Schedule investment / Redeem actions. Invest and Redeem open a dedicated dialog with inline holding selection, the holding's current position/available balance for context, and a movement-type choice — buy or contribution when investing; sell (quantity × price) or lump-sum withdrawal when redeeming — with quantity-priced rows auto-computing their total. Both movements can flow through a chosen Finance account — investing debits it (an investment outflow), redeeming credits it (income) — defaulting to the holding's linked account, so the cash actually leaves/lands in Finance (or "None" to skip).
- Investment simulator: a "what-if" panel beside the projection chart to layer hypothetical future investments — either a brand-new investment (with its own yield) or extra deposits into an existing holding (reusing its yield) — each with an initial amount, a monthly contribution and a contribution period; the chart overlays a "with simulation" line so the impact is visible, and simulations can be stacked or cleared.
- Investments: track holdings across fixed income, Brazilian stocks/FIIs, crypto, and foreign/other assets, with a full buy/sell/contribution/withdrawal/income transaction history per holding.
- Automatic position math per holding (quantity, average price, market value, income, and gain/loss) plus a portfolio summary of total invested, market value, gain, and income received.
- Manual valuation: update each holding's current price/value to mark it to market.
- Market tab with public Brazilian economic indicators (USD/BRL, SELIC, IPCA, CDI, IGP-M) fetched from the Banco Central do Brasil (BCB) SGS API and cached locally so they remain available offline, with a history line chart.
- Indicator refresh runs off the UI thread so the app stays responsive, and degrades gracefully to cached data when offline.
- Customizable Investments dashboard: the Investments screen is now a fully customizable dashboard (same engine as the main dashboard) — multi-tab reports, Edit-Layout mode, drag-to-move, resizable widgets, add/remove, and a custom chart builder.
- Investment widget types: portfolio stat cards, allocation by asset type (pie/bar), per-holding breakdowns, a holdings table, and portfolio value over time; the economic indicators are now placeable widgets on this dashboard (the separate Market tab was merged in).
- Portfolio value history: the app records a daily portfolio snapshot so the portfolio-value-over-time chart accrues history.
- Holdings management lives in a dedicated "Carteira" tab in Investments mode (add/edit/delete holdings, transactions, schedules, and price updates).
- Savings boxes (Nubank "Caixinha" / Inter "Cofrinho"): a Savings Box asset type with an optional goal amount and target date, goal-progress tracking, and a "Savings goals" dashboard widget showing progress bars per box.
- Per-holding yield: set a yield as a fixed annual % or indexed to CDI/SELIC/IPCA (e.g. "100% CDI", "IPCA + 5%"), resolved against the cached indicators.
- Yield-driven predictions: projected monthly/annual income (per holding and portfolio total), a projected-value-over-time chart, and a projected goal-completion date (ETA) for savings boxes (factoring in an optional planned monthly deposit).
- Maturity dates (vencimento) for fixed-income titles, with an "Upcoming maturities" widget (days remaining) and a "Value at maturity" projection (each title's projected value on its maturity date).
- Interactive "Investment projection" widget: one line per asset projected forward, with an on-screen period selector and asset multi-select (both persisted on the widget).
- Scheduled investments (recurring contributions): daily/weekly/monthly/yearly deposit rules per holding. Past-due occurrences are materialized as real contribution transactions on app open; future ones feed the projection charts. Managed via a "Schedule" action in Manage Holdings.
- Additive index yields: "SELIC +" and "CDI +" spreads (e.g. Tesouro Selic = SELIC + 0.07%), alongside the existing "% of CDI/SELIC" and "IPCA +".
- Full English, Portuguese (pt_BR), and Spanish (es) translations for the new screens.

### Changed

- Savings boxes (Caixinha/Cofrinho) now have their own model instead of borrowing the share-based one for stocks. They live in a dedicated "Caixinhas" tab with box-appropriate columns — current balance, amount contributed, yield (balance minus contributed, in R$ and %), and goal progress — and no longer appear in the "Carteira" assets table. Deposits and withdrawals use a minimal dialog asking only for amount, date, account and a note (no quantity, unit price, or fees, which never applied to a savings box): a deposit raises the balance and contributed total together, a withdrawal lowers both, and an "Update balance" action records the interest the bank actually credited. The add/edit box dialog relabels "current price" as "current balance" and hides the ticker and maturity fields. The global Invest/Redeem action now targets only quantity-priced assets. Existing boxes, deposits, and withdrawals are read as-is — no balances or history are rewritten.
- Investment movements no longer count as monthly income or expenses: buying into a holding and redeeming from one are now treated like transfers — they still change account balances but are excluded from the income/expense totals, category breakdown, and monthly summary. Redemptions use a new "redemption" event type; investments keep the "investment" type, both classified as balance-only movements.
- Savings Rate redefined to measure investing: it is now the net amount put into investments this month (investment/redemption events plus expense/income events in investment-flagged categories, net of redemptions) divided by income — so it reflects how much of your income you actually invested, rather than money merely left unspent.
- Categories can be flagged as investment ("Is investment" in the category dialog): events in a flagged category (and its sub-categories) get the same balance-only treatment — excluded from income/expense totals, the Savings Rate, and category charts, while still moving the account balance. Lets money logged manually under an "Investment" category behave like a real investment.

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
