import json
from database.database import Database

class Teacher:
    def __init__(self, id=None, name='', specialization=None, rate=0.0):
        self.id = id
        self.name = name
        self.specialization = specialization or []
        self.rate = rate

    @staticmethod
    def get_all():
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teachers ORDER BY name')
        rows = cursor.fetchall()
        db.close()
        return [
            Teacher(
                id=row[0],
                name=row[1],
                specialization=json.loads(row[2]) if row[2] else [],
                rate=row[3]
            )
            for row in rows
        ]

    def save(self):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        if self.id:
            cursor.execute(
                'UPDATE teachers SET name=?, specialization=?, rate=? WHERE id=?',
                (self.name, json.dumps(self.specialization, ensure_ascii=False), self.rate, self.id)
            )
        else:
            cursor.execute(
                'INSERT INTO teachers (name, specialization, rate) VALUES (?, ?, ?)',
                (self.name, json.dumps(self.specialization, ensure_ascii=False), self.rate)
            )
            self.id = cursor.lastrowid
        conn.commit()
        db.close()

    @staticmethod
    def get_by_id(teacher_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teachers WHERE id=?', (teacher_id,))
        row = cursor.fetchone()
        db.close()
        if row:
            return Teacher(
                id=row[0],
                name=row[1],
                specialization=json.loads(row[2]) if row[2] else [],
                rate=row[3]
            )
        return None

    @staticmethod
    def get_by_specialization(subject_name):
        normalized = subject_name.strip().lower()
        return [
            t for t in Teacher.get_all()
            if any(
                normalized == s.strip().lower() or
                normalized in s.strip().lower() or
                s.strip().lower() in normalized
                for s in t.specialization
            )
        ]

    def delete(self):
        if not self.id:
            return
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        # Сначала удаляем все уроки учителя (вызывающий код уже сделал переназначение)
        cursor.execute('DELETE FROM teachers WHERE id=?', (self.id,))
        conn.commit()
        db.close()
