#!/usr/bin/env python3
import sqlite3


DEFAULT_SCHEDULE = (
    (1, "AULA", 1, "Aula 1", "07:00", "07:50"),
    (2, "AULA", 2, "Aula 2", "07:50", "08:40"),
    (3, "INTERVALO", None, "Intervalo da manha", "08:40", "09:00"),
    (4, "AULA", 3, "Aula 3", "09:00", "09:50"),
    (5, "AULA", 4, "Aula 4", "09:50", "10:40"),
    (6, "AULA", 5, "Aula 5", "10:40", "11:30"),
    (7, "AULA", 6, "Aula 6", "13:00", "13:50"),
    (8, "AULA", 7, "Aula 7", "13:50", "14:40"),
    (9, "INTERVALO", None, "Intervalo da tarde", "14:40", "15:00"),
    (10, "AULA", 8, "Aula 8", "15:00", "15:50"),
    (11, "AULA", 9, "Aula 9", "15:50", "16:40"),
    (12, "AULA", 10, "Aula 10", "16:40", "17:30"),
    (13, "AULA", 11, "Aula 11", "17:30", "18:20"),
)


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    )
    return cursor.fetchone() is not None


def _seed_empty_schedule(cursor: sqlite3.Cursor) -> None:
    if not _table_exists(cursor, "configuracao_aulas"):
        return
    total = int(cursor.execute("SELECT COUNT(*) FROM configuracao_aulas").fetchone()[0])
    if total > 0 or not _has_global_schedule_data(cursor):
        return
    cursor.executemany(
        """
        INSERT INTO configuracao_aulas (
            ordem_visual, tipo, aula_numero, nome,
            horario_inicio, horario_fim, ativo
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        DEFAULT_SCHEDULE,
    )


def _has_global_schedule_data(cursor: sqlite3.Cursor) -> bool:
    if _table_exists(cursor, "horarios_escolares"):
        columns = {
            str(row[1])
            for row in cursor.execute("PRAGMA table_info(horarios_escolares)").fetchall()
        }
        checks = []
        if "aula_numero" in columns:
            checks.append("CAST(COALESCE(aula_numero, 0) AS INTEGER) >= 6")
        if "faixa_global" in columns:
            checks.append("CAST(COALESCE(faixa_global, 0) AS INTEGER) >= 6")
        if checks:
            query = f"SELECT 1 FROM horarios_escolares WHERE {' OR '.join(checks)} LIMIT 1"
            if cursor.execute(query).fetchone():
                return True

    if not _table_exists(cursor, "turmas"):
        return False
    return cursor.execute(
        """
        SELECT 1
        FROM turmas
        WHERE UPPER(COALESCE(turno, '')) IN ('VESPERTINO', 'VESPERTINO_EM')
          AND aula_inicial >= 6
        LIMIT 1
        """
    ).fetchone() is not None


def _repair_class_windows(cursor: sqlite3.Cursor) -> None:
    if not _table_exists(cursor, "turmas"):
        return
    cursor.execute(
        """
        UPDATE turmas
        SET aula_inicial = 6,
            aula_final = CASE
                WHEN UPPER(COALESCE(turno, '')) = 'VESPERTINO_EM' THEN 11
                ELSE 10
            END
        WHERE UPPER(COALESCE(turno, '')) IN ('VESPERTINO', 'VESPERTINO_EM')
          AND aula_inicial = 1
          AND aula_final = 5
        """
    )


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    _seed_empty_schedule(cursor)
    _repair_class_windows(cursor)
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.commit()
