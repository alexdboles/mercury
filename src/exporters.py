from __future__ import annotations

from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime, time
from xml.sax.saxutils import escape
from typing import Iterable

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from .models import ScheduledPost


def safe_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return value[:80] or "scheduled-post"


def import_excel(path: str | Path) -> list[ScheduledPost]:
    frame = pd.read_excel(path)
    required = {"Date", "Time", "Type", "Title"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(sorted(missing))}")
    posts: list[ScheduledPost] = []
    for index, row in frame.iterrows():
        def cell(key, default=""):
            value = row.get(key)
            return default if pd.isna(value) else str(value).strip()
        if row.isna().all():
            continue
        try:
            if pd.isna(row["Date"]) or pd.isna(row["Time"]):
                raise ValueError("Date and Time are required.")
            date_value = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")
            raw_time = row["Time"]
            if isinstance(raw_time, (datetime, time, pd.Timestamp)):
                time_value = raw_time.strftime("%I:%M %p")
            else:
                time_value = None
                for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S"):
                    try:
                        time_value = datetime.strptime(str(raw_time).strip(), fmt).strftime("%I:%M %p")
                        break
                    except ValueError:
                        pass
                if time_value is None:
                    raise ValueError("Time must be hh:mm AM/PM or HH:MM.")
            post = ScheduledPost(
                id=None, date=date_value, time=time_value,
                platform=cell("Platform", "Instagram") or "Instagram",
                post_type=cell("Type"), title=cell("Title"),
                url=cell("URL"), story_message=cell("Message"), description=cell("Description"),
            )
            post.validate()
            posts.append(post)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Row {index + 2}: {exc}") from exc
    return posts


def export_post_bundle(post: ScheduledPost, root: str | Path) -> Path:
    post.validate()
    sources = [Path(source) for source in post.media_paths]
    missing = [src.name for src in sources if not src.is_file()]
    if missing:
        raise ValueError("Missing media: " + ", ".join(missing))
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # Every export gets its own directory; repeated exports cannot overwrite old bundles.
    folder = Path(tempfile.mkdtemp(prefix=safe_slug(f"{post.date}_{post.platform}_{post.title}") + "-", dir=root))
    try:
        used = {"content.txt"}
        for src in sources:
            name = src.name
            suffix = 2
            while name.casefold() in used:
                name = f"{src.stem}-{suffix}{src.suffix}"
                suffix += 1
            used.add(name.casefold())
            shutil.copy2(src, folder / name)
        (folder / "content.txt").write_text(post.content_text(), encoding="utf-8")
    except Exception:
        shutil.rmtree(folder)
        raise
    return folder


def export_day_pdf(posts: Iterable[ScheduledPost], output_path: str | Path, date_label: str) -> Path:
    posts = list(posts)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = [Paragraph(f"Mercury Content Schedule — {escape(date_label)}", styles["Title"]), Spacer(1, 12)]
    if not posts:
        story.append(Paragraph("No posts scheduled for this date.", styles["BodyText"]))
    else:
        rows = [["Time", "Platform", "Type", "Title", "Content"]]
        for post in posts:
            content = post.content_text() or "—"
            rows.append([Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["BodyText"])
                         for value in (post.time, post.platform, post.post_type, post.title, content[:120])])
        table = Table(rows, colWidths=[60, 65, 45, 135, 235], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#315efb")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#d7dce5")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f9fc")]),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(table)
    doc.build(story)
    return path
