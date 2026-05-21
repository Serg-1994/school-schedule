import sqlite3
from contextlib import contextmanager

DB_NAME = "school_schedule.db"

class Database:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._conn = None

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_name)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def table_has_column(conn, table, column):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT,
                rate INTEGER DEFAULT 18
            );
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                lesson_number INTEGER NOT NULL CHECK(lesson_number BETWEEN 1 AND 8),
                status TEXT DEFAULT 'работает',
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                UNIQUE(teacher_id, date, lesson_number)
            );
            CREATE TABLE IF NOT EXISTS absences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                reason TEXT DEFAULT 'больничный',
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                UNIQUE(teacher_id, date)
            );
            CREATE INDEX IF NOT EXISTS idx_schedule_teacher_date ON schedule(teacher_id, date);
            CREATE INDEX IF NOT EXISTS idx_schedule_class_date ON schedule(class_id, date);
            CREATE INDEX IF NOT EXISTS idx_schedule_subject ON schedule(subject_id);
            CREATE INDEX IF NOT EXISTS idx_absences_teacher_date ON absences(teacher_id, date);
        """)

        if table_has_column(conn, 'teachers', 'full_name') and not table_has_column(conn, 'teachers', 'name'):
            conn.execute('ALTER TABLE teachers RENAME COLUMN full_name TO name')
        if table_has_column(conn, 'teachers', 'desired_hours') and not table_has_column(conn, 'teachers', 'rate'):
            conn.execute('ALTER TABLE teachers RENAME COLUMN desired_hours TO rate')
        if table_has_column(conn, 'schedule', 'id') and not table_has_column(conn, 'schedule', 'status'):
            conn.execute("ALTER TABLE schedule ADD COLUMN status TEXT DEFAULT 'работает'")

        conn.commit()

# ----- Учителя -----
def get_all_teachers():
    with get_db() as conn:
        return conn.execute("SELECT * FROM teachers ORDER BY full_name").fetchall()

def add_teacher(full_name, specialization="", desired_hours=18):
    with get_db() as conn:
        cur = conn.execute("INSERT INTO teachers (full_name, specialization, desired_hours) VALUES (?,?,?)",
                           (full_name, specialization, desired_hours))
        conn.commit()
        return cur.lastrowid

def update_teacher(teacher_id, full_name, specialization, desired_hours):
    with get_db() as conn:
        conn.execute("UPDATE teachers SET full_name=?, specialization=?, desired_hours=? WHERE id=?",
                     (full_name, specialization, desired_hours, teacher_id))
        conn.commit()

def delete_teacher(teacher_id):
    with get_db() as conn:
        conn.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
        conn.commit()

# ----- Классы -----
def get_all_classes():
    with get_db() as conn:
        return conn.execute("SELECT * FROM classes ORDER BY name").fetchall()

def add_class(name):
    with get_db() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO classes (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid

def delete_class(class_id):
    with get_db() as conn:
        conn.execute("DELETE FROM classes WHERE id=?", (class_id,))
        conn.commit()

# ----- Предметы -----
def get_all_subjects():
    with get_db() as conn:
        return conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()

def add_subject(name):
    with get_db() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid

def delete_subject(subject_id):
    with get_db() as conn:
        conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        conn.commit()

# ----- Расписание -----
def get_schedule_for_teacher_date(teacher_id, date_str):
    with get_db() as conn:
        return conn.execute("""
            SELECT s.lesson_number, s.subject_id, sub.name as subject_name,
                   s.class_id, c.name as class_name
            FROM schedule s
            JOIN subjects sub ON s.subject_id = sub.id
            JOIN classes c ON s.class_id = c.id
            WHERE s.teacher_id = ? AND s.date = ?
            ORDER BY s.lesson_number
        """, (teacher_id, date_str)).fetchall()

def set_lesson(teacher_id, date_str, lesson_number, subject_id, class_id):
    with get_db() as conn:
        # Используем INSERT OR REPLACE для соблюдения UNIQUE
        conn.execute("""
            INSERT OR REPLACE INTO schedule (teacher_id, class_id, subject_id, date, lesson_number)
            VALUES (?,?,?,?,?)
        """, (teacher_id, class_id, subject_id, date_str, lesson_number))
        conn.commit()

def delete_lesson(teacher_id, date_str, lesson_number):
    with get_db() as conn:
        conn.execute("DELETE FROM schedule WHERE teacher_id=? AND date=? AND lesson_number=?",
                     (teacher_id, date_str, lesson_number))
        conn.commit()

def get_teacher_conflicts(teacher_id, date_str, lesson_number):
    """Проверяет, есть ли другие уроки у того же учителя в это же время (должна быть 0 записей, если конфликта нет)"""
    with get_db() as conn:
        row = conn.execute("""
            SELECT COUNT(*) FROM schedule
            WHERE teacher_id=? AND date=? AND lesson_number=?
        """, (teacher_id, date_str, lesson_number)).fetchone()
        return row[0] > 0

def get_conflicting_teacher_entry(teacher_id, date_str, lesson_number):
    with get_db() as conn:
        return conn.execute("""
            SELECT s.id, s.teacher_id, s.class_id, s.subject_id, s.date, s.lesson_number, s.status,
                   t.name as teacher_name, c.name as class_name, sub.name as subject_name
            FROM schedule s
            JOIN teachers t ON s.teacher_id = t.id
            JOIN classes c ON s.class_id = c.id
            JOIN subjects sub ON s.subject_id = sub.id
            WHERE s.teacher_id=? AND s.date=? AND s.lesson_number=?
        """, (teacher_id, date_str, lesson_number)).fetchone()

def get_conflicting_class_entry(class_id, date_str, lesson_number):
    with get_db() as conn:
        return conn.execute("""
            SELECT s.id, s.teacher_id, s.class_id, s.subject_id, s.date, s.lesson_number, s.status,
                   t.name as teacher_name, c.name as class_name, sub.name as subject_name
            FROM schedule s
            JOIN teachers t ON s.teacher_id = t.id
            JOIN classes c ON s.class_id = c.id
            JOIN subjects sub ON s.subject_id = sub.id
            WHERE s.class_id=? AND s.date=? AND s.lesson_number=?
        """, (class_id, date_str, lesson_number)).fetchone()

# ----- Отсутствия -----
def set_absence(teacher_id, date_str, reason="больничный"):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO absences (teacher_id, date, reason) VALUES (?,?,?)",
                     (teacher_id, date_str, reason))
        conn.commit()

def remove_absence(teacher_id, date_str):
    with get_db() as conn:
        conn.execute("DELETE FROM absences WHERE teacher_id=? AND date=?", (teacher_id, date_str))
        conn.commit()

def is_absent(teacher_id, date_str):
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM absences WHERE teacher_id=? AND date=?", (teacher_id, date_str)).fetchone()
        return row is not None

# ----- Отчёт -----
def teacher_hours_in_month(teacher_id, year, month):
    """Сумма уроков (каждый урок = 1 академический час) за указанный месяц."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    with get_db() as conn:
        row = conn.execute("""
            SELECT COUNT(*) FROM schedule
            WHERE teacher_id=? AND date >= ? AND date < ?
        """, (teacher_id, start_date, end_date)).fetchone()
        return row[0]