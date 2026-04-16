import sqlite3
import bcrypt

DB_PATH = 'users.db'

admin_password = '87347748'
hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())

with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (id, username, password, approved) VALUES (?, ?, ?, ?)', (1, 'admin', hashed.decode('utf-8'), 1))
    conn.commit()
print('Usuário admin criado com sucesso!')
