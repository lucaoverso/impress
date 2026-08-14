import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS finance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by_user_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL
                CHECK(transaction_type IN ('INCOME', 'EXPENSE')),
            occurred_on TEXT NOT NULL
                CHECK(length(occurred_on) = 10),
            description TEXT NOT NULL
                CHECK(length(trim(description)) BETWEEN 1 AND 180),
            category TEXT NOT NULL
                CHECK(length(trim(category)) BETWEEN 1 AND 100),
            amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
            counterparty TEXT NOT NULL DEFAULT ''
                CHECK(length(counterparty) <= 160),
            notes TEXT NOT NULL DEFAULT ''
                CHECK(length(notes) <= 1000),
            status TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK(status IN ('ACTIVE', 'CANCELED')),
            cancellation_reason TEXT NOT NULL DEFAULT ''
                CHECK(length(cancellation_reason) <= 300),
            canceled_by_user_id INTEGER,
            canceled_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(created_by_user_id) REFERENCES usuarios(id) ON DELETE RESTRICT,
            FOREIGN KEY(canceled_by_user_id) REFERENCES usuarios(id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_finance_transactions_month
        ON finance_transactions(substr(occurred_on, 1, 7), status, occurred_on DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_finance_transactions_category
        ON finance_transactions(category, transaction_type, occurred_on DESC);

        CREATE TABLE IF NOT EXISTS finance_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE CHECK(length(token) = 32),
            stored_name TEXT NOT NULL UNIQUE CHECK(length(stored_name) <= 80),
            original_name TEXT NOT NULL CHECK(length(original_name) BETWEEN 1 AND 255),
            media_type TEXT NOT NULL CHECK(length(media_type) <= 80),
            size_bytes INTEGER NOT NULL CHECK(size_bytes > 0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(transaction_id) REFERENCES finance_transactions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_finance_attachments_transaction
        ON finance_attachments(transaction_id, id);
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP INDEX IF EXISTS idx_finance_attachments_transaction;
        DROP TABLE IF EXISTS finance_attachments;
        DROP INDEX IF EXISTS idx_finance_transactions_category;
        DROP INDEX IF EXISTS idx_finance_transactions_month;
        DROP TABLE IF EXISTS finance_transactions;
        """
    )
    conn.commit()
