def create_tables(conn):
    conn.executescript("""
        PRAGMA foreign_keys=OFF;

        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            parent_id TEXT
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
            FOREIGN KEY(purchase_id) REFERENCES purchases(id),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS installment_plans (
            id TEXT PRIMARY KEY,
            purchase_id TEXT NOT NULL,
            total_amount REAL NOT NULL,
            installment_count INTEGER NOT NULL,
            created_at TEXT,
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
