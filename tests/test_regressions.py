from pathlib import Path
import tempfile
import unittest
import pandas as pd
from src.models import ScheduledPost
from src.database import PostRepository
from src.exporters import import_excel, export_post_bundle, export_day_pdf

class RegressionTests(unittest.TestCase):
    def test_blank_optional_excel_cells_are_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'input.xlsx'
            pd.DataFrame([{'Date':'2026-09-07','Time':'14:30','Type':'Post','Title':'Demo','Platform':None,'Description':None}]).to_excel(p,index=False)
            post = import_excel(p)[0]
            self.assertEqual((post.platform, post.description, post.time), ('Instagram', '', '02:30 PM'))

    def test_invalid_import_reports_row(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.xlsx'
            pd.DataFrame([{'Date':'2026-09-07','Time':'14:30','Type':'Unknown','Title':'Demo'}]).to_excel(p,index=False)
            with self.assertRaisesRegex(ValueError, 'Row 2'):
                import_excel(p)

    def test_validation_and_atomic_import(self):
        with tempfile.TemporaryDirectory() as d:
            repo=PostRepository(Path(d)/'test.db')
            try:
                good=ScheduledPost(None,'2026-09-07','09:00 AM','Instagram','Post','Good')
                bad=ScheduledPost(None,'2026-02-30','09:00 AM','Instagram','Post','Bad')
                with self.assertRaises(ValueError): repo.save_many([good,bad])
                self.assertEqual(repo.date_counts(),{})
                repo.save_many([good])
                self.assertEqual(repo.date_counts(),{'2026-09-07':1})
                with self.assertRaisesRegex(ValueError,'no longer exists'):
                    repo.save(ScheduledPost(999,'2026-09-07','09:00 AM','Instagram','Post','Deleted'))
            finally: repo.close()

    def test_exports_preserve_colliding_media_and_previous_bundles(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for folder, text in [('a','first'),('b','second')]:
                (root/folder).mkdir(); (root/folder/'same.jpg').write_text(text)
            post=ScheduledPost(None,'2026-09-07','09:00 AM','Instagram','Story','Demo',url='https://example.com',story_message='Hello', description='Stale caption',media_paths=[str(root/'a/same.jpg'),str(root/'b/same.jpg')])
            a=export_post_bundle(post,root/'exports');b=export_post_bundle(post,root/'exports')
            self.assertNotEqual(a,b)
            self.assertEqual((a/'same.jpg').read_text(),'first')
            self.assertEqual((a/'same-2.jpg').read_text(),'second')
            self.assertEqual((a/'content.txt').read_text(),'https://example.com\n\nHello')
            post.media_paths.append(str(root/'missing.jpg'))
            with self.assertRaisesRegex(ValueError,'Missing media'): export_post_bundle(post,root/'exports')

    def test_pdf_accepts_markup_and_long_text(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pdf'
            export_day_pdf([ScheduledPost(None,'2026-09-07','09:00 AM','Instagram','Post','<b> & ' * 20,description='Caption ' * 60)],p,'<demo> & test')
            self.assertTrue(p.read_bytes().startswith(b'%PDF'))
