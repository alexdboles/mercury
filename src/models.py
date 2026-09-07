from __future__ import annotations

from dataclasses import dataclass, field
import json
from datetime import datetime

PLATFORMS = ["Instagram", "Facebook", "LinkedIn", "TikTok", "X / Twitter", "YouTube"]
POST_TYPES = ["Post", "Story", "Reel"]


@dataclass
class ScheduledPost:
    id: int | None
    date: str
    time: str
    platform: str
    post_type: str
    title: str
    url: str = ""
    story_message: str = ""
    description: str = ""
    media_paths: list[str] = field(default_factory=list)
    display_image: str = ""

    def validate(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Post title is required.")
        try:
            if datetime.strptime(self.date, "%Y-%m-%d").strftime("%Y-%m-%d") != self.date:
                raise ValueError
            datetime.strptime(self.time, "%I:%M %p")
        except (TypeError, ValueError):
            raise ValueError("Use a valid YYYY-MM-DD date and hh:mm AM/PM time.") from None
        if self.platform not in PLATFORMS:
            raise ValueError("Choose a supported platform.")
        if self.post_type not in POST_TYPES:
            raise ValueError("Content type must be Post, Story, or Reel.")

    def content_text(self) -> str:
        if self.post_type == "Story":
            return "\n\n".join(part.strip() for part in (self.url, self.story_message) if part.strip())
        return self.description.strip()

    def media_json(self) -> str:
        return json.dumps(self.media_paths, ensure_ascii=False)

    @staticmethod
    def parse_media(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            data = json.loads(value)
            return [str(item) for item in data] if isinstance(data, list) else []
        except json.JSONDecodeError:
            # Backward-compatible fallback for older comma-separated records.
            return [part for part in value.split(",") if part]
