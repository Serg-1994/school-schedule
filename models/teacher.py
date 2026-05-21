import json
from database.database import Database

class Teacher:
    def __init__(self, id=None, name='', specialization=None, rate=0.0):
        self.id = id
        self.name = name
        self.specialization = specialization or []  # список предметов
        self.rate = rate

    @staticmethod
    def get_all():
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teachers')
        rows = cursor.fetchall()
        db.close()
        teachers = []
        for row in rows:
            teachers.append(Teacher(
                id=row[0],
                name=row[1],
                specialization=json.loads(row[2]) if row[2] else [],
                rate=row[3]
            ))
        return teachers

    def save(self):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE teachers SET name=?, specialization=?, rate=? WHERE id=?
            ''', (self.name, json.dumps(self.specialization), self.rate, self.id))
        else:
            cursor.execute('''
                INSERT INTO teachers (name, specialization, rate) VALUES (?, ?, ?)
            ''', (self.name, json.dumps(self.specialization), self.rate))
            self.id = cursor.lastrowid
        conn.commit()
        db.close()

    @staticmethod
    def get_by_id(id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teachers WHERE id=?', (id,))
        row = cursor.fetchone()
        db.close()
        if row:
            return Teacher(id=row[0], name=row[1], specialization=json.loads(row[2]) if row[2] else [], rate=row[3])
        return None

    @staticmethod
    def get_by_specialization(subject_name):
        normalized = subject_name.strip().lower()
        matching = []
        for teacher in Teacher.get_all():
            for spec in teacher.specialization:
                if normalized == spec.strip().lower() or normalized in spec.strip().lower() or spec.strip().lower() in normalized:
                    matching.append(teacher)
                    break
        return matching

    def delete(self):
        if self.id:
            db = Database()
            conn = db.connect()
            cursor = conn.cursor()
            # Проверить, есть ли связанные записи в schedule
            cursor.execute('SELECT COUNT(*) FROM schedule WHERE teacher_id=?', (self.id,))
            count = cursor.fetchone()[0]
            if count > 0:
                raise ValueError(f"Нельзя удалить учителя {self.name}, так как у него есть {count} уроков в расписании.")
            cursor.execute('DELETE FROM teachers WHERE id=?', (self.id,))
            conn.commit()
            db.close()