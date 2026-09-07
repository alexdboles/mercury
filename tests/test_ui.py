"""Exercise the actual Qt form without requiring a physical display."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QDate
from unittest.mock import patch
from src.app import MercuryScheduler

class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.qt = QApplication.instance() or QApplication([])
    def test_create_edit_delete_calendar_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'app.db'; w=MercuryScheduler(db,Path(d)/'exports')
            try:
                w.calendar.setSelectedDate(QDate(2027,1,4))
                w.title_input.setText('UI check'); w.save_post()
                self.assertEqual(w.posts_list.count(),1)
                w.posts_list.setCurrentRow(0); w.edit_selected()
                w.title_input.setText('Updated'); w.save_post()
                self.assertEqual(w.repo.for_date('2027-01-04')[0].title,'Updated')
                w.posts_list.setCurrentRow(0);w.edit_selected()
                with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes): w.delete_selected()
                self.assertIsNone(w.editing_post_id)
                for day in w.repo.date_counts():
                    for post in w.repo.for_date(day): w.repo.delete(post.id)
            finally: w.close()
            w=MercuryScheduler(db,Path(d)/'exports')
            try: self.assertEqual(w.repo.date_counts(),{})
            finally: w.close()
