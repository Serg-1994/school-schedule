from database.database import Database

class Class:
    def __init__(self, id=None, name=''):
        self.id = id
        self.name = name

    @staticmethod
    def get_all():
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM classes')
        rows = cursor.fetchall()
        db.close()
        classes = []
        for row in rows:
            classes.append(Class(id=row[0], name=row[1]))
        return classes

    def save(self):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('UPDATE classes SET name=? WHERE id=?', (self.name, self.id))
        else:
            cursor.execute('INSERT INTO classes (name) VALUES (?)', (self.name,))
            self.id = cursor.lastrowid
        conn.commit()
        db.close()

    @staticmethod
    def get_by_id(class_id):
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM classes WHERE id=?', (class_id,))
        row = cursor.fetchone()
        db.close()
        if row:
            return Class(id=row[0], name=row[1])
        return None

    def delete(self):
        if self.id:
            db = Database()
            conn = db.connect()
            cursor = conn.cursor()
            # Проверить, есть ли связанные записи в schedule
            cursor.execute('SELECT COUNT(*) FROM schedule WHERE class_id=?', (self.id,))
            count = cursor.fetchone()[0]
            if count > 0:
                raise ValueError(f"Нельзя удалить класс {self.name}, так как у него есть {count} уроков в расписании.")
            cursor.execute('DELETE FROM classes WHERE id=?', (self.id,))
            conn.commit()
            db.close()