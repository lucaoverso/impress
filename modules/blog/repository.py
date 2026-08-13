from db.core import get_connection

from .models import PUBLIC_STATUS
from . import tag_repository


def _one(row) -> dict | None:
    return dict(row) if row else None


def _many(rows) -> list[dict]:
    return [dict(row) for row in rows]


def create_post(
    *, author_user_id: int, title: str, slug: str, summary: str, body_html: str,
    tags: list[dict] | None = None,
) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO blog_posts (author_user_id, title, slug, summary, body_html)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(author_user_id), title, slug, summary, body_html),
        )
        post_id = int(cursor.lastrowid)
        tag_repository.replace_post_tags(conn, post_id, tags or [])
        conn.commit()
        post = _one(conn.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,)).fetchone())
        return tag_repository.attach_tags(conn, [post])[0] if post else {}
    finally:
        conn.close()


def get_post_by_id(post_id: int) -> dict | None:
    conn = get_connection()
    try:
        post = _one(conn.execute("SELECT * FROM blog_posts WHERE id = ?", (int(post_id),)).fetchone())
        return tag_repository.attach_tags(conn, [post])[0] if post else None
    finally:
        conn.close()


def slug_exists(slug: str, *, exclude_post_id: int | None = None) -> bool:
    conn = get_connection()
    try:
        query = "SELECT 1 FROM blog_posts WHERE slug = ?"
        params: list = [slug]
        if exclude_post_id is not None:
            query += " AND id != ?"
            params.append(int(exclude_post_id))
        return conn.execute(query, params).fetchone() is not None
    finally:
        conn.close()


def list_posts(*, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_connection()
    try:
        where = ""
        params: list = []
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.extend((max(1, int(limit)), max(0, int(offset))))
        rows = conn.execute(
            f"""
            SELECT * FROM blog_posts
            {where}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        return tag_repository.attach_tags(conn, _many(rows))
    finally:
        conn.close()


def update_post(
    post_id: int, *, title: str, slug: str, summary: str, body_html: str,
    tags: list[dict] | None = None,
) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE blog_posts
            SET title = ?, slug = ?, summary = ?, body_html = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (title, slug, summary, body_html, int(post_id)),
        )
        if cursor.rowcount <= 0:
            conn.rollback()
            return None
        tag_repository.replace_post_tags(conn, post_id, tags or [])
        conn.commit()
        post = _one(conn.execute("SELECT * FROM blog_posts WHERE id = ?", (int(post_id),)).fetchone())
        return tag_repository.attach_tags(conn, [post])[0] if post else None
    finally:
        conn.close()


def set_post_status(post_id: int, status: str) -> dict | None:
    conn = get_connection()
    try:
        published_sql = (
            "published_at = COALESCE(published_at, datetime('now')),"
            if status == PUBLIC_STATUS
            else ""
        )
        cursor = conn.execute(
            f"""
            UPDATE blog_posts
            SET status = ?, {published_sql} updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, int(post_id)),
        )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
        post = _one(conn.execute("SELECT * FROM blog_posts WHERE id = ?", (int(post_id),)).fetchone())
        return tag_repository.attach_tags(conn, [post])[0] if post else None
    finally:
        conn.close()


def list_public_posts(*, limit: int = 20, offset: int = 0, tag_slug: str = "") -> list[dict]:
    conn = get_connection()
    try:
        tag_join = "INNER JOIN blog_post_tags pt ON pt.post_id = p.id INNER JOIN blog_tags t ON t.id = pt.tag_id" if tag_slug else ""
        tag_where = "AND t.slug = ?" if tag_slug else ""
        params: list = [PUBLIC_STATUS]
        if tag_slug:
            params.append(tag_slug)
        params.extend((max(1, int(limit)), max(0, int(offset))))
        rows = conn.execute(
            f"""
            SELECT p.*, c.token AS cover_token, c.alt_text AS cover_alt_text, c.caption AS cover_caption
            FROM blog_posts AS p
            LEFT JOIN blog_images AS c ON c.post_id = p.id AND c.is_cover = 1
            {tag_join}
            WHERE p.status = ? AND p.published_at IS NOT NULL
              AND p.published_at <= datetime('now')
              {tag_where}
            ORDER BY p.published_at DESC, p.id DESC
            LIMIT ? OFFSET ?
            """, params,
        ).fetchall()
        return tag_repository.attach_tags(conn, _many(rows))
    finally:
        conn.close()


