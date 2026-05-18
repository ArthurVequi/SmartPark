import sqlite3

def init_db():
    conn = sqlite3.connect('estacionamento.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            x1 INTEGER,
            y1 INTEGER,
            x2 INTEGER,
            y2 INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def carregar_vagas():
    conn = sqlite3.connect('estacionamento.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, x1, y1, x2, y2 FROM vagas ORDER BY id ASC')
    vagas_db = cursor.fetchall()
    conn.close()
    return vagas_db

def salvar_vaga(x1, y1, x2, y2):
    conn = sqlite3.connect('estacionamento.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO vagas (x1, y1, x2, y2) VALUES (?, ?, ?, ?)', (x1, y1, x2, y2))
    conn.commit()
    vaga_id = cursor.lastrowid
    conn.close()
    return vaga_id

def remover_vaga(vaga_id):
    conn = sqlite3.connect('estacionamento.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vagas WHERE id = ?', (vaga_id,))
    conn.commit()
    conn.close()
