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

        # Миграции: переименовать старые колонки если БД создана старой версией
        if table_has_column(conn, 'teachers', 'full_name') and not table_has_column(conn, 'teachers', 'name'):
            conn.execute('ALTER TABLE teachers RENAME COLUMN full_name TO name')
        if table_has_column(conn, 'teachers', 'desired_hours') and not table_has_column(conn, 'teachers', 'rate'):
            conn.execute('ALTER TABLE teachers RENAME COLUMN desired_hours TO rate')
        if table_has_column(conn, 'schedule', 'id') and not table_has_column(conn, 'schedule', 'status'):
            conn.execute("ALTER TABLE schedule ADD COLUMN status TEXT DEFAULT 'работает'")

# --- Логика Больничных и Замен ---

def add_absence_and_update_schedule(teacher_id, start_date, end_date, reason="больничный"):
    """
    Фиксирует больничный в таблице absences и автоматически переводит 
    все запланированные уроки учителя в этот период в статус 'болеет'.
    """
    with get_db() as conn:
        # 1. Записываем дни отсутствия (для простоты генерируем записи по дням)
        # В реальном GUI можно передать список дат или пройтись циклом от start до end
        import datetime
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            conn.execute("""
                INSERT OR REPLACE INTO absences (teacher_id, date, reason)
                VALUES (?, ?, ?)
            """, (teacher_id, date_str, reason))
            
            # 2. Меняем статус уроков этого учителя на 'болеет' на этот день
            conn.execute("""
                UPDATE schedule 
                SET status = 'болеет'
                WHERE teacher_id = ? AND date = ? AND status = 'работает'
            """, (teacher_id, date_str))
            
            current += datetime.timedelta(days=1)
            
        conn.commit()

def get_available_teachers_for_lesson(date_str, lesson_number, subject_id):
    """
    Возвращает список ВСЕХ учителей с отметкой, свободны они (зеленые) или заняты (красные).
    Приоритет отдается тем, у кого совпадает предмет (специализация).
    """
    with get_db() as conn:
        # Получаем список учителей и проверяем, есть ли у них уроки в это время
        sql = """
            SELECT t.id, t.name, t.specialization,
                   (SELECT COUNT(*) FROM schedule s WHERE s.teacher_id = t.id AND s.date = ? AND s.lesson_number = ?) as is_busy,
                   (SELECT COUNT(*) FROM absences a WHERE a.teacher_id = t.id AND a.date = ?) as is_absent
            FROM teachers t
            ORDER BY t.name
        """
        rows = conn.execute(sql, (date_str, lesson_number, date_str)).fetchall()
        
        result = []
        for row in rows:
            # Если учитель сам на больничном, вообще его не предлагаем
            if row['is_absent'] > 0:
                continue
                
            status_color = "green" if row['is_busy'] == 0 else "red"
            result.append({
                "id": row['id'],
                "name": row['name'],
                "specialization": row['specialization'],
                "status_color": status_color
            })
        return result

def assign_substitution(sub_teacher_id, original_lesson_id):
    """
    Назначает учителя на замену.
    Создает дубликат урока, но для нового учителя и со статусом 'замена'.
    """
    with get_db() as conn:
        # Получаем данные оригинального урока
        lesson = conn.execute("SELECT * FROM schedule WHERE id = ?", (original_lesson_id,)).fetchone()
        if not lesson:
            return False
            
        # Создаем запись замены
        conn.execute("""
            INSERT INTO schedule (teacher_id, class_id, subject_id, date, lesson_number, status)
            VALUES (?, ?, ?, ?, ?, 'замена')
        """, (sub_teacher_id, lesson['class_id'], lesson['subject_id'], lesson['date'], lesson['lesson_number'],))
        
        # Обновляем оригинальный урок, связывая его (опционально, можно хранить ID замены в статусе)
        conn.commit()
        return True
    
        conn.commit()
