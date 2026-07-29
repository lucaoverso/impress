#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
            body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 300),
            action_url TEXT NOT NULL DEFAULT '/',
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK(priority IN ('normal', 'urgent')),
            source_type TEXT NOT NULL DEFAULT '',
            source_id TEXT NOT NULL DEFAULT '',
            dedupe_key TEXT,
            batch_id TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_by_user_id INTEGER,
            available_at TEXT NOT NULL DEFAULT (datetime('now')),
            read_at TEXT,
            cancelled_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(recipient_user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by_user_id) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_recipient_dedupe
        ON notifications(recipient_user_id, dedupe_key)
        WHERE dedupe_key IS NOT NULL AND dedupe_key <> '';

        CREATE INDEX IF NOT EXISTS idx_notifications_inbox
        ON notifications(recipient_user_id, cancelled_at, available_at DESC, id DESC);

        CREATE INDEX IF NOT EXISTS idx_notifications_source
        ON notifications(source_type, source_id, available_at);

        CREATE INDEX IF NOT EXISTS idx_notifications_batch
        ON notifications(batch_id, available_at);

        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
            failures INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_success_at TEXT,
            disabled_at TEXT,
            FOREIGN KEY(user_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user
        ON push_subscriptions(user_id, active);

        CREATE TABLE IF NOT EXISTS notification_push_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'processing', 'sent', 'failed', 'dead')),
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            claimed_at TEXT,
            sent_at TEXT,
            FOREIGN KEY(notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
            FOREIGN KEY(subscription_id) REFERENCES push_subscriptions(id) ON DELETE CASCADE,
            UNIQUE(notification_id, subscription_id)
        );

        CREATE INDEX IF NOT EXISTS idx_notification_push_due
        ON notification_push_deliveries(status, next_attempt_at, id);
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.executescript(
        """
        DROP TABLE IF EXISTS notification_push_deliveries;
        DROP TABLE IF EXISTS push_subscriptions;
        DROP TABLE IF EXISTS notifications;
        """
    )
    conn.commit()
