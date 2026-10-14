def create_tables(conn):
    conn.executescript("""
        PRAGMA foreign_keys=OFF;

        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            parent_id TEXT,
            is_investment INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            initial_balance REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS counterparties (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS credit_cards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            issuer TEXT NOT NULL,
            credit_limit REAL NOT NULL,
            closing_day INTEGER NOT NULL,
            due_day INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS financial_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            category_id TEXT,
            account_id TEXT,
            destination_account_id TEXT,
            credit_card_id TEXT,
            counterparty_id TEXT,
            currency TEXT NOT NULL DEFAULT 'BRL',
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id),
            FOREIGN KEY(destination_account_id) REFERENCES accounts(id),
            FOREIGN KEY(credit_card_id) REFERENCES credit_cards(id),
            FOREIGN KEY(counterparty_id) REFERENCES counterparties(id)
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id TEXT PRIMARY KEY,
            financial_event_id TEXT NOT NULL UNIQUE,
            total_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            credit_card_id TEXT,
            counterparty_id TEXT,
            invoice_date TEXT,
            notes TEXT,
            FOREIGN KEY(financial_event_id) REFERENCES financial_events(id),
            FOREIGN KEY(credit_card_id) REFERENCES credit_cards(id),
            FOREIGN KEY(counterparty_id) REFERENCES counterparties(id)
        );

        CREATE TABLE IF NOT EXISTS purchase_items (
            id TEXT PRIMARY KEY,
            purchase_id TEXT NOT NULL,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            category_id TEXT,
            product_id TEXT,
            FOREIGN KEY(purchase_id) REFERENCES purchases(id),
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS installment_plans (
            id TEXT PRIMARY KEY,
            purchase_id TEXT NOT NULL,
            total_amount REAL NOT NULL,
            installment_count INTEGER NOT NULL,
            created_at TEXT,
            remainder_on_first INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(purchase_id) REFERENCES purchases(id)
        );

        CREATE TABLE IF NOT EXISTS installments (
            id TEXT PRIMARY KEY,
            installment_plan_id TEXT NOT NULL,
            installment_number INTEGER NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(installment_plan_id) REFERENCES installment_plans(id)
        );

        CREATE TABLE IF NOT EXISTS dashboard_widgets (
            id TEXT PRIMARY KEY,
            dashboard_id TEXT NOT NULL DEFAULT 'default',
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            grid_row INTEGER NOT NULL,
            grid_col INTEGER NOT NULL,
            grid_row_span INTEGER NOT NULL DEFAULT 1,
            grid_col_span INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0,
            config_json TEXT NOT NULL DEFAULT '{}',
            source_preset_id TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard_id ON dashboard_widgets(dashboard_id);

        CREATE TABLE IF NOT EXISTS dashboard_reports (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            context TEXT NOT NULL DEFAULT 'finance',
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS dashboard_widget_templates (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            row_span INTEGER NOT NULL DEFAULT 3,
            col_span INTEGER NOT NULL DEFAULT 6,
            context TEXT NOT NULL DEFAULT 'finance',
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS recurring_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            frequency TEXT NOT NULL,
            interval INTEGER NOT NULL DEFAULT 1,
            day_of_month INTEGER,
            weekday INTEGER,
            month INTEGER,
            start_date TEXT NOT NULL,
            end_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            category_id TEXT,
            account_id TEXT,
            destination_account_id TEXT,
            credit_card_id TEXT,
            counterparty_id TEXT,
            currency TEXT NOT NULL DEFAULT 'BRL',
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id),
            FOREIGN KEY(destination_account_id) REFERENCES accounts(id),
            FOREIGN KEY(credit_card_id) REFERENCES credit_cards(id),
            FOREIGN KEY(counterparty_id) REFERENCES counterparties(id)
        );

        CREATE TABLE IF NOT EXISTS recurring_event_skips (
            id TEXT PRIMARY KEY,
            recurring_event_id TEXT NOT NULL,
            occurrence_date TEXT NOT NULL,
            created_at TEXT,
            UNIQUE(recurring_event_id, occurrence_date),
            FOREIGN KEY(recurring_event_id) REFERENCES recurring_events(id)
        );

        CREATE INDEX IF NOT EXISTS idx_recurring_events_is_active ON recurring_events(is_active);
        CREATE INDEX IF NOT EXISTS idx_recurring_events_start_date ON recurring_events(start_date);
        CREATE INDEX IF NOT EXISTS idx_recurring_event_skips_recurring_event_id ON recurring_event_skips(recurring_event_id);

        CREATE TABLE IF NOT EXISTS investments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'BRL',
            ticker TEXT,
            account_id TEXT,
            current_price REAL NOT NULL DEFAULT 0,
            price_updated_at TEXT,
            goal_amount REAL,
            goal_date TEXT,
            yield_rate REAL,
            yield_index TEXT NOT NULL DEFAULT 'prefixed',
            monthly_contribution REAL,
            maturity_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS investment_transactions (
            id TEXT PRIMARY KEY,
            investment_id TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            date TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0,
            fees REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            notes TEXT,
            financial_event_id TEXT,
            FOREIGN KEY(investment_id) REFERENCES investments(id)
        );

        CREATE INDEX IF NOT EXISTS idx_investment_transactions_investment_id
            ON investment_transactions(investment_id);
        CREATE INDEX IF NOT EXISTS idx_investment_transactions_date
            ON investment_transactions(date);

        CREATE TABLE IF NOT EXISTS investment_schedules (
            id TEXT PRIMARY KEY,
            investment_id TEXT NOT NULL,
            amount REAL NOT NULL,
            frequency TEXT NOT NULL,
            interval INTEGER NOT NULL DEFAULT 1,
            start_date TEXT NOT NULL,
            end_date TEXT,
            last_generated_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(investment_id) REFERENCES investments(id)
        );

        CREATE INDEX IF NOT EXISTS idx_investment_schedules_investment_id
            ON investment_schedules(investment_id);

        CREATE TABLE IF NOT EXISTS economic_indicator_values (
            indicator_key TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY(indicator_key, date)
        );

        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            total_invested REAL NOT NULL DEFAULT 0,
            total_market_value REAL NOT NULL DEFAULT 0,
            total_gain REAL NOT NULL DEFAULT 0,
            total_income REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_financial_events_event_date ON financial_events(event_date);
        CREATE INDEX IF NOT EXISTS idx_financial_events_account_id ON financial_events(account_id);
        CREATE INDEX IF NOT EXISTS idx_financial_events_category_id ON financial_events(category_id);
        CREATE INDEX IF NOT EXISTS idx_financial_events_counterparty_id ON financial_events(counterparty_id);

        CREATE INDEX IF NOT EXISTS idx_purchases_credit_card_id ON purchases(credit_card_id);
        CREATE INDEX IF NOT EXISTS idx_purchase_items_purchase_id ON purchase_items(purchase_id);
        CREATE INDEX IF NOT EXISTS idx_installment_plans_purchase_id ON installment_plans(purchase_id);
        CREATE INDEX IF NOT EXISTS idx_installments_installment_plan_id ON installments(installment_plan_id);
        CREATE INDEX IF NOT EXISTS idx_installments_due_date ON installments(due_date);
        CREATE INDEX IF NOT EXISTS idx_installments_status ON installments(status);

        PRAGMA foreign_keys=ON;
    """)
    conn.commit()
    _migrate(conn)

    # destination_account_id/credit_card_id only exist on financial_events after
    # the ALTER TABLE statements above run, so these two indexes must be created
    # afterward — on a pre-existing database that predates those columns, creating
    # them earlier raises "no such column" and aborts initialization entirely.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_financial_events_destination_account_id "
        "ON financial_events(destination_account_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_financial_events_credit_card_id "
        "ON financial_events(credit_card_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_purchases_counterparty_id "
        "ON purchases(counterparty_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_financial_events_recurring_event_id "
        "ON financial_events(recurring_event_id)"
    )
    conn.commit()


