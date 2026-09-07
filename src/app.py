from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate, QTime, Qt, QSize
from PyQt6.QtGui import QColor, QTextCharFormat, QIcon
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (
    QApplication, QCalendarWidget, QComboBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)

from .database import PostRepository
from .exporters import export_day_pdf, export_post_bundle, import_excel
from .models import ScheduledPost, PLATFORMS, POST_TYPES




class MercuryScheduler(QMainWindow):
    def __init__(self, db_path: Path, export_dir: Path):
        super().__init__()
        first_run = not db_path.exists()
        self.repo = PostRepository(db_path)
        if first_run:
            self.repo.seed_demo()
        self.export_dir = export_dir
        self.editing_post_id: int | None = None
        self.media_paths: list[str] = []
        self.display_image = ""
        self.setWindowTitle("Mercury — Social Media Planner")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "assets/mercury.svg")))
        self.resize(1220, 790)
        self.setMinimumSize(980, 680)
        self._set_style()
        self._build_ui()
        self.calendar.setSelectedDate(QDate.currentDate())
        self.refresh()

    def _set_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #F6F2EB; }
            QLabel { color: #382949; }
            QFrame#card { background: white; border: 1px solid #DDD2C1; border-radius: 10px; }
            QPushButton { background: #674C78; color: white; border: none; border-radius: 7px; padding: 9px 12px; font-weight: 600; }
            QPushButton:hover { background: #50385F; }
            QPushButton#secondary { background: #EDE5D8; color: #493C4F; }
            QLineEdit, QTextEdit, QComboBox, QTimeEdit { color: #382949; background: white; border: 1px solid #cfd8e7; border-radius: 6px; padding: 7px; }
            QListWidget { color: #382949; background: white; border: 1px solid #dce3ee; border-radius: 8px; }
            QCalendarWidget { background: white; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background: #674C78; }
            QCalendarWidget QAbstractItemView { selection-background-color: #674C78; selection-color: white; }
            QCalendarWidget QToolButton { color: white; background: #674C78; }
        """)

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        outer = QVBoxLayout(central); outer.setContentsMargins(18,18,18,18); outer.setSpacing(12)
        header = QHBoxLayout()
        emblem = QSvgWidget(str(Path(__file__).resolve().parents[1] / "assets/mercury.svg"))
        emblem.setFixedSize(58, 58)
        header.addWidget(emblem)
        header.addSpacing(10)
        title_box = QVBoxLayout()
        title = QLabel("Mercury"); title.setStyleSheet("font-family: Georgia; font-size: 30px; font-weight: 700; letter-spacing: 3px;")
        sub = QLabel("Messenger of your next story. Plan locally. Publish with intention."); sub.setStyleSheet("color:#786C7E;")
        title_box.addWidget(title); title_box.addWidget(sub); header.addLayout(title_box); header.addStretch()
        demo_btn = QPushButton("Reset Demo Data"); demo_btn.setObjectName("secondary"); demo_btn.clicked.connect(self.reset_demo)
        import_btn = QPushButton("Import Excel"); import_btn.clicked.connect(self.import_excel)
        pdf_btn = QPushButton("Export Day PDF"); pdf_btn.clicked.connect(self.export_pdf)
        header.addWidget(demo_btn); header.addWidget(import_btn); header.addWidget(pdf_btn)
        outer.addLayout(header)
        ornament = QLabel("┐┌┐┌┐┌    •    CONTENT IN MOTION    •    ┐┌┐┌┐┌")
        ornament.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ornament.setStyleSheet("color: #967347; font-size: 10px; letter-spacing: 2px; padding: 5px; border-top: 1px solid #D9CBB4; border-bottom: 1px solid #D9CBB4;")
        outer.addWidget(ornament)

        content = QHBoxLayout(); content.setSpacing(14); outer.addLayout(content, 1)
        left = QFrame(); left.setObjectName("card"); left_layout = QVBoxLayout(left); left_layout.setContentsMargins(14,14,14,14)
        content.addWidget(left, 3)
        self.calendar = QCalendarWidget(); self.calendar.selectionChanged.connect(self.refresh)
        left_layout.addWidget(self.calendar, 2)
        posts_label = QLabel("Scheduled content"); posts_label.setStyleSheet("font-size:16px;font-weight:700;")
        left_layout.addWidget(posts_label)
        self.posts_list = QListWidget(); self.posts_list.setWordWrap(True); self.posts_list.itemDoubleClicked.connect(self.edit_selected)
        left_layout.addWidget(self.posts_list, 3)
        row = QHBoxLayout()
        edit_btn = QPushButton("Edit Selected"); edit_btn.setObjectName("secondary"); edit_btn.clicked.connect(self.edit_selected)
        delete_btn = QPushButton("Delete Selected"); delete_btn.setObjectName("secondary"); delete_btn.clicked.connect(self.delete_selected)
        export_btn = QPushButton("Export Selected"); export_btn.clicked.connect(self.export_selected)
        row.addWidget(edit_btn); row.addWidget(delete_btn); row.addStretch(); row.addWidget(export_btn)
        left_layout.addLayout(row)

        right = QFrame(); right.setObjectName("card"); right.setMaximumWidth(420)
        form = QFormLayout(right); form.setContentsMargins(16,16,16,16); form.setSpacing(11)
        heading = QLabel("Create / edit post"); heading.setStyleSheet("font-size:17px;font-weight:750;")
        form.addRow(heading)
        self.platform = QComboBox(); self.platform.addItems(PLATFORMS); form.addRow("Platform", self.platform)
        self.post_type = QComboBox(); self.post_type.addItems(POST_TYPES); self.post_type.currentTextChanged.connect(self.update_type_fields); form.addRow("Content type", self.post_type)
        self.title_input = QLineEdit(); self.title_input.setPlaceholderText("Short internal title"); form.addRow("Title", self.title_input)
        self.time_input = QTimeEdit(QTime.currentTime()); self.time_input.setDisplayFormat("hh:mm AP"); form.addRow("Time", self.time_input)
        self.url_input = QLineEdit(); self.url_input.setPlaceholderText("Optional link for stories / campaigns"); form.addRow("URL", self.url_input)
        self.message_input = QTextEdit(); self.message_input.setMaximumHeight(80); self.message_input.setPlaceholderText("Story message"); form.addRow("Story message", self.message_input)
        self.description_input = QTextEdit(); self.description_input.setMaximumHeight(120); self.description_input.setPlaceholderText("Caption / post copy"); form.addRow("Description", self.description_input)
        self.media_label = QLabel("No media selected"); self.media_label.setWordWrap(True); self.media_label.setStyleSheet("color:#786C7E;")
        media_row = QHBoxLayout(); media_btn = QPushButton("Add Media"); media_btn.setObjectName("secondary"); media_btn.clicked.connect(self.add_media)
        clear_media_btn = QPushButton("Clear"); clear_media_btn.setObjectName("secondary"); clear_media_btn.clicked.connect(self.clear_media)
        media_row.addWidget(media_btn); media_row.addWidget(clear_media_btn)
        form.addRow("Media", media_row); form.addRow("", self.media_label)
        save_btn = QPushButton("Save Schedule"); save_btn.clicked.connect(self.save_post); form.addRow(save_btn)
        cancel_btn = QPushButton("Clear Form"); cancel_btn.setObjectName("secondary"); cancel_btn.clicked.connect(self.clear_form); form.addRow(cancel_btn)
        content.addWidget(right, 2)
        self.update_type_fields()

    def current_date(self) -> str:
        return self.calendar.selectedDate().toString("yyyy-MM-dd")

    def refresh(self):
        self.posts_list.clear()
        posts = self.repo.for_date(self.current_date())
        for post in posts:
            text = f"{post.time}  •  {post.platform}  •  {post.post_type}\n{post.title}"
            item = self._make_item(text, post.id)
            self.posts_list.addItem(item)
        self._mark_calendar_dates()

    def _make_item(self, text: str, post_id: int | None):
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, post_id); item.setSizeHint(QSize(0, 58))
        return item

    def _mark_calendar_dates(self):
        normal = QTextCharFormat(); normal.setBackground(QColor("white"))
        highlight = QTextCharFormat(); highlight.setBackground(QColor("#E9DFEE")); highlight.setForeground(QColor("#50385F"))
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        for date_str in self.repo.date_counts():
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            if qdate.isValid(): self.calendar.setDateTextFormat(qdate, highlight)

    def update_type_fields(self):
        is_story = self.post_type.currentText() == "Story"
        self.url_input.setEnabled(is_story)
        self.message_input.setEnabled(is_story)
        self.description_input.setEnabled(not is_story)

    def add_media(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select media", "", "Media (*.png *.jpg *.jpeg *.webp *.mp4 *.mov)")
        for path in files:
            if path not in self.media_paths: self.media_paths.append(path)
        self._update_media_label()

    def clear_media(self):
        self.media_paths = []; self.display_image = ""; self._update_media_label()

    def _update_media_label(self):
        self.media_label.setText("No media selected" if not self.media_paths else "\n".join(Path(p).name for p in self.media_paths))

    def save_post(self):
        post = ScheduledPost(
            id=self.editing_post_id, date=self.current_date(), time=self.time_input.time().toString("hh:mm AP"),
            platform=self.platform.currentText(), post_type=self.post_type.currentText(), title=self.title_input.text(),
            url=self.url_input.text() if self.post_type.currentText() == "Story" else "",
            story_message=self.message_input.toPlainText() if self.post_type.currentText() == "Story" else "",
            description=self.description_input.toPlainText() if self.post_type.currentText() != "Story" else "", media_paths=list(self.media_paths), display_image=self.display_image,
        )
        try:
            self.repo.save(post)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot save", str(exc)); return
        self.clear_form(); self.refresh()

    def selected_id(self) -> int | None:
        item = self.posts_list.currentItem()
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def edit_selected(self, *_args):
        post_id = self.selected_id()
        if not post_id: return
        post = self.repo.get(post_id)
        if not post: return
        self.editing_post_id = post.id
        self.platform.setCurrentText(post.platform); self.post_type.setCurrentText(post.post_type); self.title_input.setText(post.title)
        self.time_input.setTime(QTime.fromString(post.time, "hh:mm AP")); self.url_input.setText(post.url)
        self.message_input.setPlainText(post.story_message); self.description_input.setPlainText(post.description)
        self.media_paths = list(post.media_paths); self.display_image = post.display_image; self._update_media_label(); self.update_type_fields()

    def delete_selected(self):
        post_id = self.selected_id()
        if not post_id: return
        if QMessageBox.question(self, "Delete post", "Delete the selected scheduled post?") == QMessageBox.StandardButton.Yes:
            self.repo.delete(post_id)
            if self.editing_post_id == post_id:
                self.clear_form()
            self.refresh()

    def export_selected(self):
        post_id = self.selected_id()
        if not post_id: return
        post = self.repo.get(post_id)
        if not post: return
        try:
            folder = export_post_bundle(post, self.export_dir)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc)); return
        QApplication.clipboard().setText(post.content_text())
        QMessageBox.information(self, "Export complete", f"Exported to:\n{folder}\n\nPost text was copied to the clipboard.")

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import schedule", "", "Excel (*.xlsx)")
        if not path: return
        try:
            posts = import_excel(path)
            self.repo.save_many(posts)
        except Exception as exc:
            QMessageBox.warning(self, "Import failed", str(exc)); return
        self.refresh(); QMessageBox.information(self, "Import complete", f"Imported {len(posts)} scheduled posts.")

    def export_pdf(self):
        posts = self.repo.for_date(self.current_date())
        default = self.export_dir / f"Schedule_{self.current_date()}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export day PDF", str(default), "PDF (*.pdf)")
        if not path: return
        try:
            export_day_pdf(posts, path, self.current_date())
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc)); return
        QMessageBox.information(self, "Export complete", f"Daily schedule exported to:\n{path}")

    def clear_form(self):
        self.editing_post_id = None; self.title_input.clear(); self.url_input.clear(); self.message_input.clear(); self.description_input.clear()
        self.time_input.setTime(QTime.currentTime()); self.media_paths = []; self.display_image = ""; self._update_media_label()

    def reset_demo(self):
        if QMessageBox.question(self, "Reset demo", "Replace local schedules with fictional demo data?") == QMessageBox.StandardButton.Yes:
            self.repo.seed_demo(force=True); self.clear_form(); self.refresh()

    def closeEvent(self, event):
        self.repo.close(); event.accept()
