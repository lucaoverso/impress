import sqlite3

from .models import PUBLIC_STATUS


def replace_post_tags(conn: sqlite3.Connection, post_id: int, tags: list[dict]) -> None:
    conn.execute("DELETE FROM blog_post_tags WHERE post_id = ?", (int(post_id),))
    for position, tag in enumerate(tags):
        conn.execute(
            "INSERT OR IGNORE INTO blog_tags (name, slug) VALUES (?, ?)",
            (tag["name"], tag["slug"]),
        )
        row = conn.execute(
            "SELECT id FROM blog_tags WHERE slug = ?", (tag["slug"],)
        ).fetchone()
        conn.execute(
            "INSERT INTO blog_post_tags (post_id, tag_id, position) VALUES (?, ?, ?)",
            (int(post_id), int(row[0]), position),
        )


def attach_tags(conn: sqlite3.Connection, posts: list[dict]) -> list[dict]:
    if not posts:
        return posts
    post_ids = [int(post["id"]) for post in posts]
    placeholders = ",".join("?" for _ in post_ids)
    rows = conn.execute(
        f"""
        SELECT pt.post_id, t.name, t.slug
        FROM blog_post_tags pt
        INNER JOIN blog_tags t ON t.id = pt.tag_id
        WHERE pt.post_id IN ({placeholders})
        ORDER BY pt.post_id, pt.position, t.name
        """,
        post_ids,
    ).fetchall()
    grouped: dict[int, list[dict[str, str]]] = {post_id: [] for post_id in post_ids}
    for row in rows:
        grouped[int(row[0])].append({"name": str(row[1]), "slug": str(row[2])})
    return [{**post, "tags": grouped[int(post["id"])]} for post in posts]


def list_public_tags(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT t.name, t.slug, COUNT(DISTINCT pt.post_id) AS post_count
        FROM blog_tags t
        INNER JOIN blog_post_tags pt ON pt.tag_id = t.id
        INNER JOIN blog_posts p ON p.id = pt.post_id
        WHERE p.status = ? AND p.published_at IS NOT NULL
          AND p.published_at <= datetime('now')
        GROUP BY t.id, t.name, t.slug
        ORDER BY post_count DESC, t.name COLLATE NOCASE
        """,
        (PUBLIC_STATUS,),
    ).fetchall()
    return [dict(row) for row in rows]
