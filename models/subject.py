from database.database import Database

class Subject:
    def __init__(self, id=None, name=''):
        self.id = id
        self.name = name

    @staticmethod
    def get_all():
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subjects')
        rows = cursor.fetchall()
        db.close()
        subjects = []
        for row in rows:
            subjects.append(Subject(id=row[0], name=row[1]))
        return subjects

    @staticmethod
    def get_by_id(subject_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subjects WHERE id=?', (subject_id,))
        row = cursor.fetchone()
        db.close()
        if row:
            return Subject(id=row[0], name=row[1])
        return None

    def save(self):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('UPDATE subjects SET name=? WHERE id=?', (self.name, self.id))
        else:
            cursor.execute('INSERT INTO subjects (name) VALUES (?)', (self.name,))
            self.id = cursor.lastrowid
        conn.commit()
        db.close()

    def delete(self):
        if self.id:
            db = Database()
            conn = db.connect()
            cursor = conn.cursor()
            # Проверить, есть ли связанные записи в schedule
            cursor.execute('SELECT COUNT(*) FROM schedule WHERE subject_id=?', (self.id,))
            count = cursor.fetchone()[0]
            if count > 0:
                raise ValueError(f"Нельзя удалить предмет {self.name}, так как он используется в {count} уроках.")
            cursor.execute('DELETE FROM subjects WHERE id=?', (self.id,))
            conn.commit()
            db.close()