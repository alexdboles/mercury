from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.exporters import export_day_pdf, import_excel, safe_slug
from src.models import ScheduledPost


class ExporterTests(unittest.TestCase):
    def test_safe_slug(self):
        self.assertEqual(safe_slug("Instagram: launch / test"), "Instagram-launch-test")

    def test_import_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schedule.xlsx"
            pd.DataFrame([{"Date":"2026-09-07","Time":"09:00 AM","Platform":"LinkedIn","Type":"Post","Title":"Demo","Description":"Text"}]).to_excel(path, index=False)
            posts = import_excel(path)
            self.assertEqual(posts[0].platform, "LinkedIn")
            self.assertEqual(posts[0].title, "Demo")

    def test_pdf_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "day.pdf"
            export_day_pdf([ScheduledPost(None,"2026-09-07","09:00 AM","Instagram","Post","Demo",description="Text")], path, "2026-09-07")
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 100)


if __name__ == "__main__": unittest.main()