def get_public_post_by_slug(slug: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT p.*, c.token AS cover_token, c.alt_text AS cover_alt_text, c.caption AS cover_caption
            FROM blog_posts AS p
            LEFT JOIN blog_images AS c ON c.post_id = p.id AND c.is_cover = 1
            WHERE p.slug = ? AND p.status = ? AND p.published_at IS NOT NULL
              AND p.published_at <= datetime('now')
            """,
            (slug, PUBLIC_STATUS),
        ).fetchone()
        post = _one(row)
        return tag_repository.attach_tags(conn, [post])[0] if post else None
    finally:
        conn.close()


def list_public_tags() -> list[dict]:
    conn = get_connection()
    try:
        return tag_repository.list_public_tags(conn)
    finally:
        conn.close()


def create_image(post_id: int, values: dict) -> dict:
    conn = get_connection()
    try:
        if values.get("is_cover"):
            conn.execute("UPDATE blog_images SET is_cover = 0 WHERE post_id = ?", (int(post_id),))
        cursor = conn.execute(
            """
            INSERT INTO blog_images (
                post_id, token, stored_name, thumbnail_name, alt_text, caption,
                width, height, is_cover
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(post_id),
                values["token"],
                values["stored_name"],
                values["thumbnail_name"],
                values["alt_text"],
                values["caption"],
                int(values["width"]),
                int(values["height"]),
                int(bool(values["is_cover"])),
            ),
        )
        image_id = int(cursor.lastrowid)
        conn.commit()
        return (
            _one(conn.execute("SELECT * FROM blog_images WHERE id = ?", (image_id,)).fetchone())
            or {}
        )
    finally:
        conn.close()


def get_image(image_id: int) -> dict | None:
    conn = get_connection()
    try:
        return _one(
            conn.execute("SELECT * FROM blog_images WHERE id = ?", (int(image_id),)).fetchone()
        )
    finally:
        conn.close()


def get_image_by_token(token: str) -> dict | None:
    conn = get_connection()
    try:
        return _one(conn.execute("SELECT * FROM blog_images WHERE token = ?", (token,)).fetchone())
    finally:
        conn.close()


def get_public_image_by_token(token: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT i.*
            FROM blog_images i
            INNER JOIN blog_posts p ON p.id = i.post_id
            WHERE i.token = ?
              AND p.status = ?
              AND p.published_at IS NOT NULL
              AND p.published_at <= datetime('now')
            """,
            (token, PUBLIC_STATUS),
        ).fetchone()
        return _one(row)
    finally:
        conn.close()


def list_images(post_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM blog_images WHERE post_id = ? ORDER BY id", (int(post_id),)
        ).fetchall()
        return _many(rows)
    finally:
        conn.close()


def update_image(image_id: int, *, alt_text: str, caption: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE blog_images SET alt_text = ?, caption = ? WHERE id = ?",
            (alt_text, caption, int(image_id)),
        )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
        return _one(
            conn.execute("SELECT * FROM blog_images WHERE id = ?", (int(image_id),)).fetchone()
        )
    finally:
        conn.close()


def set_cover_image(post_id: int, image_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM blog_images WHERE id = ? AND post_id = ?",
            (int(image_id), int(post_id)),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE blog_images SET is_cover = 0 WHERE post_id = ?", (int(post_id),))
        conn.execute("UPDATE blog_images SET is_cover = 1 WHERE id = ?", (int(image_id),))
        conn.commit()
        return _one(
            conn.execute("SELECT * FROM blog_images WHERE id = ?", (int(image_id),)).fetchone()
        )
    finally:
        conn.close()


def delete_image(image_id: int) -> dict | None:
    conn = get_connection()
    try:
        image = _one(
            conn.execute("SELECT * FROM blog_images WHERE id = ?", (int(image_id),)).fetchone()
        )
        if not image:
            return None
        conn.execute("DELETE FROM blog_images WHERE id = ?", (int(image_id),))
        conn.commit()
        return image
    finally:
        conn.close()
