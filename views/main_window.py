import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget, QCalendarWidget, QHBoxLayout, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog, QComboBox, QGridLayout, QTabWidget, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox
from PyQt6.QtCore import QDate
from models.teacher import Teacher
from models.school_class import Class
from models.subject import Subject
from models.schedule import Schedule
from controllers.main_controller import MainController
import json

class LessonDialog(QDialog):
    def __init__(self, date, parent=None):
        super().__init__(parent)
        self.date = date
        self.setWindowTitle(f"Расписание на {date.toString('yyyy-MM-dd')}")
        self.layout = QGridLayout()

        self.subject_combos = []
        self.class_combos = []

        subjects = Subject.get_all()
        classes = Class.get_all()
        teachers = Teacher.get_all()

        for i in range(1, 9):  # 8 уроков
            label = QLabel(f"Урок {i}")
            self.layout.addWidget(label, i-1, 0)

            subject_combo = QComboBox()
            subject_combo.addItem("", None)
            for subj in subjects:
                subject_combo.addItem(subj.name, subj.id)
            self.layout.addWidget(subject_combo, i-1, 1)
            self.subject_combos.append(subject_combo)

            class_combo = QComboBox()
            class_combo.addItem("", None)
            for cls in classes:
                class_combo.addItem(cls.name, cls.id)
            self.layout.addWidget(class_combo, i-1, 2)
            self.class_combos.append(class_combo)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_schedule)
        self.layout.addWidget(save_button, 9, 1, 1, 2)

        self.setLayout(self.layout)

        # Загрузить существующие уроки
        existing = Schedule.get_by_date(date.toString('yyyy-MM-dd'))
        for sched in existing:
            if sched.lesson_number <= 8:
                self.subject_combos[sched.lesson_number-1].setCurrentIndex(
                    self.subject_combos[sched.lesson_number-1].findData(sched.subject_id)
                )
                self.class_combos[sched.lesson_number-1].setCurrentIndex(
                    self.class_combos[sched.lesson_number-1].findData(sched.class_id)
                )

    def save_schedule(self):
        date_str = self.date.toString('yyyy-MM-dd')
        # Удалить существующие для этого дня
        existing = Schedule.get_by_date(date_str)
        for sched in existing:
            sched.delete()

        # Сохранить новые
        for i in range(8):
            subj_id = self.subject_combos[i].currentData()
            cls_id = self.class_combos[i].currentData()
            if subj_id and cls_id:
                # Предполагаем, что учитель выбирается, но пока hardcoded teacher_id=1
                sched = Schedule(teacher_id=1, class_id=cls_id, subject_id=subj_id, date=date_str, lesson_number=i+1)
                sched.save()
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = MainController()
        self.setWindowTitle("Школьное расписание")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

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

    def setup_schedule_tab(self):
        layout = QHBoxLayout(self.schedule_tab)

        # Список учителей слева
        self.teacher_list = QListWidget()
        self.teacher_list.itemClicked.connect(self.on_teacher_selected)
        self.load_teachers()
        layout.addWidget(self.teacher_list)

        # Календарь справа
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.on_date_clicked)
        layout.addWidget(self.calendar)

        self.selected_teacher_id = None

    def setup_teachers_tab(self):
        layout = QVBoxLayout(self.teachers_tab)

        self.teachers_list = QListWidget()
        self.teachers_list.itemDoubleClicked.connect(self.show_teacher_profile)
        layout.addWidget(self.teachers_list)

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
        layout.addLayout(buttons_layout)

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
            self.teacher_list.addItem(teacher.name, teacher.id)

    def load_teachers_list(self):
        self.teachers_list.clear()
        teachers = Teacher.get_all()
        for teacher in teachers:
            self.teachers_list.addItem(teacher.name, teacher)

    def load_classes_list(self):
        self.classes_list.clear()
        classes = Class.get_all()
        for cls in classes:
            self.classes_list.addItem(cls.name, cls)

    def load_subjects_list(self):
        self.subjects_list.clear()
        subjects = Subject.get_all()
        for subj in subjects:
            self.subjects_list.addItem(subj.name, subj)

    def on_teacher_selected(self, item):
        self.selected_teacher_id = item.data()

    def on_date_clicked(self, date):
        if self.selected_teacher_id:
            dialog = LessonDialog(date, self.selected_teacher_id, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Выберите учителя", "Сначала выберите учителя из списка.")

    def show_teacher_profile(self, item):
        teacher = item.data()
        current_date = QDate.currentDate()
        year = current_date.year()
        month = current_date.month()
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{current_date.daysInMonth()}"
        hours = self.controller.calculate_hours(teacher.id, start_date, end_date)
        QMessageBox.information(self, "Профиль учителя", f"Учитель: {teacher.name}\nСпециализация: {', '.join(teacher.specialization)}\nСтавка: {teacher.rate} ч\nОтработано в этом месяце: {hours} ч")

    def add_teacher(self):
        dialog = TeacherDialog(parent=self)
        if dialog.exec():
            teacher = dialog.get_teacher()
            teacher.save()
            self.load_teachers_list()
            self.load_teachers()

    def edit_teacher(self):
        current = self.teachers_list.currentItem()
        if current:
            teacher = current.data()
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
        if current:
            teacher = current.data()
            reply = QMessageBox.question(self, "Удалить учителя", f"Удалить {teacher.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                teacher.delete()
                self.load_teachers_list()
                self.load_teachers()
        else:
            QMessageBox.warning(self, "Выберите учителя", "Выберите учителя для удаления.")

    def add_class(self):
        dialog = ClassDialog(parent=self)
        if dialog.exec():
            cls = dialog.get_class()
            cls.save()
            self.load_classes_list()

    def edit_class(self):
        current = self.classes_list.currentItem()
        if current:
            cls = current.data()
            dialog = ClassDialog(cls, self)
            if dialog.exec():
                cls = dialog.get_class()
                cls.save()
                self.load_classes_list()
        else:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для редактирования.")

    def delete_class(self):
        current = self.classes_list.currentItem()
        if current:
            cls = current.data()
            reply = QMessageBox.question(self, "Удалить класс", f"Удалить {cls.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                cls.delete()
                self.load_classes_list()
        else:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для удаления.")

    def add_subject(self):
        dialog = SubjectDialog(parent=self)
        if dialog.exec():
            subj = dialog.get_subject()
            subj.save()
            self.load_subjects_list()

    def edit_subject(self):
        current = self.subjects_list.currentItem()
        if current:
            subj = current.data()
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
            subj = current.data()
            reply = QMessageBox.question(self, "Удалить предмет", f"Удалить {subj.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                subj.delete()
                self.load_subjects_list()
        else:
            QMessageBox.warning(self, "Выберите предмет", "Выберите предмет для удаления.")
    def __init__(self, date, teacher_id, parent=None):
        super().__init__(parent)
        self.date = date
        self.teacher_id = teacher_id
        self.setWindowTitle(f"Расписание на {date.toString('yyyy-MM-dd')} для учителя {Teacher.get_by_id(teacher_id).name}")
        self.layout = QGridLayout()

        self.subject_combos = []
        self.class_combos = []

        subjects = Subject.get_all()
        classes = Class.get_all()

        for i in range(1, 9):  # 8 уроков
            label = QLabel(f"Урок {i}")
            self.layout.addWidget(label, i-1, 0)

            subject_combo = QComboBox()
            subject_combo.addItem("", None)
            for subj in subjects:
                subject_combo.addItem(subj.name, subj.id)
            self.layout.addWidget(subject_combo, i-1, 1)
            self.subject_combos.append(subject_combo)

            class_combo = QComboBox()
            class_combo.addItem("", None)
            for cls in classes:
                class_combo.addItem(cls.name, cls.id)
            self.layout.addWidget(class_combo, i-1, 2)
            self.class_combos.append(class_combo)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_schedule)
        self.layout.addWidget(save_button, 9, 1, 1, 2)

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

    def save_schedule(self):
        date_str = self.date.toString('yyyy-MM-dd')
        # Удалить существующие для этого дня и учителя
        existing = Schedule.get_by_date_and_teacher(date_str, self.teacher_id)
        for sched in existing:
            sched.delete()

        # Сохранить новые
        for i in range(8):
            subj_id = self.subject_combos[i].currentData()
            cls_id = self.class_combos[i].currentData()
            if subj_id and cls_id:
                sched = Schedule(teacher_id=self.teacher_id, class_id=cls_id, subject_id=subj_id, date=date_str, lesson_number=i+1)
                sched.save()
        self.accept()

    # Список учителей слева
        self.teacher_list = QListWidget()
        self.teacher_list.itemClicked.connect(self.on_teacher_selected)
        self.load_teachers()
        layout.addWidget(self.teacher_list)

        # Календарь справа
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.on_date_clicked)
        layout.addWidget(self.calendar)

        self.selected_teacher_id = None

    def setup_teachers_tab(self):
        layout = QVBoxLayout(self.teachers_tab)

        self.teachers_list = QListWidget()
        self.teachers_list.itemDoubleClicked.connect(self.show_teacher_profile)
        layout.addWidget(self.teachers_list)

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
        layout.addLayout(buttons_layout)

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
            self.teacher_list.addItem(teacher.name, teacher.id)

    def load_teachers_list(self):
        self.teachers_list.clear()
        teachers = Teacher.get_all()
        for teacher in teachers:
            self.teachers_list.addItem(teacher.name, teacher)

    def load_classes_list(self):
        self.classes_list.clear()
        classes = Class.get_all()
        for cls in classes:
            self.classes_list.addItem(cls.name, cls)

    def load_subjects_list(self):
        self.subjects_list.clear()
        subjects = Subject.get_all()
        for subj in subjects:
            self.subjects_list.addItem(subj.name, subj)

    def on_teacher_selected(self, item):
        self.selected_teacher_id = item.data()

    def on_date_clicked(self, date):
        if self.selected_teacher_id:
            dialog = LessonDialog(date, self.selected_teacher_id, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Выберите учителя", "Сначала выберите учителя из списка.")

    def show_teacher_profile(self, item):
        teacher = item.data()
        current_date = QDate.currentDate()
        year = current_date.year()
        month = current_date.month()
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{current_date.daysInMonth()}"
        hours = self.controller.calculate_hours(teacher.id, start_date, end_date)
        QMessageBox.information(self, "Профиль учителя", f"Учитель: {teacher.name}\nСпециализация: {', '.join(teacher.specialization)}\nСтавка: {teacher.rate} ч\nОтработано в этом месяце: {hours} ч")

    def add_teacher(self):
        dialog = TeacherDialog(parent=self)
        if dialog.exec():
            teacher = dialog.get_teacher()
            teacher.save()
            self.load_teachers_list()
            self.load_teachers()

    def edit_teacher(self):
        current = self.teachers_list.currentItem()
        if current:
            teacher = current.data()
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
        if current:
            teacher = current.data()
            reply = QMessageBox.question(self, "Удалить учителя", f"Удалить {teacher.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                teacher.delete()
                self.load_teachers_list()
                self.load_teachers()
        else:
            QMessageBox.warning(self, "Выберите учителя", "Выберите учителя для удаления.")

    def add_class(self):
        dialog = ClassDialog(parent=self)
        if dialog.exec():
            cls = dialog.get_class()
            cls.save()
            self.load_classes_list()

    def edit_class(self):
        current = self.classes_list.currentItem()
        if current:
            cls = current.data()
            dialog = ClassDialog(cls, self)
            if dialog.exec():
                cls = dialog.get_class()
                cls.save()
                self.load_classes_list()
        else:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для редактирования.")

    def delete_class(self):
        current = self.classes_list.currentItem()
        if current:
            cls = current.data()
            reply = QMessageBox.question(self, "Удалить класс", f"Удалить {cls.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                cls.delete()
                self.load_classes_list()
        else:
            QMessageBox.warning(self, "Выберите класс", "Выберите класс для удаления.")

    def add_subject(self):
        dialog = SubjectDialog(parent=self)
        if dialog.exec():
            subj = dialog.get_subject()
            subj.save()
            self.load_subjects_list()

    def edit_subject(self):
        current = self.subjects_list.currentItem()
        if current:
            subj = current.data()
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
            subj = current.data()
            reply = QMessageBox.question(self, "Удалить предмет", f"Удалить {subj.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                subj.delete()
                self.load_subjects_list()
        else:
            QMessageBox.warning(self, "Выберите предмет", "Выберите предмет для удаления.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())