def _migrate(conn):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
    )
    if cursor.fetchone():
        conn.execute("DROP TABLE IF EXISTS transactions")
        conn.commit()
    for table in ["invoice_items", "invoices"]:
        cursor = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        )
        if cursor.fetchone():
            conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()

    cursor = conn.execute("PRAGMA table_info(financial_events)")
    columns = [row[1] for row in cursor.fetchall()]
    if "destination_account_id" not in columns:
        conn.execute(
            "ALTER TABLE financial_events ADD COLUMN destination_account_id TEXT"
        )
        conn.commit()
    if "credit_card_id" not in columns:
        conn.execute(
            "ALTER TABLE financial_events ADD COLUMN credit_card_id TEXT"
        )
        conn.commit()
    if "recurring_event_id" not in columns:
        conn.execute(
            "ALTER TABLE financial_events ADD COLUMN recurring_event_id TEXT"
        )
        conn.commit()

    cursor = conn.execute("PRAGMA table_info(purchases)")
    purchase_columns = [row[1] for row in cursor.fetchall()]
    if purchase_columns:
        if "invoice_date" not in purchase_columns:
            conn.execute("ALTER TABLE purchases ADD COLUMN invoice_date TEXT")
            conn.commit()
        if "notes" not in purchase_columns:
            conn.execute("ALTER TABLE purchases ADD COLUMN notes TEXT")
            conn.commit()
        if "counterparty_id" not in purchase_columns:
            conn.execute("ALTER TABLE purchases ADD COLUMN counterparty_id TEXT")
            conn.commit()
        if "merchant_name" in purchase_columns:
            conn.execute("ALTER TABLE purchases DROP COLUMN merchant_name")
            conn.commit()

        # Backfill credit_card_id onto purchase events created before it was
        # tracked directly on financial_events (it used to live only on the
        # purchases row) - account_summary_service needs it on the event
        # itself to exclude credit-card charges from bank account totals.
        conn.execute(
            """UPDATE financial_events
               SET credit_card_id = (
                   SELECT credit_card_id FROM purchases
                   WHERE purchases.financial_event_id = financial_events.id
               )
               WHERE event_type = 'purchase'
                 AND credit_card_id IS NULL
                 AND id IN (
                     SELECT financial_event_id FROM purchases WHERE credit_card_id IS NOT NULL
                 )"""
        )
        conn.commit()

    cursor = conn.execute("PRAGMA table_info(purchase_items)")
    item_columns = [row[1] for row in cursor.fetchall()]
    if item_columns and "product_id" not in item_columns:
        conn.execute("ALTER TABLE purchase_items ADD COLUMN product_id TEXT")
        conn.commit()

    cursor = conn.execute("PRAGMA table_info(installment_plans)")
    plan_columns = [row[1] for row in cursor.fetchall()]
    if plan_columns and "remainder_on_first" not in plan_columns:
        conn.execute(
            "ALTER TABLE installment_plans ADD COLUMN remainder_on_first INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()

    # 'context' namespaces dashboards/templates so the finance and investment
    # dashboards never see each other's reports/templates (added with the
    # customizable Investments screen).
    cursor = conn.execute("PRAGMA table_info(dashboard_reports)")
    report_columns = [row[1] for row in cursor.fetchall()]
    if report_columns and "context" not in report_columns:
        conn.execute(
            "ALTER TABLE dashboard_reports ADD COLUMN context TEXT NOT NULL DEFAULT 'finance'"
        )
        conn.commit()

    cursor = conn.execute("PRAGMA table_info(dashboard_widget_templates)")
    template_columns = [row[1] for row in cursor.fetchall()]
    if template_columns and "context" not in template_columns:
        conn.execute(
            "ALTER TABLE dashboard_widget_templates ADD COLUMN context TEXT NOT NULL DEFAULT 'finance'"
        )
        conn.commit()

    # Savings-box goal fields (Caixinha/Cofrinho) on investments.
    cursor = conn.execute("PRAGMA table_info(investments)")
    investment_columns = [row[1] for row in cursor.fetchall()]
    if investment_columns:
        if "goal_amount" not in investment_columns:
            conn.execute("ALTER TABLE investments ADD COLUMN goal_amount REAL")
            conn.commit()
        if "goal_date" not in investment_columns:
            conn.execute("ALTER TABLE investments ADD COLUMN goal_date TEXT")
            conn.commit()
        if "yield_rate" not in investment_columns:
            conn.execute("ALTER TABLE investments ADD COLUMN yield_rate REAL")
            conn.commit()
        if "yield_index" not in investment_columns:
            conn.execute(
                "ALTER TABLE investments ADD COLUMN yield_index TEXT NOT NULL DEFAULT 'prefixed'"
            )
            conn.commit()
        if "monthly_contribution" not in investment_columns:
            conn.execute("ALTER TABLE investments ADD COLUMN monthly_contribution REAL")
            conn.commit()
        if "maturity_date" not in investment_columns:
            conn.execute("ALTER TABLE investments ADD COLUMN maturity_date TEXT")
            conn.commit()

    # Investment flag on categories: events in a flagged category are treated
    # like investments (balance-only, excluded from income/expense and charts).
    cursor = conn.execute("PRAGMA table_info(categories)")
    category_columns = [row[1] for row in cursor.fetchall()]
    if category_columns and "is_investment" not in category_columns:
        conn.execute("ALTER TABLE categories ADD COLUMN is_investment INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    # Link a contribution transaction back to the finance investment event that
    # created it, so the two stay in sync.
    cursor = conn.execute("PRAGMA table_info(investment_transactions)")
    txn_columns = [row[1] for row in cursor.fetchall()]
    if txn_columns and "financial_event_id" not in txn_columns:
        conn.execute("ALTER TABLE investment_transactions ADD COLUMN financial_event_id TEXT")
        conn.commit()
