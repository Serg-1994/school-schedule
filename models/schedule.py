from database.database import Database

class Schedule:
    def __init__(self, id=None, teacher_id=None, class_id=None, subject_id=None, date='', lesson_number=None, status='работает'):
        self.id = id
        self.teacher_id = teacher_id
        self.class_id = class_id
        self.subject_id = subject_id
        self.date = date
        self.lesson_number = lesson_number
        self.status = status or 'работает'

    @staticmethod
    def _row_to_schedule(row):
        status = row[6] if len(row) > 6 else 'работает'
        return Schedule(
            id=row[0],
            teacher_id=row[1],
            class_id=row[2],
            subject_id=row[3],
            date=row[4],
            lesson_number=row[5],
            status=status
        )

    @staticmethod
    def get_by_date(date):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE date=?', (date,))
        rows = cursor.fetchall()
        db.close()
        return [Schedule._row_to_schedule(row) for row in rows]

    def save(self):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('UPDATE schedule SET teacher_id=?, class_id=?, subject_id=?, date=?, lesson_number=?, status=? WHERE id=?',
                           (self.teacher_id, self.class_id, self.subject_id, self.date, self.lesson_number, self.status, self.id))
        else:
            cursor.execute('INSERT INTO schedule (teacher_id, class_id, subject_id, date, lesson_number, status) VALUES (?, ?, ?, ?, ?, ?)',
                           (self.teacher_id, self.class_id, self.subject_id, self.date, self.lesson_number, self.status))
            self.id = cursor.lastrowid
        conn.commit()
        db.close()

    def delete(self):
        if not self.id:
            return
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schedule WHERE id=?', (self.id,))
        conn.commit()
        db.close()

    @staticmethod
    def get_by_date_and_teacher(date, teacher_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE date=? AND teacher_id=?', (date, teacher_id))
        rows = cursor.fetchall()
        db.close()
        return [Schedule._row_to_schedule(row) for row in rows]

    @staticmethod
    def get_daily_lesson_counts_for_teacher_month(teacher_id, year, month):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        cursor.execute('''
            SELECT date, COUNT(*) as lessons
            FROM schedule
            WHERE teacher_id=? AND date >= ? AND date < ?
            GROUP BY date
        ''', (teacher_id, start_date, end_date))
        rows = cursor.fetchall()
        db.close()
        return {row[0]: row[1] for row in rows}

    @staticmethod
    def get_conflicting_teacher_entry(teacher_id, date, lesson_number):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.teacher_id, s.class_id, s.subject_id, s.date, s.lesson_number, s.status
            FROM schedule s
            WHERE s.teacher_id=? AND s.date=? AND s.lesson_number=?
        ''', (teacher_id, date, lesson_number))
        row = cursor.fetchone()
        db.close()
        return row

    @staticmethod
    def get_conflicting_class_entry(class_id, date, lesson_number):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.teacher_id, s.class_id, s.subject_id, s.date, s.lesson_number, s.status
            FROM schedule s
            WHERE s.class_id=? AND s.date=? AND s.lesson_number=?
        ''', (class_id, date, lesson_number))
        row = cursor.fetchone()
        db.close()
        return row

    @staticmethod
    def get_by_teacher_date_range(teacher_id, start_date, end_date):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE teacher_id=? AND date >= ? AND date <= ?',
                       (teacher_id, start_date, end_date))
        rows = cursor.fetchall()
        db.close()
        return [Schedule._row_to_schedule(row) for row in rows]

    @staticmethod
    def get_by_teacher(teacher_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE teacher_id=? ORDER BY date, lesson_number', (teacher_id,))
        rows = cursor.fetchall()
        db.close()
        return [Schedule._row_to_schedule(row) for row in rows]

    @staticmethod
    def get_by_class(class_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE class_id=? ORDER BY date, lesson_number', (class_id,))
        rows = cursor.fetchall()
        db.close()
        return [Schedule._row_to_schedule(row) for row in rows]

    @staticmethod
    def get_by_subject(subject_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE subject_id=? ORDER BY date, lesson_number', (subject_id,))
        rows = cursor.fetchall()
        db.close()
        return [Schedule._row_to_schedule(row) for row in rows]

    @staticmethod
    def get_by_id(schedule_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule WHERE id=?', (schedule_id,))
        row = cursor.fetchone()
        db.close()
        return Schedule._row_to_schedule(row) if row else None
