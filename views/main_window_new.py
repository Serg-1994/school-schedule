import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QListWidget, QCalendarWidget,
    QHBoxLayout, QWidget, QVBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QGridLayout, QTabWidget, QFormLayout,
    QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox, QListWidgetItem
)
from PyQt6.QtGui import QPainter, QBrush, QColor, QPalette
from PyQt6.QtCore import QDate, Qt
from models.teacher import Teacher
from models.school_class import Class
from models.subject import Subject
from models.schedule import Schedule
from controllers.main_controller import MainController
import json


class ScheduleCalendar(QCalendarWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.teacher_id = None
        self.lesson_counts = {}
        self.currentPageChanged.connect(self._on_page_changed)

    def set_teacher_id(self, teacher_id):
        self.teacher_id = teacher_id
        self.update_lesson_counts()

    def update_lesson_counts(self):
        if not self.teacher_id:
            self.lesson_counts = {}
            self.update()
            return
        year = self.yearShown()
        month = self.monthShown()
        mw = self.main_window
        if (self.teacher_id not in mw.lesson_cache or
                year not in mw.lesson_cache[self.teacher_id] or
                month not in mw.lesson_cache[self.teacher_id][year]):
            mw.load_lesson_counts_for_teacher(self.teacher_id, year, month)
        self.lesson_counts = mw.lesson_cache[self.teacher_id][year][month]
        self.update()

    def _on_page_changed(self, year, month):
        mw = self.main_window
        mw.current_year = year
        mw.current_month = month
        mw.load_all_lesson_counts()
        self.update_lesson_counts()
        mw.refresh_teacher_info()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        count = self.lesson_counts.get(date, 0)
        if count:
            painter.save()
            painter.setPen(Qt.GlobalColor.darkRed)
            painter.setBrush(QColor(255, 230, 100, 200))
            text_rect = rect.adjusted(rect.width() - 22, rect.height() - 22, -1, -1)
            painter.drawRoundedRect(text_rect, 3, 3)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(count))
            painter.restore()


