import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget, QCalendarWidget, QHBoxLayout, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog, QComboBox, QGridLayout, QTabWidget, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox, QListWidgetItem
from PyQt6.QtGui import QPainter, QBrush, QColor, QPalette
from PyQt6.QtCore import QDate, Qt
from models.teacher import Teacher
from models.school_class import Class
from models.subject import Subject
from models.schedule import Schedule
from controllers.main_controller import MainController
import json

class ScheduleCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.teacher_id = None
        self.lesson_counts = {}
        self.currentPageChanged.connect(self._on_page_changed)

    def set_teacher_id(self, teacher_id):
        self.teacher_id = teacher_id
        self.update_lesson_counts()

    def update_lesson_counts(self):
        if not self.teacher_id or not hasattr(self.parent(), 'lesson_cache'):
            self.lesson_counts = {}
            self.update()
            return
        year = self.yearShown()
        month = self.monthShown()
        cache = self.parent().lesson_cache
        if self.teacher_id not in cache or year not in cache[self.teacher_id] or month not in cache[self.teacher_id][year]:
            # Load if not cached
            self.parent().load_lesson_counts_for_teacher(self.teacher_id, year, month)
        self.lesson_counts = cache[self.teacher_id][year][month]
        self.update()

    def _on_page_changed(self, year, month):
        self.parent().current_year = year
        self.parent().current_month = month
        self.parent().load_all_lesson_counts()
        self.update_lesson_counts()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        count = self.lesson_counts.get(date, 0)
        if count:
            painter.save()
            painter.setPen(Qt.GlobalColor.red)
            painter.setBrush(Qt.GlobalColor.yellow)  # Add background
            text_rect = rect.adjusted(rect.width() - 20, rect.height() - 20, 0, 0)
            painter.drawRect(text_rect)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(count))
            painter.restore()

