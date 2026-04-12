import sqlite3

DB_PATH = 'users.db'

with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (id, username, password, approved) VALUES (?, ?, ?, ?)', (1, 'admin', '87347748', 1))
    conn.commit()
print('Usuário admin criado com sucesso!')