class TeacherDialog(QDialog):
    def __init__(self, teacher=None, parent=None):
        super().__init__(parent)
        self.teacher = teacher
        self.setWindowTitle("Редактировать учителя" if teacher else "Новый учитель")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(teacher.name if teacher else "")
        self.spec_edit = QLineEdit(", ".join(teacher.specialization) if teacher else "")
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(0, 200)
        self.rate_spin.setValue(int(teacher.rate) if teacher else 18)

        layout.addRow("ФИО:", self.name_edit)
        layout.addRow("Предметы (через запятую):", self.spec_edit)
        layout.addRow("Ставка (часов/мес):", self.rate_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_teacher(self):
        name = self.name_edit.text().strip()
        spec = [s.strip() for s in self.spec_edit.text().split(",") if s.strip()]
        rate = self.rate_spin.value()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО учителя.")
            return None
        if self.teacher:
            self.teacher.name = name
            self.teacher.specialization = spec
            self.teacher.rate = rate
            return self.teacher
        return Teacher(name=name, specialization=spec, rate=rate)


class ClassDialog(QDialog):
    def __init__(self, cls=None, parent=None):
        super().__init__(parent)
        self.cls = cls
        self.setWindowTitle("Редактировать класс" if cls else "Новый класс")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(cls.name if cls else "")
        layout.addRow("Название:", self.name_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_class(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название класса.")
            return None
        if self.cls:
            self.cls.name = name
            return self.cls
        return Class(name=name)


class SubjectDialog(QDialog):
    def __init__(self, subj=None, parent=None):
        super().__init__(parent)
        self.subj = subj
        self.setWindowTitle("Редактировать предмет" if subj else "Новый предмет")
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(subj.name if subj else "")
        layout.addRow("Название:", self.name_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_subject(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название предмета.")
            return None
        if self.subj:
            self.subj.name = name
            return self.subj
        return Subject(name=name)


class LessonDialog(QDialog):
    def __init__(self, date, teacher_id, parent=None):
        super().__init__(parent)
        self.date = date
        self.teacher_id = teacher_id
        teacher = Teacher.get_by_id(teacher_id)
        teacher_name = teacher.name if teacher else str(teacher_id)
        self.setWindowTitle(
            f"Расписание: {teacher_name}  —  {date.toString('dd.MM.yyyy')}"
        )

        self.subject_combos = []
        self.class_combos = []
        self.status_combos = []

        subjects = Subject.get_all()
        classes = Class.get_all()

        grid = QGridLayout()
        grid.addWidget(QLabel("Урок"), 0, 0)
        grid.addWidget(QLabel("Предмет"), 0, 1)
        grid.addWidget(QLabel("Класс"), 0, 2)
        grid.addWidget(QLabel("Статус"), 0, 3)
        grid.addWidget(QLabel("Очистить"), 0, 4)

        for i in range(1, 9):
            grid.addWidget(QLabel(f"{i}"), i, 0)

            subj_combo = QComboBox()
            subj_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            subj_combo.setMinimumWidth(140)
            subj_combo.addItem("—", None)
            for s in subjects:
                subj_combo.addItem(s.name, s.id)
            grid.addWidget(subj_combo, i, 1)
            self.subject_combos.append(subj_combo)

            cls_combo = QComboBox()
            cls_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            cls_combo.setMinimumWidth(120)
            cls_combo.addItem("—", None)
            for c in classes:
                cls_combo.addItem(c.name, c.id)
            grid.addWidget(cls_combo, i, 2)
            self.class_combos.append(cls_combo)

            status_combo = QComboBox()
            status_combo.addItem("Работает", "работает")
            status_combo.addItem("На замене", "на замене")
            status_combo.addItem("Болеет", "болеет")
            status_combo.addItem("Отсутствует", "отсутствует")
            grid.addWidget(status_combo, i, 3)
            self.status_combos.append(status_combo)

            clear_btn = QPushButton("✕")
            clear_btn.setFixedWidth(30)
            clear_btn.clicked.connect(lambda checked, row=i - 1: self.clear_row(row))
            grid.addWidget(clear_btn, i, 4)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_schedule)
        grid.addWidget(save_btn, 9, 0, 1, 5)

        self.setMinimumWidth(680)
        self.setLayout(grid)
        self._load_existing()

    def _load_existing(self):
        date_str = self.date.toString('yyyy-MM-dd')
        existing = Schedule.get_by_date_and_teacher(date_str, self.teacher_id)
        for sched in existing:
            idx = sched.lesson_number - 1
            if 0 <= idx < 8:
                self.subject_combos[idx].setCurrentIndex(
                    self.subject_combos[idx].findData(sched.subject_id)
                )
                self.class_combos[idx].setCurrentIndex(
                    self.class_combos[idx].findData(sched.class_id)
                )
                self.status_combos[idx].setCurrentIndex(
                    self.status_combos[idx].findData(sched.status)
                )

    def save_schedule(self):
        date_str = self.date.toString('yyyy-MM-dd')

        # Удаляем старые записи этого дня для учителя
        for sched in Schedule.get_by_date_and_teacher(date_str, self.teacher_id):
            sched.delete()

        for i in range(8):
            subj_id = self.subject_combos[i].currentData()
            cls_id = self.class_combos[i].currentData()
            if not subj_id or not cls_id:
                continue

            lesson_number = i + 1
            status = self.status_combos[i].currentData() or "работает"

            # Проверка конфликта учителя
            teacher_conflict = Schedule.get_conflicting_teacher_entry(
                self.teacher_id, date_str, lesson_number
            )
            if teacher_conflict and teacher_conflict[2] != cls_id:
                conflict_class = Class.get_by_id(teacher_conflict[2])
                conflict_name = conflict_class.name if conflict_class else str(teacher_conflict[2])
                teacher = Teacher.get_by_id(self.teacher_id)
                result = QMessageBox.question(
                    self,
                    "Конфликт учителя",
                    f"Учитель {teacher.name} уже назначен на урок {lesson_number} "
                    f"({date_str}) для класса {conflict_name}.\n"
                    "Назначить на два класса одновременно?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result != QMessageBox.StandardButton.Yes:
                    return

            # Проверка конфликта класса
            class_conflict = Schedule.get_conflicting_class_entry(cls_id, date_str, lesson_number)
            if class_conflict and class_conflict[1] != self.teacher_id:
                conflict_teacher = Teacher.get_by_id(class_conflict[1])
                conflict_name = conflict_teacher.name if conflict_teacher else str(class_conflict[1])
                cls = Class.get_by_id(cls_id)
                QMessageBox.critical(
                    self,
                    "Конфликт класса",
                    f"Класс {cls.name} уже занят на урок {lesson_number} "
                    f"({date_str}) у учителя {conflict_name}."
                )
                return

            Schedule(
                teacher_id=self.teacher_id,
                class_id=cls_id,
                subject_id=subj_id,
                date=date_str,
                lesson_number=lesson_number,
                status=status
            ).save()

        self.accept()

    def clear_row(self, row):
        if 0 <= row < 8:
            self.subject_combos[row].setCurrentIndex(0)
            self.class_combos[row].setCurrentIndex(0)
            self.status_combos[row].setCurrentIndex(0)


class ScheduleReassignmentDialog(QDialog):
    def __init__(self, object_type, object_to_delete, schedules, parent=None):
        super().__init__(parent)
        self.object_type = object_type
        self.object_to_delete = object_to_delete
        self.schedules = schedules

        title = (
            f"Переназначить уроки учителя: {object_to_delete.name}"
            if object_type == 'teacher'
            else f"Переназначить уроки класса: {object_to_delete.name}"
        )
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        note = (
            "Зелёным выделены учителя с подходящей специализацией. "
            "Красным — без специализации по предмету."
            if object_type == 'teacher'
            else "Выберите новый класс для каждого урока."
        )
        layout.addWidget(QLabel(note))

        self.replacement_combos = {}

        if object_type == 'teacher':
            self.global_options = [t for t in Teacher.get_all() if t.id != object_to_delete.id]
        else:
            self.global_options = [c for c in Class.get_all() if c.id != object_to_delete.id]

        grid = QGridLayout()
        headers = ["Дата", "Урок", "Класс" if object_type == 'teacher' else "Учитель",
                   "Предмет", "Статус", "Замена"]
        for col, h in enumerate(headers):
            grid.addWidget(QLabel(f"<b>{h}</b>"), 0, col)

        for row, sched in enumerate(self.schedules, start=1):
            cls_name = Class.get_by_id(sched.class_id).name if sched.class_id else ""
            teacher_name = Teacher.get_by_id(sched.teacher_id).name if sched.teacher_id else ""
            subject = Subject.get_by_id(sched.subject_id)
            subject_name = subject.name if subject else ""

            grid.addWidget(QLabel(sched.date), row, 0)
            grid.addWidget(QLabel(str(sched.lesson_number)), row, 1)
            grid.addWidget(QLabel(cls_name if object_type == 'teacher' else teacher_name), row, 2)
            grid.addWidget(QLabel(subject_name), row, 3)
            grid.addWidget(QLabel(sched.status), row, 4)

            combo = QComboBox()
            combo.addItem("—", None)

            if object_type == 'teacher' and subject_name:
                matching_ids = {t.id for t in Teacher.get_by_specialization(subject_name)}
                free = [
                    t for t in self.global_options
                    if not Schedule.get_conflicting_teacher_entry(t.id, sched.date, sched.lesson_number)
                ]
                candidates = free if free else self.global_options
            else:
                matching_ids = set()
                candidates = self.global_options

            for option in candidates:
                idx = combo.count()
                combo.addItem(option.name, option.id)
                if object_type == 'teacher':
                    color = Qt.GlobalColor.green if option.id in matching_ids else Qt.GlobalColor.red
                    combo.setItemData(idx, QBrush(color), Qt.ItemDataRole.ForegroundRole)

            if combo.count() > 1:
                combo.setCurrentIndex(1)

            self.replacement_combos[sched.id] = combo
            grid.addWidget(combo, row, 5)

        layout.addLayout(grid)

        if not self.global_options:
            layout.addWidget(QLabel(
                "<b>Нет доступных замен.</b> Сначала добавьте нового учителя или класс."
            ))

        save_btn = QPushButton("Сохранить и удалить")
        save_btn.setEnabled(bool(self.global_options))
        save_btn.clicked.connect(self.save_replacements)
        layout.addWidget(save_btn)

    def save_replacements(self):
        chosen = set()
        for sched in self.schedules:
            new_id = self.replacement_combos[sched.id].currentData()
            if not new_id:
                QMessageBox.warning(self, "Не выбрана замена",
                                    "Для каждого урока нужно выбрать замену.")
                return

            key = (new_id, sched.date, sched.lesson_number)
            if key in chosen:
                QMessageBox.warning(self, "Конфликт",
                                    "Один и тот же заменитель выбран дважды на одно время.")
                return
            chosen.add(key)

            if self.object_type == 'teacher':
                conflict = Schedule.get_conflicting_teacher_entry(new_id, sched.date, sched.lesson_number)
                if conflict and conflict[0] != sched.id:
                    t = Teacher.get_by_id(new_id)
                    c = Class.get_by_id(conflict[2])
                    QMessageBox.warning(self, "Конфликт учителя",
                                        f"{t.name} уже занят на {sched.date} урок {sched.lesson_number} "
                                        f"(класс {c.name if c else '?'}).")
                    return
            else:
                conflict = Schedule.get_conflicting_class_entry(new_id, sched.date, sched.lesson_number)
                if conflict and conflict[0] != sched.id:
                    c = Class.get_by_id(new_id)
                    t = Teacher.get_by_id(conflict[1])
                    QMessageBox.warning(self, "Конфликт класса",
                                        f"{c.name if c else '?'} уже занят на {sched.date} урок {sched.lesson_number} "
                                        f"(учитель {t.name if t else '?'}).")
                    return

        for sched in self.schedules:
            new_id = self.replacement_combos[sched.id].currentData()
            if self.object_type == 'teacher':
                sched.teacher_id = new_id
                sched.status = 'на замене'
            else:
                sched.class_id = new_id
            sched.save()

        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = MainController()
        self.setWindowTitle("Школьное расписание")
        self.setGeometry(100, 100, 1100, 720)

        self.lesson_cache = {}
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()
        self.selected_teacher_id = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Кнопки темы
        theme_layout = QHBoxLayout()
        light_btn = QPushButton("☀ Светлая тема")
        dark_btn = QPushButton("🌙 Тёмная тема")
        light_btn.clicked.connect(self.set_light_theme)
        dark_btn.clicked.connect(self.set_dark_theme)
        theme_layout.addWidget(light_btn)
        theme_layout.addWidget(dark_btn)
        theme_layout.addStretch()
        main_layout.addLayout(theme_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.schedule_tab = QWidget()
        self.tabs.addTab(self.schedule_tab, "📅 Расписание")
        self.setup_schedule_tab()

        self.teachers_tab = QWidget()
        self.tabs.addTab(self.teachers_tab, "👩‍🏫 Учителя")
        self.setup_teachers_tab()

        self.classes_tab = QWidget()
        self.tabs.addTab(self.classes_tab, "🏫 Классы")
        self.setup_classes_tab()

        self.subjects_tab = QWidget()
        self.tabs.addTab(self.subjects_tab, "📚 Предметы")
        self.setup_subjects_tab()

        self.load_all_lesson_counts()
        self.set_light_theme()

    # ── Кэш уроков ──────────────────────────────────────────────────────────

    def load_lesson_counts_for_teacher(self, teacher_id, year=None, month=None):
        year = year or self.current_year
        month = month or self.current_month
        self.lesson_cache.setdefault(teacher_id, {}).setdefault(year, {})
        counts = Schedule.get_daily_lesson_counts_for_teacher_month(teacher_id, year, month)
        self.lesson_cache[teacher_id][year][month] = {
            QDate.fromString(d, 'yyyy-MM-dd'): cnt
            for d, cnt in counts.items()
        }

    def load_all_lesson_counts(self):
        for teacher in Teacher.get_all():
            self.load_lesson_counts_for_teacher(teacher.id, self.current_year, self.current_month)

    def update_lesson_cache_for_teacher(self, teacher_id):
        self.load_lesson_counts_for_teacher(teacher_id)
        if self.selected_teacher_id == teacher_id:
            self.calendar.update_lesson_counts()
        self.load_all_lesson_counts()

    # ── Темы ────────────────────────────────────────────────────────────────

    def set_light_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f3f8"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#d8e2f1"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#0057b7"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet(
            "QWidget { background-color: #ffffff; color: #111111; }"
            "QLineEdit, QComboBox, QListWidget, QTabWidget, QCalendarWidget, QPushButton "
            "{ background-color: #f8fbff; color: #111111; border: 1px solid #c4d6ea; }"
            "QTabBar::tab { background: #e3eff9; color: #111111; padding: 8px 14px; margin: 2px; }"
            "QTabBar::tab:selected { background: #c7dcf2; font-weight: bold; }"
            "QPushButton { background-color: #d8e2f1; border: 1px solid #8aa7c7; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #b9d0ee; }"
            "QListWidget { alternate-background-color: #f0f5fb; }"
        )

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#232629"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2b2d31"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#32363d"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#f0f0f0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#3c4048"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#3399ff"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet(
            "QWidget { background-color: #232629; color: #f0f0f0; }"
            "QLineEdit, QComboBox, QListWidget, QTabWidget, QCalendarWidget, QPushButton "
            "{ background-color: #2b2d31; color: #f0f0f0; border: 1px solid #555; }"
            "QTabBar::tab { background: #2b2d31; color: #f0f0f0; padding: 8px 14px; margin: 2px; }"
            "QTabBar::tab:selected { background: #3c4048; font-weight: bold; }"
            "QPushButton { padding: 4px 10px; }"
            "QPushButton:hover { background-color: #4a5060; }"
        )

    # ── Вкладка Расписание ───────────────────────────────────────────────────

    def setup_schedule_tab(self):
        layout = QHBoxLayout(self.schedule_tab)

        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Учителя</b>"))
        self.teacher_list = QListWidget()
        self.teacher_list.itemClicked.connect(self.on_teacher_selected)
        left.addWidget(self.teacher_list)
        layout.addLayout(left, 1)

        self.calendar = ScheduleCalendar(self)
        self.calendar.clicked.connect(self.on_date_clicked)
        layout.addWidget(self.calendar, 2)

        self.load_teachers()

    def load_teachers(self):
        self.teacher_list.clear()
        for teacher in Teacher.get_all():
            item = QListWidgetItem(teacher.name)
            item.setData(Qt.ItemDataRole.UserRole, teacher.id)
            self.teacher_list.addItem(item)

    def on_teacher_selected(self, item):
        self.selected_teacher_id = item.data(Qt.ItemDataRole.UserRole)
        self.calendar.set_teacher_id(self.selected_teacher_id)

    def on_date_clicked(self, date):
        if not self.selected_teacher_id:
            QMessageBox.warning(self, "Выберите учителя",
                                "Сначала выберите учителя из списка слева.")
            return
        dialog = LessonDialog(date, self.selected_teacher_id, self)
        if dialog.exec():
            self.update_lesson_cache_for_teacher(self.selected_teacher_id)
            self.refresh_teacher_info()

    # ── Вкладка Учителя ──────────────────────────────────────────────────────

    def setup_teachers_tab(self):
        layout = QHBoxLayout(self.teachers_tab)

        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Список учителей</b>"))
        self.teachers_list = QListWidget()
        self.teachers_list.currentItemChanged.connect(self.display_teacher_info)
        left.addWidget(self.teachers_list)

        btns = QHBoxLayout()
        for label, slot in [("Добавить", self.add_teacher),
                             ("Редактировать", self.edit_teacher),
                             ("Удалить", self.delete_teacher)]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        left.addLayout(btns)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Профиль учителя</b>"))
        self.teacher_info_label = QLabel("Выберите учителя, чтобы увидеть данные")
        self.teacher_info_label.setWordWrap(True)
        self.teacher_info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.teacher_info_label.setMinimumWidth(300)
        right.addWidget(self.teacher_info_label)
        right.addStretch()
        layout.addLayout(right, 1)

        self.load_teachers_list()

    def load_teachers_list(self):
        self.teachers_list.clear()
        for teacher in Teacher.get_all():
            item = QListWidgetItem(teacher.name)
            item.setData(Qt.ItemDataRole.UserRole, teacher)
            self.teachers_list.addItem(item)

    def display_teacher_info(self, current, previous=None):
        if not current:
            self.teacher_info_label.setText("Выберите учителя, чтобы увидеть данные")
            return
        teacher = current.data(Qt.ItemDataRole.UserRole)
        # Используем current_year/current_month из календаря (тот месяц, что открыт)
        year = self.current_year
        month = self.current_month
        import calendar as cal_mod
        last_day = cal_mod.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"
        schedules = Schedule.get_by_teacher_date_range(teacher.id, start_date, end_date)
        counts = {'работает': 0, 'на замене': 0, 'болеет': 0, 'отсутствует': 0}
        for s in schedules:
            counts[s.status or 'работает'] = counts.get(s.status or 'работает', 0) + 1
        hours = counts['работает'] + counts['на замене']
        diff = hours - int(teacher.rate)
        diff_str = (f"+{diff}" if diff > 0 else str(diff)) if diff != 0 else "ровно"

        month_name = [
            "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
        ][month - 1]

        self.teacher_info_label.setText(
            f"<b>{teacher.name}</b><br><br>"
            f"Предметы: {', '.join(teacher.specialization) or '—'}<br>"
            f"Ставка: {teacher.rate} ч/мес<br><br>"
            f"<b>Месяц: {month_name} {year}</b><br>"
            f"Отработано: {hours} ч  ({diff_str} от ставки)<br><br>"
            f"Работает: {counts['работает']} уроков<br>"
            f"На замене: {counts['на замене']} уроков<br>"
            f"Болеет: {counts['болеет']} дней<br>"
            f"Отсутствует: {counts['отсутствует']} дней"
        )

    def refresh_teacher_info(self):
        current = self.teachers_list.currentItem()
        if current:
            self.display_teacher_info(current)

    def add_teacher(self):
        dialog = TeacherDialog(parent=self)
        if dialog.exec():
            teacher = dialog.get_teacher()
            if teacher:
                teacher.save()
                self.load_lesson_counts_for_teacher(teacher.id)
                self.load_teachers_list()
                self.load_teachers()

    def edit_teacher(self):
        current = self.teachers_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите учителя", "Выберите учителя для редактирования.")
            return
        teacher = current.data(Qt.ItemDataRole.UserRole)
        dialog = TeacherDialog(teacher, self)
        if dialog.exec():
            t = dialog.get_teacher()
            if t:
                t.save()
                self.load_teachers_list()
                self.load_teachers()

    def delete_teacher(self):
        current = self.teachers_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите учителя", "Выберите учителя для удаления.")
            return
        teacher = current.data(Qt.ItemDataRole.UserRole)
        schedules = Schedule.get_by_teacher(teacher.id)
        if schedules:
            dialog = ScheduleReassignmentDialog('teacher', teacher, schedules, self)
            if not dialog.exec():
                return
        else:
            reply = QMessageBox.question(
                self, "Удалить учителя",
                f"Удалить {teacher.name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        teacher.delete()
        self.lesson_cache.pop(teacher.id, None)
        self.load_teachers_list()
        self.load_teachers()
        self.refresh_teacher_info()

    # ── Вкладка Классы ───────────────────────────────────────────────────────

    def setup_classes_tab(self):
        layout = QVBoxLayout(self.classes_tab)
        layout.addWidget(QLabel("<b>Список классов</b>"))
        self.classes_list = QListWidget()
        layout.addWidget(self.classes_list)
        btns = QHBoxLayout()
        for label, slot in [("Добавить", self.add_class),
                             ("Редактировать", self.edit_class),
                             ("Удалить", self.delete_class)]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        layout.addLayout(btns)
        self.load_classes_list()

    def load_classes_list(self):
        self.classes_list.clear()
        for cls in Class.get_all():
            item = QListWidgetItem(cls.name)
            item.setData(Qt.ItemDataRole.UserRole, cls)
            self.classes_list.addItem(item)

    def add_class(self):
        dialog = ClassDialog(parent=self)
        if dialog.exec():
            cls = dialog.get_class()
            if cls:
                cls.save()
                self.load_classes_list()

    def edit_class(self):
        current = self.classes_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для редактирования.")
            return
        cls = current.data(Qt.ItemDataRole.UserRole)
        dialog = ClassDialog(cls, self)
        if dialog.exec():
            c = dialog.get_class()
            if c:
                c.save()
                self.load_classes_list()

    def delete_class(self):
        current = self.classes_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для удаления.")
            return
        cls = current.data(Qt.ItemDataRole.UserRole)
        schedules = Schedule.get_by_class(cls.id)
        if schedules:
            dialog = ScheduleReassignmentDialog('class', cls, schedules, self)
            if not dialog.exec():
                return
        else:
            reply = QMessageBox.question(
                self, "Удалить класс",
                f"Удалить {cls.name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        cls.delete()
        self.load_classes_list()
        self.refresh_teacher_info()

    # ── Вкладка Предметы ─────────────────────────────────────────────────────

    def setup_subjects_tab(self):
        layout = QVBoxLayout(self.subjects_tab)
        layout.addWidget(QLabel("<b>Список предметов</b>"))
        self.subjects_list = QListWidget()
        layout.addWidget(self.subjects_list)
        btns = QHBoxLayout()
        for label, slot in [("Добавить", self.add_subject),
                             ("Редактировать", self.edit_subject),
                             ("Удалить", self.delete_subject)]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        layout.addLayout(btns)
        self.load_subjects_list()

    def load_subjects_list(self):
        self.subjects_list.clear()
        for subj in Subject.get_all():
            item = QListWidgetItem(subj.name)
            item.setData(Qt.ItemDataRole.UserRole, subj)
            self.subjects_list.addItem(item)

    def add_subject(self):
        dialog = SubjectDialog(parent=self)
        if dialog.exec():
            subj = dialog.get_subject()
            if subj:
                subj.save()
                self.load_subjects_list()

    def edit_subject(self):
        current = self.subjects_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите предмет", "Выберите предмет для редактирования.")
            return
        subj = current.data(Qt.ItemDataRole.UserRole)
        dialog = SubjectDialog(subj, self)
        if dialog.exec():
            s = dialog.get_subject()
            if s:
                s.save()
                self.load_subjects_list()

    def delete_subject(self):
        current = self.subjects_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите предмет", "Выберите предмет для удаления.")
            return
        subj = current.data(Qt.ItemDataRole.UserRole)
        if Schedule.get_by_subject(subj.id):
            QMessageBox.warning(
                self, "Нельзя удалить",
                f"Предмет «{subj.name}» используется в расписании. "
                "Сначала удалите связанные уроки."
            )
            return
        reply = QMessageBox.question(
            self, "Удалить предмет",
            f"Удалить «{subj.name}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            subj.delete()
            self.load_subjects_list()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
