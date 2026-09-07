from __future__ import annotations

from pathlib import Path
import sqlite3

from .models import ScheduledPost


SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduled_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    platform TEXT NOT NULL,
    post_type TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    story_message TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    media_paths TEXT NOT NULL DEFAULT '[]',
    display_image TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_posts_date_time ON scheduled_posts(date, time);
CREATE INDEX IF NOT EXISTS idx_posts_platform ON scheduled_posts(platform);
"""


class PostRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def save(self, post: ScheduledPost, *, commit: bool = True) -> int:
        post.validate()
        if post.id is None:
            cur = self.conn.execute(
                """INSERT INTO scheduled_posts
                (date,time,platform,post_type,title,url,story_message,description,media_paths,display_image)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (post.date, post.time, post.platform, post.post_type, post.title.strip(), post.url.strip(),
                 post.story_message.strip(), post.description.strip(), post.media_json(), post.display_image),
            )
            post_id = int(cur.lastrowid)
        else:
            cur = self.conn.execute(
                """UPDATE scheduled_posts SET
                date=?,time=?,platform=?,post_type=?,title=?,url=?,story_message=?,description=?,
                media_paths=?,display_image=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (post.date, post.time, post.platform, post.post_type, post.title.strip(), post.url.strip(),
                 post.story_message.strip(), post.description.strip(), post.media_json(), post.display_image, post.id),
            )
            if cur.rowcount == 0:
                raise ValueError("This post no longer exists. Clear the form to create a new one.")
            post_id = post.id
        if commit:
            self.conn.commit()
        return post_id

    def save_many(self, posts: list[ScheduledPost]) -> None:
        # Validate every row before writing, then import all rows in one transaction.
        for post in posts:
            post.validate()
        with self.conn:
            for post in posts:
                self.save(post, commit=False)

    def delete(self, post_id: int) -> None:
        self.conn.execute("DELETE FROM scheduled_posts WHERE id=?", (post_id,))
        self.conn.commit()

    def get(self, post_id: int) -> ScheduledPost | None:
        row = self.conn.execute("SELECT * FROM scheduled_posts WHERE id=?", (post_id,)).fetchone()
        return self._row_to_post(row) if row else None

    def for_date(self, date_str: str) -> list[ScheduledPost]:
        rows = self.conn.execute(
            "SELECT * FROM scheduled_posts WHERE date=?",
            (date_str,),
        ).fetchall()
        posts = [self._row_to_post(r) for r in rows]

        def sort_key(post: ScheduledPost):
            from datetime import datetime
            try:
                parsed = datetime.strptime(post.time, "%I:%M %p")
                return (parsed.hour, parsed.minute, post.platform.lower(), post.title.lower())
            except ValueError:
                return (99, 99, post.platform.lower(), post.title.lower())

        return sorted(posts, key=sort_key)

    def date_counts(self) -> dict[str, int]:
        return {row["date"]: row["count"] for row in self.conn.execute(
            "SELECT date, COUNT(*) AS count FROM scheduled_posts GROUP BY date"
        )}

    def seed_demo(self, force: bool = False) -> None:
        count = self.conn.execute("SELECT COUNT(*) FROM scheduled_posts").fetchone()[0]
        if count and not force:
            return
        if force:
            self.conn.execute("DELETE FROM scheduled_posts")
        from datetime import date, timedelta
        today = date.today()
        demos = [
            (today.isoformat(), "10:00 AM", "Instagram", "Post", "Product spotlight", "", "", "Highlight a new feature with a short customer-focused caption."),
            ((today + timedelta(days=1)).isoformat(), "02:00 PM", "LinkedIn", "Post", "Behind the build", "", "", "Share a short development update and lessons learned."),
            ((today + timedelta(days=2)).isoformat(), "06:30 PM", "Instagram", "Reel", "Quick demo reel", "", "", "Publish a concise walkthrough of the latest project milestone."),
            ((today + timedelta(days=4)).isoformat(), "09:00 AM", "Facebook", "Post", "Community update", "", "", "Share this week's announcement and invite feedback."),
            ((today + timedelta(days=6)).isoformat(), "05:00 PM", "Instagram", "Story", "Launch reminder", "https://example.com/demo", "New demo is live — take a look.", ""),
        ]
        for d in demos:
            self.save(ScheduledPost(None, *d))
        self.conn.commit()

    @staticmethod
    def _row_to_post(row: sqlite3.Row) -> ScheduledPost:
        return ScheduledPost(
            id=row["id"], date=row["date"], time=row["time"], platform=row["platform"],
            post_type=row["post_type"], title=row["title"], url=row["url"],
            story_message=row["story_message"], description=row["description"],
            media_paths=ScheduledPost.parse_media(row["media_paths"]), display_image=row["display_image"],
        )
