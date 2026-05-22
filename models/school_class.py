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
        cursor.execute('SELECT * FROM classes ORDER BY name')
        rows = cursor.fetchall()
        db.close()
        return [Class(id=row[0], name=row[1]) for row in rows]

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
        if not self.id:
            return
        db = Database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM classes WHERE id=?', (self.id,))
        conn.commit()
        db.close()
