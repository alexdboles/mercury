from pathlib import Path
import tempfile
import unittest

from src.database import PostRepository
from src.models import ScheduledPost


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = PostRepository(Path(self.tmp.name) / "scheduler.db")

    def tearDown(self):
        self.repo.close(); self.tmp.cleanup()

    def test_save_and_read_post(self):
        post = ScheduledPost(None, "2026-09-07", "09:30 AM", "LinkedIn", "Post", "Launch update", description="Demo")
        post_id = self.repo.save(post)
        loaded = self.repo.get(post_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.platform, "LinkedIn")
        self.assertEqual(loaded.title, "Launch update")

    def test_media_paths_are_json_safe(self):
        post = ScheduledPost(None, "2026-09-07", "09:30 AM", "Instagram", "Post", "Media", media_paths=["/tmp/a,b.png", "/tmp/c.png"])
        post_id = self.repo.save(post)
        loaded = self.repo.get(post_id)
        self.assertEqual(loaded.media_paths, ["/tmp/a,b.png", "/tmp/c.png"])

    def test_demo_seed(self):
        self.repo.seed_demo()
        self.assertGreater(sum(self.repo.date_counts().values()), 0)

    def test_delete(self):
        post_id = self.repo.save(ScheduledPost(None, "2026-09-07", "11:00 AM", "Instagram", "Story", "Delete me"))
        self.repo.delete(post_id)
        self.assertIsNone(self.repo.get(post_id))


if __name__ == "__main__": unittest.main()