class TeacherDialog(QDialog):
    def __init__(self, teacher=None, parent=None):
        super().__init__(parent)
        self.teacher = teacher
        self.setWindowTitle("Учитель" if teacher else "Новый учитель")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(teacher.name if teacher else "")
        self.spec_edit = QLineEdit(", ".join(teacher.specialization) if teacher else "")
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(0, 200)
        self.rate_spin.setValue(int(teacher.rate) if teacher else 0)

        layout.addRow("ФИО:", self.name_edit)
        layout.addRow("Специализация (через запятую):", self.spec_edit)
        layout.addRow("Ставка (часы):", self.rate_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_teacher(self):
        name = self.name_edit.text().strip()
        spec = [s.strip() for s in self.spec_edit.text().split(",") if s.strip()]
        rate = self.rate_spin.value()
        if self.teacher:
            self.teacher.name = name
            self.teacher.specialization = spec
            self.teacher.rate = rate
            return self.teacher
        else:
            return Teacher(name=name, specialization=spec, rate=rate)

class ClassDialog(QDialog):
    def __init__(self, cls=None, parent=None):
        super().__init__(parent)
        self.cls = cls
        self.setWindowTitle("Класс" if cls else "Новый класс")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(cls.name if cls else "")

        layout.addRow("Название:", self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_class(self):
        name = self.name_edit.text().strip()
        if self.cls:
            self.cls.name = name
            return self.cls
        else:
            return Class(name=name)

class SubjectDialog(QDialog):
    def __init__(self, subj=None, parent=None):
        super().__init__(parent)
        self.subj = subj
        self.setWindowTitle("Предмет" if subj else "Новый предмет")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(subj.name if subj else "")

        layout.addRow("Название:", self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_subject(self):
        name = self.name_edit.text().strip()
        if self.subj:
            self.subj.name = name
            return self.subj
        else:
            return Subject(name=name)

class LessonDialog(QDialog):
    def __init__(self, date, teacher_id, parent=None):
        super().__init__(parent)
        self.date = date
        self.teacher_id = teacher_id
        self.setWindowTitle(f"Расписание на {date.toString('yyyy-MM-dd')} для учителя {Teacher.get_by_id(teacher_id).name}")
        self.layout = QGridLayout()

        self.subject_combos = []
        self.class_combos = []
        self.status_combos = []
        self.clear_buttons = []

        subjects = Subject.get_all()
        classes = Class.get_all()

        self.layout.addWidget(QLabel("Урок"), 0, 0)
        self.layout.addWidget(QLabel("Предмет"), 0, 1)
        self.layout.addWidget(QLabel("Класс"), 0, 2)
        self.layout.addWidget(QLabel("Статус"), 0, 3)
        self.layout.addWidget(QLabel("Очистить"), 0, 4)

        for i in range(1, 9):  # 8 уроков
            label = QLabel(f"Урок {i}")
            self.layout.addWidget(label, i, 0)

            subject_combo = QComboBox()
            subject_combo.addItem("", None)
            for subj in subjects:
                subject_combo.addItem(subj.name, subj.id)
            self.layout.addWidget(subject_combo, i, 1)
            self.subject_combos.append(subject_combo)

            class_combo = QComboBox()
            class_combo.addItem("", None)
            for cls in classes:
                class_combo.addItem(cls.name, cls.id)
            self.layout.addWidget(class_combo, i, 2)
            self.class_combos.append(class_combo)

            status_combo = QComboBox()
            status_combo.addItem("Работает", "работает")
            status_combo.addItem("На замене", "на замене")
            status_combo.addItem("Болеет", "болеет")
            status_combo.addItem("Отсутствует", "отсутствует")
            self.layout.addWidget(status_combo, i, 3)
            self.status_combos.append(status_combo)

            clear_button = QPushButton("Очистить")
            clear_button.clicked.connect(lambda checked, row=i-1: self.clear_row(row))
            self.layout.addWidget(clear_button, i, 4)
            self.clear_buttons.append(clear_button)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_schedule)
        self.layout.addWidget(save_button, 10, 1, 1, 4)

        self.setLayout(self.layout)

        # Загрузить существующие уроки
        existing = Schedule.get_by_date_and_teacher(date.toString('yyyy-MM-dd'), teacher_id)
        for sched in existing:
            if sched.lesson_number <= 8:
                self.subject_combos[sched.lesson_number-1].setCurrentIndex(
                    self.subject_combos[sched.lesson_number-1].findData(sched.subject_id)
                )
                self.class_combos[sched.lesson_number-1].setCurrentIndex(
                    self.class_combos[sched.lesson_number-1].findData(sched.class_id)
                )
                self.status_combos[sched.lesson_number-1].setCurrentIndex(
                    self.status_combos[sched.lesson_number-1].findData(sched.status)
                )

    def save_schedule(self):
        date_str = self.date.toString('yyyy-MM-dd')
        # Удалить существующие для этого дня и учителя
        existing = Schedule.get_by_date_and_teacher(date_str, self.teacher_id)
        for sched in existing:
            sched.delete()

        # Проверить и сохранить новые
        for i in range(8):
            subj_id = self.subject_combos[i].currentData()
            cls_id = self.class_combos[i].currentData()
            status = self.status_combos[i].currentData() or "работает"
            if not subj_id or not cls_id:
                continue

            lesson_number = i + 1
            teacher_conflict = Schedule.get_conflicting_teacher_entry(self.teacher_id, date_str, lesson_number)
            class_conflict = Schedule.get_conflicting_class_entry(cls_id, date_str, lesson_number)

            if teacher_conflict and teacher_conflict[2] != cls_id:
                teacher_name = Teacher.get_by_id(self.teacher_id).name
                conflict_class_id = teacher_conflict[2]
                conflict_class = Class.get_by_id(conflict_class_id)
                conflict_class_name = conflict_class.name if conflict_class else str(conflict_class_id)
                result = QMessageBox.question(
                    self,
                    "Конфликт учителя",
                    f"Учитель {teacher_name} уже назначен на урок {lesson_number} {date_str} для класса {conflict_class_name}.\n"
                    "Вы уверены, что хотите назначить его на два класса одновременно?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result != QMessageBox.StandardButton.Yes:
                    return

            if class_conflict and class_conflict[1] != self.teacher_id:
                conflict_teacher_id = class_conflict[1]
                conflict_teacher = Teacher.get_by_id(conflict_teacher_id)
                conflict_teacher_name = conflict_teacher.name if conflict_teacher else str(conflict_teacher_id)
                QMessageBox.critical(
                    self,
                    "Конфликт класса",
                    f"Класс уже занят: класс {Class.get_by_id(cls_id).name} имеет урок {lesson_number} {date_str} у учителя {conflict_teacher_name}.\n"
                    "Нельзя назначить этот класс на два урока одновременно."
                )
                return

            sched = Schedule(teacher_id=self.teacher_id, class_id=cls_id, subject_id=subj_id, date=date_str, lesson_number=lesson_number, status=status)
            sched.save()

        self.accept()

    def clear_row(self, row):
        if 0 <= row < len(self.subject_combos):
            self.subject_combos[row].setCurrentIndex(0)
            self.class_combos[row].setCurrentIndex(0)
            self.status_combos[row].setCurrentIndex(0)

class ScheduleReassignmentDialog(QDialog):
    def __init__(self, object_type, object_to_delete, schedules, parent=None):
        super().__init__(parent)
        self.object_type = object_type
        self.object_to_delete = object_to_delete
        self.schedules = schedules
        self.setWindowTitle(
            f"Переназначить уроки учителя {object_to_delete.name}" if object_type == 'teacher'
            else f"Переназначить уроки класса {object_to_delete.name}"
        )

        layout = QVBoxLayout(self)
        note_text = (
            "Подбираем свободного учителя по предмету. Если подходящих нет, выберите замену вручную."
            if object_type == 'teacher' else
            "Выберите новый класс для каждого урока и сохраните изменения."
        )
        layout.addWidget(QLabel(note_text))

        self.replacement_combos = {}
        self.replacement_options = {}
        self.global_options = []

        if object_type == 'teacher':
            self.global_options = [t for t in Teacher.get_all() if t.id != object_to_delete.id]
            replacement_label = "Новый учитель"
        else:
            self.global_options = [c for c in Class.get_all() if c.id != object_to_delete.id]
            replacement_label = "Новый класс"

        grid = QGridLayout()
        grid.addWidget(QLabel("Дата"), 0, 0)
        grid.addWidget(QLabel("Урок"), 0, 1)
        grid.addWidget(QLabel("Класс" if object_type == 'teacher' else "Учитель"), 0, 2)
        grid.addWidget(QLabel("Предмет"), 0, 3)
        grid.addWidget(QLabel("Статус"), 0, 4)
        grid.addWidget(QLabel(replacement_label), 0, 5)

        self.suggested_found = False
        fallback_needed = False

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
            combo.addItem("", None)
            candidates = []
            same_specialization_ids = set()

            if object_type == 'teacher' and subject_name:
                matching = Teacher.get_by_specialization(subject_name)
                same_specialization_ids = {t.id for t in matching}
                candidates = [t for t in matching if t.id != object_to_delete.id and not Schedule.get_conflicting_teacher_entry(t.id, sched.date, sched.lesson_number)]
                if candidates:
                    self.suggested_found = True
                else:
                    fallback_needed = True

            if not candidates:
                candidates = self.global_options

            for option in candidates:
                index = combo.count()
                combo.addItem(option.name, option.id)
                if object_type == 'teacher':
                    if option.id in same_specialization_ids:
                        combo.setItemData(index, QBrush(Qt.GlobalColor.green), Qt.ItemDataRole.ForegroundRole)
                    else:
                        combo.setItemData(index, QBrush(Qt.GlobalColor.red), Qt.ItemDataRole.ForegroundRole)

            if candidates and candidates[0].id is not None:
                combo.setCurrentIndex(1)

            self.replacement_combos[sched.id] = combo
            self.replacement_options[sched.id] = candidates
            grid.addWidget(combo, row, 5)

        layout.addLayout(grid)

        if object_type == 'teacher' and fallback_needed and not self.suggested_found:
            layout.addWidget(QLabel("Нет свободных учителей со специализацией по предмету. Выберите замену вручную."))
        elif object_type == 'teacher' and not self.suggested_found:
            layout.addWidget(QLabel("Нет данных для подбора замены по специализации. Выберите учителя вручную."))

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_replacements)
        layout.addWidget(self.save_button)

        if not self.global_options:
            self.save_button.setEnabled(False)
            layout.addWidget(QLabel("Нет доступных заменителей. Добавьте нового учителя или класс перед удалением."))

    def save_replacements(self):
        if not self.global_options:
            return

        chosen = set()
        for sched in self.schedules:
            combo = self.replacement_combos[sched.id]
            new_id = combo.currentData()
            if not new_id:
                QMessageBox.warning(self, "Не выбрана замена", "Для каждого урока нужно выбрать замену.")
                return

            if self.object_type == 'teacher':
                key = (new_id, sched.date, sched.lesson_number)
                if key in chosen:
                    QMessageBox.warning(self, "Конфликт замены", "Один и тот же учитель выбран для двух уроков в одно и то же время.")
                    return
                chosen.add(key)
                conflict = Schedule.get_conflicting_teacher_entry(new_id, sched.date, sched.lesson_number)
                if conflict and conflict[0] != sched.id:
                    conflict_class = Class.get_by_id(conflict[2])
                    QMessageBox.warning(
                        self,
                        "Конфликт учителя",
                        f"Учитель {Teacher.get_by_id(new_id).name} уже занят на {sched.date} урок {sched.lesson_number} для класса {conflict_class.name if conflict_class else conflict[2]}."
                    )
                    return
            else:
                key = (new_id, sched.date, sched.lesson_number)
                if key in chosen:
                    QMessageBox.warning(self, "Конфликт замены", "Один и тот же класс выбран для двух уроков в одно и то же время.")
                    return
                chosen.add(key)
                conflict = Schedule.get_conflicting_class_entry(new_id, sched.date, sched.lesson_number)
                if conflict and conflict[0] != sched.id:
                    conflict_teacher = Teacher.get_by_id(conflict[1])
                    QMessageBox.warning(
                        self,
                        "Конфликт класса",
                        f"Класс {Class.get_by_id(new_id).name} уже занят на {sched.date} урок {sched.lesson_number} у учителя {conflict_teacher.name if conflict_teacher else conflict[1]}."
                    )
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
        self.setGeometry(100, 100, 1000, 700)

        self.lesson_cache = {}  # {teacher_id: {year: {month: {date: count}}}}
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        theme_layout = QHBoxLayout()
        light_btn = QPushButton("Светлая тема")
        dark_btn = QPushButton("Темная тема")
        light_btn.clicked.connect(self.set_light_theme)
        dark_btn.clicked.connect(self.set_dark_theme)
        theme_layout.addWidget(light_btn)
        theme_layout.addWidget(dark_btn)
        theme_layout.addStretch()
        main_layout.addLayout(theme_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка Расписание
        self.schedule_tab = QWidget()
        self.tabs.addTab(self.schedule_tab, "Расписание")
        self.setup_schedule_tab()

        # Вкладка Учителя
        self.teachers_tab = QWidget()
        self.tabs.addTab(self.teachers_tab, "Учителя")
        self.setup_teachers_tab()

        # Вкладка Классы
        self.classes_tab = QWidget()
        self.tabs.addTab(self.classes_tab, "Классы")
        self.setup_classes_tab()

        # Вкладка Предметы
        self.subjects_tab = QWidget()
        self.tabs.addTab(self.subjects_tab, "Предметы")
        self.setup_subjects_tab()

        self.load_all_lesson_counts()
        self.set_light_theme()

    def load_all_lesson_counts(self):
        teachers = Teacher.get_all()
        for teacher in teachers:
            self.load_lesson_counts_for_teacher(teacher.id, self.current_year, self.current_month)

    def set_light_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f3f8"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#d8e2f1"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#0057b7"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet(
            "QWidget { background-color: #ffffff; color: #111111; } "
            "QLineEdit, QComboBox, QListWidget, QTabWidget, QCalendarWidget, QPushButton { background-color: #f8fbff; color: #111111; border: 1px solid #c4d6ea; } "
            "QTabBar::tab { background: #e3eff9; color: #111111; padding: 8px; margin: 2px; } "
            "QTabBar::tab:selected { background: #c7dcf2; font-weight: bold; } "
            "QPushButton { background-color: #d8e2f1; border: 1px solid #8aa7c7; } "
            "QPushButton:hover { background-color: #b9d0ee; } "
            "QListWidget { alternate-background-color: #f0f5fb; }"
        )

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#232629"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2b2d31"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#32363d"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#f0f0f0"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#f0f0f0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#3c4048"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#3399ff"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet("QWidget { background-color: #232629; color: #f0f0f0; } QLineEdit, QComboBox, QListWidget, QTabWidget, QCalendarWidget, QPushButton { background-color: #2b2d31; color: #f0f0f0; }")

    def refresh_teacher_info(self):
        current = self.teachers_list.currentItem()
        if current:
            self.display_teacher_info(current)

    def load_lesson_counts_for_teacher(self, teacher_id, year=None, month=None):
        if year is None:
            year = self.current_year
        if month is None:
            month = self.current_month
        if teacher_id not in self.lesson_cache:
            self.lesson_cache[teacher_id] = {}
        if year not in self.lesson_cache[teacher_id]:
            self.lesson_cache[teacher_id][year] = {}
        counts = Schedule.get_daily_lesson_counts_for_teacher_month(teacher_id, year, month)
        self.lesson_cache[teacher_id][year][month] = {QDate.fromString(date_str, 'yyyy-MM-dd'): count for date_str, count in counts.items()}

    def update_lesson_cache_for_teacher(self, teacher_id):
        self.load_lesson_counts_for_teacher(teacher_id)
        if self.selected_teacher_id == teacher_id:
            self.calendar.update_lesson_counts()

        self.load_all_lesson_counts()

    def setup_schedule_tab(self):
        layout = QHBoxLayout(self.schedule_tab)

        # Список учителей слева
        self.teacher_list = QListWidget()
        self.teacher_list.itemClicked.connect(self.on_teacher_selected)
        self.load_teachers()
        layout.addWidget(self.teacher_list)

        # Календарь справа
        self.calendar = ScheduleCalendar()
        self.calendar.clicked.connect(self.on_date_clicked)
        layout.addWidget(self.calendar)

        self.selected_teacher_id = None

    def setup_teachers_tab(self):
        layout = QHBoxLayout(self.teachers_tab)

        left_layout = QVBoxLayout()
        self.teachers_list = QListWidget()
        self.teachers_list.currentItemChanged.connect(self.display_teacher_info)
        left_layout.addWidget(self.teachers_list)

        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_teacher)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_teacher)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_teacher)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        left_layout.addLayout(buttons_layout)

        layout.addLayout(left_layout, 1)

        self.teacher_info_label = QLabel("Выберите учителя, чтобы увидеть данные")
        self.teacher_info_label.setWordWrap(True)
        self.teacher_info_label.setMinimumWidth(300)
        layout.addWidget(self.teacher_info_label, 1)

        self.load_teachers_list()

    def setup_classes_tab(self):
        layout = QVBoxLayout(self.classes_tab)

        self.classes_list = QListWidget()
        layout.addWidget(self.classes_list)

        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_class)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_class)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_class)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        layout.addLayout(buttons_layout)

        self.load_classes_list()

    def setup_subjects_tab(self):
        layout = QVBoxLayout(self.subjects_tab)

        self.subjects_list = QListWidget()
        layout.addWidget(self.subjects_list)

        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_subject)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_subject)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_subject)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        layout.addLayout(buttons_layout)

        self.load_subjects_list()

    def load_teachers(self):
        self.teacher_list.clear()
        teachers = Teacher.get_all()
        for teacher in teachers:
            item = QListWidgetItem(teacher.name)
            item.setData(Qt.ItemDataRole.UserRole, teacher.id)
            self.teacher_list.addItem(item)

    def load_teachers_list(self):
        self.teachers_list.clear()
        teachers = Teacher.get_all()
        for teacher in teachers:
            item = QListWidgetItem(teacher.name)
            item.setData(Qt.ItemDataRole.UserRole, teacher)
            self.teachers_list.addItem(item)

    def load_classes_list(self):
        self.classes_list.clear()
        classes = Class.get_all()
        for cls in classes:
            item = QListWidgetItem(cls.name)
            item.setData(Qt.ItemDataRole.UserRole, cls)
            self.classes_list.addItem(item)

    def load_subjects_list(self):
        self.subjects_list.clear()
        subjects = Subject.get_all()
        for subj in subjects:
            item = QListWidgetItem(subj.name)
            item.setData(Qt.ItemDataRole.UserRole, subj)
            self.subjects_list.addItem(item)

    def on_teacher_selected(self, item):
        self.selected_teacher_id = item.data(Qt.ItemDataRole.UserRole)
        self.calendar.set_teacher_id(self.selected_teacher_id)

    def on_date_clicked(self, date):
        if self.selected_teacher_id:
            dialog = LessonDialog(date, self.selected_teacher_id, self)
            if dialog.exec():
                self.update_lesson_cache_for_teacher(self.selected_teacher_id)
                self.refresh_teacher_info()
        else:
            QMessageBox.warning(self, "Выберите учителя", "Сначала выберите учителя из списка.")

    def display_teacher_info(self, current, previous=None):
        if current:
            teacher = current.data(Qt.ItemDataRole.UserRole)
            current_date = QDate.currentDate()
            year = current_date.year()
            month = current_date.month()
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{current_date.daysInMonth()}"
            schedules = Schedule.get_by_teacher_date_range(teacher.id, start_date, end_date)
            counts = {
                'работает': 0,
                'на замене': 0,
                'болеет': 0,
                'отсутствует': 0,
            }
            for sched in schedules:
                status = sched.status or 'работает'
                counts[status] = counts.get(status, 0) + 1
            hours = counts['работает'] + counts['на замене']
            self.teacher_info_label.setText(
                f"Учитель: {teacher.name}\n"
                f"Специализация: {', '.join(teacher.specialization)}\n"
                f"Ставка: {teacher.rate} ч\n"
                f"Отработано в этом месяце: {hours} ч\n"
                f"Статусы: работает {counts['работает']}, на замене {counts['на замене']}, болеет {counts['болеет']}, отсутствует {counts['отсутствует']}"
            )
        else:
            self.teacher_info_label.setText("Выберите учителя, чтобы увидеть данные")

    def add_teacher(self):
        dialog = TeacherDialog(parent=self)
        if dialog.exec():
            teacher = dialog.get_teacher()
            teacher.save()
            self.load_lesson_counts_for_teacher(teacher.id)
            self.load_teachers_list()
            self.load_teachers()

    def edit_teacher(self):
        current = self.teachers_list.currentItem()
        if current:
            teacher = current.data(Qt.ItemDataRole.UserRole)
            dialog = TeacherDialog(teacher, self)
            if dialog.exec():
                teacher = dialog.get_teacher()
                teacher.save()
                self.load_teachers_list()
                self.load_teachers()
        else:
            QMessageBox.warning(self, "Выберите учителя", "Выберите учителя для редактирования.")

    def delete_teacher(self):
        current = self.teachers_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите учителя", "Выберите учителя для удаления.")
            return

        teacher = current.data(Qt.ItemDataRole.UserRole)
        schedules = Schedule.get_by_teacher(teacher.id)
        if not schedules:
            reply = QMessageBox.question(self, "Удалить учителя", f"Удалить {teacher.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                teacher.delete()
                if teacher.id in self.lesson_cache:
                    del self.lesson_cache[teacher.id]
                self.load_teachers_list()
                self.load_teachers()
                self.refresh_teacher_info()
            return

        dialog = ScheduleReassignmentDialog('teacher', teacher, schedules, self)
        if dialog.exec():
            try:
                teacher.delete()
                if teacher.id in self.lesson_cache:
                    del self.lesson_cache[teacher.id]
                self.load_teachers_list()
                self.load_teachers()
                self.refresh_teacher_info()
            except ValueError as e:
                QMessageBox.warning(self, "Нельзя удалить", str(e))

    def add_class(self):
        dialog = ClassDialog(parent=self)
        if dialog.exec():
            cls = dialog.get_class()
            cls.save()
            self.load_classes_list()

    def edit_class(self):
        current = self.classes_list.currentItem()
        if current:
            cls = current.data(Qt.ItemDataRole.UserRole)
            dialog = ClassDialog(cls, self)
            if dialog.exec():
                cls = dialog.get_class()
                cls.save()
                self.load_classes_list()
        else:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для редактирования.")

    def delete_class(self):
        current = self.classes_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для удаления.")
            return

        cls = current.data(Qt.ItemDataRole.UserRole)
        schedules = Schedule.get_by_class(cls.id)
        if not schedules:
            reply = QMessageBox.question(self, "Удалить класс", f"Удалить {cls.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                cls.delete()
                self.load_classes_list()
            return

        dialog = ScheduleReassignmentDialog('class', cls, schedules, self)
        if dialog.exec():
            try:
                cls.delete()
                self.load_classes_list()
                self.refresh_teacher_info()
            except ValueError as e:
                QMessageBox.warning(self, "Нельзя удалить", str(e))

    def add_subject(self):
        dialog = SubjectDialog(parent=self)
        if dialog.exec():
            subj = dialog.get_subject()
            subj.save()
            self.load_subjects_list()

    def edit_subject(self):
        current = self.subjects_list.currentItem()
        if current:
            subj = current.data(Qt.ItemDataRole.UserRole)
            dialog = SubjectDialog(subj, self)
            if dialog.exec():
                subj = dialog.get_subject()
                subj.save()
                self.load_subjects_list()
        else:
            QMessageBox.warning(self, "Выберите предмет", "Выберите предмет для редактирования.")

    def delete_subject(self):
        current = self.subjects_list.currentItem()
        if current:
            subj = current.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self, "Удалить предмет", f"Удалить {subj.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    subj.delete()
                    self.load_subjects_list()
                except ValueError as e:
                    QMessageBox.warning(self, "Нельзя удалить", str(e))
        else:
            QMessageBox.warning(self, "Выберите предмет", "Выберите предмет для удаления.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())