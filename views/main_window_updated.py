from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QCalendarWidget, QLabel,
    QComboBox, QDialog, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QSpinBox, QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, QDate
import database as db

class TeacherDialog(QDialog):
    """Диалог добавления/редактирования учителя."""
    def __init__(self, parent=None, teacher=None):
        super().__init__(parent)
        self.setWindowTitle("Учитель")
        self.teacher_id = None
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.spec_edit = QLineEdit()
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 60)
        self.hours_spin.setValue(18)

        layout.addRow("ФИО:", self.name_edit)
        layout.addRow("Специализация:", self.spec_edit)
        layout.addRow("Желаемая ставка (ч):", self.hours_spin)

        if teacher:
            self.teacher_id = teacher["id"]
            self.name_edit.setText(teacher["full_name"])
            self.spec_edit.setText(teacher["specialization"] or "")
            self.hours_spin.setValue(teacher["desired_hours"] or 18)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "id": self.teacher_id,
            "full_name": self.name_edit.text().strip(),
            "specialization": self.spec_edit.text().strip(),
            "desired_hours": self.hours_spin.value()
        }

class LessonDialog(QDialog):
    """Модальное окно с сеткой 8 уроков для выбранного учителя и даты."""
    LESSON_TIMES = [
        ("1", "08:30-09:15"),
        ("2", "09:25-10:10"),
        ("3", "10:30-11:15"),
        ("4", "11:25-12:10"),
        ("5", "12:20-13:05"),
        ("6", "13:15-14:00"),
        ("7", "14:10-14:55"),
        ("8", "15:05-15:50")
    ]

    def __init__(self, teacher, date: QDate, parent=None):
        super().__init__(parent)
        self.teacher = teacher
        self.date = date
        self.date_str = date.toString("yyyy-MM-dd")
        self.setWindowTitle(f"Расписание: {teacher['full_name']} – {date.toString('dd.MM.yyyy')}")
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Информация об отсутствии
        self.absent = db.is_absent(teacher["id"], self.date_str)
        self.absent_label = QLabel()
        self.absent_label.setStyleSheet("color: red; font-weight: bold;")
        if self.absent:
            self.absent_label.setText("⚠ Учитель на больничном (требуется замена)")
        else:
            self.absent_label.setText("")
        layout.addWidget(self.absent_label)

        # Таблица уроков
        self.table = QTableWidget(8, 4)
        self.table.setHorizontalHeaderLabels(["№", "Время", "Предмет", "Класс"])
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 150)

        # Предзаполнение комбобоксов
        self.subjects = db.get_all_subjects()
        self.classes = db.get_all_classes()

        # Загружаем существующее расписание на эту дату
        existing = db.get_schedule_for_teacher_date(teacher["id"], self.date_str)
        self.lesson_map = {row["lesson_number"]: row for row in existing}

        # Определяем "окна" (пропуски между уроками)
        occupied = sorted([r["lesson_number"] for r in existing])
        gaps = set()
        if len(occupied) >= 2:
            for i in range(len(occupied)-1):
                gaps.update(range(occupied[i]+1, occupied[i+1]))

        for i in range(8):
            lesson_no = i+1
            time_str = self.LESSON_TIMES[i][1]
            self.table.setItem(i, 0, QTableWidgetItem(str(lesson_no)))
            self.table.setItem(i, 1, QTableWidgetItem(time_str))

            # Комбобокс предмета
            subject_combo = QComboBox()
            subject_combo.addItem("", None)
            for subj in self.subjects:
                subject_combo.addItem(subj["name"], subj["id"])
            # Комбобокс класса
            class_combo = QComboBox()
            class_combo.addItem("", None)
            for cls in self.classes:
                class_combo.addItem(cls["name"], cls["id"])

            if lesson_no in self.lesson_map:
                les = self.lesson_map[lesson_no]
                idx_subj = subject_combo.findData(les["subject_id"])
                if idx_subj >= 0:
                    subject_combo.setCurrentIndex(idx_subj)
                idx_cls = class_combo.findData(les["class_id"])
                if idx_cls >= 0:
                    class_combo.setCurrentIndex(idx_cls)

            self.table.setCellWidget(i, 2, subject_combo)
            self.table.setCellWidget(i, 3, class_combo)

            # Подсветка "окна" и больничного
            item_time = self.table.item(i, 1)
            if self.absent:
                item_time.setBackground(Qt.GlobalColor.red)
                # Оставляем редактируемыми для замены
            elif lesson_no in gaps:
                item_time.setBackground(Qt.GlobalColor.yellow)
                item_time.setToolTip("Окно (нет урока, но есть занятия до и после)")

        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.toggle_absence_btn = QPushButton("Снять больничный" if self.absent else "Отметить больничный")
        self.toggle_absence_btn.clicked.connect(self.toggle_absence)
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_schedule)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.toggle_absence_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def toggle_absence(self):
        if self.absent:
            db.remove_absence(self.teacher["id"], self.date_str)
            self.absent = False
            self.absent_label.setText("")
            self.toggle_absence_btn.setText("Отметить больничный")
            # Убираем красный фон
            for i in range(8):
                item = self.table.item(i, 1)
                if item:
                    item.setBackground(Qt.GlobalColor.white)  # сброс
        else:
            db.set_absence(self.teacher["id"], self.date_str)
            self.absent = True
            self.absent_label.setText("⚠ Учитель на больничном (требуется замена)")
            self.toggle_absence_btn.setText("Снять больничный")
            for i in range(8):
                item = self.table.item(i, 1)
                if item:
                    item.setBackground(Qt.GlobalColor.red)

    def save_schedule(self):
        tid = self.teacher["id"]
        # Проверка конфликтов: один учитель не может быть в двух классах одновременно
        for i in range(8):
            lesson_no = i+1
            subj_combo = self.table.cellWidget(i, 2)
            cls_combo = self.table.cellWidget(i, 3)
            if subj_combo.currentData() and cls_combo.currentData():
                # Проверяем конфликт
                if db.get_teacher_conflicts(tid, self.date_str, lesson_no):
                    QMessageBox.warning(self, "Конфликт", f"Урок {lesson_no} уже занят (конфликт расписания).")
                    return
        # Сохраняем
        for i in range(8):
            lesson_no = i+1
            subj_combo = self.table.cellWidget(i, 2)
            cls_combo = self.table.cellWidget(i, 3)
            sid = subj_combo.currentData()
            cid = cls_combo.currentData()
            if sid and cid:
                db.set_lesson(tid, self.date_str, lesson_no, sid, cid)
            else:
                db.delete_lesson(tid, self.date_str, lesson_no)
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание")
        self.resize(1000, 650)
        self.current_teacher = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Левая панель: учителя и справочники
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("<b>Учителя</b>"))
        self.teacher_list = QListWidget()
        self.teacher_list.currentItemChanged.connect(self.on_teacher_selected)
        left_panel.addWidget(self.teacher_list)

        btn_teacher_add = QPushButton("Добавить")
        btn_teacher_edit = QPushButton("Редактировать")
        btn_teacher_del = QPushButton("Удалить")
        btn_teacher_add.clicked.connect(self.add_teacher)
        btn_teacher_edit.clicked.connect(self.edit_teacher)
        btn_teacher_del.clicked.connect(self.delete_teacher)

        left_panel.addWidget(btn_teacher_add)
        left_panel.addWidget(btn_teacher_edit)
        left_panel.addWidget(btn_teacher_del)

        left_panel.addSpacing(15)
        left_panel.addWidget(QLabel("<b>Справочники</b>"))
        btn_classes = QPushButton("Классы")
        btn_subjects = QPushButton("Предметы")
        btn_classes.clicked.connect(self.manage_classes)
        btn_subjects.clicked.connect(self.manage_subjects)
        left_panel.addWidget(btn_classes)
        left_panel.addWidget(btn_subjects)

        left_panel.addStretch()
        self.report_btn = QPushButton("Отчёт за месяц")
        self.report_btn.clicked.connect(self.show_report)
        self.report_btn.setEnabled(False)
        left_panel.addWidget(self.report_btn)

        main_layout.addLayout(left_panel, 1)

        # Правая панель: календарь и информация
        right_panel = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.on_date_clicked)
        right_panel.addWidget(self.calendar)

        self.info_label = QLabel("Выберите учителя и дату в календаре.")
        self.info_label.setWordWrap(True)
        right_panel.addWidget(self.info_label)

        main_layout.addLayout(right_panel, 2)

        self.refresh_teacher_list()

    def refresh_teacher_list(self):
        self.teacher_list.clear()
        teachers = db.get_all_teachers()
        for t in teachers:
            self.teacher_list.addItem(f"{t['full_name']} (ставка: {t['desired_hours']}ч)")
            self.teacher_list.item(self.teacher_list.count()-1).setData(Qt.ItemDataRole.UserRole, t["id"])

    def on_teacher_selected(self, current, previous):
        if current:
            self.current_teacher = current.data(Qt.ItemDataRole.UserRole)
            self.report_btn.setEnabled(True)
        else:
            self.current_teacher = None
            self.report_btn.setEnabled(False)

    def on_date_clicked(self, date):
        if not self.current_teacher:
            QMessageBox.information(self, "Информация", "Сначала выберите учителя из списка.")
            return
        teacher = db.get_all_teachers()  # неэффективно, но для каркаса подойдёт
        teacher_data = next((t for t in teacher if t["id"] == self.current_teacher), None)
        if not teacher_data:
            return
        dlg = LessonDialog(teacher_data, date, self)
        dlg.exec()
        # После закрытия можно обновить статистику на info_label
        self.update_info_label(date)

    def update_info_label(self, date):
        if not self.current_teacher:
            return
        teacher = next((t for t in db.get_all_teachers() if t["id"] == self.current_teacher), None)
        if not teacher:
            return
        hours = db.teacher_hours_in_month(self.current_teacher, date.year(), date.month())
        self.info_label.setText(f"{teacher['full_name']}: {hours} ч. за {date.toString('MMMM yyyy')}")

    # Диалоги добавления/редактирования учителя
    def add_teacher(self):
        dlg = TeacherDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            db.add_teacher(data["full_name"], data["specialization"], data["desired_hours"])
            self.refresh_teacher_list()

    def edit_teacher(self):
        if not self.current_teacher:
            return
        teacher = next((t for t in db.get_all_teachers() if t["id"] == self.current_teacher), None)
        if not teacher:
            return
        dlg = TeacherDialog(self, teacher)
        if dlg.exec():
            data = dlg.get_data()
            db.update_teacher(data["id"], data["full_name"], data["specialization"], data["desired_hours"])
            self.refresh_teacher_list()

    def delete_teacher(self):
        if not self.current_teacher:
            return
        ret = QMessageBox.question(self, "Подтверждение", "Удалить учителя и всё его расписание?")
        if ret == QMessageBox.StandardButton.Yes:
            db.delete_teacher(self.current_teacher)
            self.refresh_teacher_list()
            self.current_teacher = None

    # Управление справочниками
    def manage_classes(self):
        items = db.get_all_classes()
        names = [c["name"] for c in items]
        item, ok = QInputDialog.getItem(self, "Классы", "Выберите класс для удаления или введите новый:", names + ["<Добавить новый>"], editable=True)
        if ok and item:
            if item == "<Добавить новый>":
                text, ok2 = QInputDialog.getText(self, "Новый класс", "Название:")
                if ok2 and text.strip():
                    db.add_class(text.strip())
            else:
                ret = QMessageBox.question(self, "Удаление", f"Удалить класс '{item}'?")
                if ret == QMessageBox.StandardButton.Yes:
                    cls = next(c for c in items if c["name"] == item)
                    db.delete_class(cls["id"])

    def manage_subjects(self):
        items = db.get_all_subjects()
        names = [s["name"] for s in items]
        item, ok = QInputDialog.getItem(self, "Предметы", "Выберите предмет для удаления или введите новый:", names + ["<Добавить новый>"], editable=True)
        if ok and item:
            if item == "<Добавить новый>":
                text, ok2 = QInputDialog.getText(self, "Новый предмет", "Название:")
                if ok2 and text.strip():
                    db.add_subject(text.strip())
            else:
                ret = QMessageBox.question(self, "Удаление", f"Удалить предмет '{item}'?")
                if ret == QMessageBox.StandardButton.Yes:
                    subj = next(s for s in items if s["name"] == item)
                    db.delete_subject(subj["id"])

    def show_report(self):
        if not self.current_teacher:
            return
        # Спрашиваем месяц
        date = self.calendar.selectedDate()
        year, month = date.year(), date.month()
        hours = db.teacher_hours_in_month(self.current_teacher, year, month)
        teacher = next((t for t in db.get_all_teachers() if t["id"] == self.current_teacher), None)
        QMessageBox.information(self, "Отчёт", f"{teacher['full_name']}\nПроведено часов в {date.toString('MMMM yyyy')}: {hours}")