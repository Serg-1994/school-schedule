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


# ─── НОВЫЕ ФУНКЦИИ ДЛЯ ПОДДЕРЖКИ БОЛЬНИЧНЫХ И ЗАМЕН ───

def add_absence_range(teacher_id, start_date, end_date, reason="больничный"):
    """Регистрирует больничный и переводит все активные уроки в статус 'болеет'"""
    import datetime
    with get_db() as conn:
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        curr = start
        while curr <= end:
            d_str = curr.strftime("%Y-%m-%d")
            conn.execute("""
                INSERT OR REPLACE INTO absences (teacher_id, date, reason)
                VALUES (?, ?, ?)
            """, (teacher_id, d_str, reason))
            
            # Меняем статус обычных уроков на 'болеет'
            conn.execute("""
                UPDATE schedule SET status = 'болеет'
                WHERE teacher_id = ? AND date = ? AND status = 'работает'
            """, (teacher_id, d_str))
            curr += datetime.timedelta(days=1)
        conn.commit()

def get_teacher_absences_for_month(teacher_id, year, month):
    """Возвращает список дат больничных учителя за указанный месяц"""
    with get_db() as conn:
        prefix = f"{year}-{month:02d}%"
        rows = conn.execute(
            "SELECT date FROM absences WHERE teacher_id = ? AND date LIKE ?",
            (teacher_id, prefix)
        ).fetchall()
        return [r['date'] for r in rows]

def get_substitutions_for_month(teacher_id, year, month):
    """Возвращает список дат, где у учителя стоит статус замена"""
    with get_db() as conn:
        prefix = f"{year}-{month:02d}%"
        rows = conn.execute(
            "SELECT DISTINCT date FROM schedule WHERE teacher_id = ? AND date LIKE ? AND status = 'на замене'",
            (teacher_id, prefix)
        ).fetchall()
        return [r['date'] for r in rows]

def check_teacher_busy(teacher_id, date_str, lesson_number):
    """Проверяет, ведет ли учитель свой собственный плановый урок в это время"""
    with get_db() as conn:
        res = conn.execute("""
            SELECT 1 FROM schedule 
            WHERE teacher_id = ? AND date = ? AND lesson_number = ? AND status = 'работает'
        """, (teacher_id, date_str, lesson_number)).fetchone()
        return bool(res)