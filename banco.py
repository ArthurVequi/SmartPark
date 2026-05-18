import sqlite3
import datetime
import time

def init_db():
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registro_vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vaga_id INTEGER,
            entrada INTEGER,
            saida INTEGER,
            valor_pago REAL
        )
    ''')
    conn.commit()
    conn.close()

def carregar_vagas():
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('SELECT id, x1, y1, x2, y2 FROM vagas ORDER BY id ASC')
    vagas_db = cursor.fetchall()
    conn.close()
    return vagas_db

def salvar_vaga(x1, y1, x2, y2):
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO vagas (x1, y1, x2, y2) VALUES (?, ?, ?, ?)', (x1, y1, x2, y2))
    conn.commit()
    vaga_id = cursor.lastrowid
    conn.close()
    return vaga_id

def remover_vaga(vaga_id):
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vagas WHERE id = ?', (vaga_id,))
    conn.commit()
    conn.close()

# =============================================================
# OPERAÇÕES DE REGISTRO E EVENTOS
# =============================================================

def registrar_entrada(vaga_id, entrada_timestamp):
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    # Verifica se já existe uma sessão ativa (caso ocorra sobreposição de detecção)
    cursor.execute('SELECT id FROM registro_vagas WHERE vaga_id = ? AND saida IS NULL', (vaga_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO registro_vagas (vaga_id, entrada, saida, valor_pago) VALUES (?, ?, NULL, NULL)', 
                       (vaga_id, int(entrada_timestamp)))
        conn.commit()
    conn.close()

def registrar_saida(vaga_id, saida_timestamp, valor_pago):
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    # Pega o registro ativo mais recente para essa vaga
    cursor.execute('SELECT id FROM registro_vagas WHERE vaga_id = ? AND saida IS NULL ORDER BY entrada DESC LIMIT 1', (vaga_id,))
    row = cursor.fetchone()
    if row:
        session_id = row[0]
        cursor.execute('UPDATE registro_vagas SET saida = ?, valor_pago = ? WHERE id = ?', 
                       (int(saida_timestamp), float(valor_pago), session_id))
        conn.commit()
    conn.close()

def obter_sessoes_ativas():
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('SELECT vaga_id, entrada FROM registro_vagas WHERE saida IS NULL ORDER BY entrada DESC')
    rows = cursor.fetchall()
    conn.close()
    return [{'vaga_id': r[0], 'entrada': r[1]} for r in rows]

def obter_logs():
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    # Obtém todas as sessões registradas
    cursor.execute('SELECT vaga_id, entrada, saida FROM registro_vagas ORDER BY entrada DESC')
    rows = cursor.fetchall()
    conn.close()
    
    eventos = []
    for vaga_id, entrada, saida in rows:
        dt_entrada = datetime.datetime.fromtimestamp(entrada).strftime('%d/%m %H:%M:%S')
        
        # Evento de entrada
        eventos.append({
            'data_hora': dt_entrada,
            'timestamp': entrada,
            'vaga_id': f"{vaga_id:02d}",
            'acao': 'Entrada',
            'duracao': '-'
        })
        
        # Evento de saída (se já saiu)
        if saida:
            dt_saida = datetime.datetime.fromtimestamp(saida).strftime('%d/%m %H:%M:%S')
            duracao_seg = saida - entrada
            
            # Formata a duração de permanência
            minutos = duracao_seg // 60
            if minutos < 60:
                duracao_str = f"{minutos}min"
            else:
                horas = minutos // 60
                mins = minutos % 60
                duracao_str = f"{horas}h {mins}m"
                
            eventos.append({
                'data_hora': dt_saida,
                'timestamp': saida,
                'vaga_id': f"{vaga_id:02d}",
                'acao': 'Saída',
                'duracao': duracao_str
            })
            
    # Ordena os eventos combinados pelo timestamp descendente
    eventos.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Remove o timestamp auxiliar
    for e in eventos:
        del e['timestamp']
        
    return eventos[:50]  # Limita aos últimos 50 eventos para performance

def obter_resumo_financeiro():
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    
    agora = datetime.datetime.now()
    
    # Início do dia de hoje (00:00:00)
    inicio_dia = int(agora.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    # Início da semana (Segunda-feira)
    inicio_semana = int((agora - datetime.timedelta(days=agora.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    # Início do mês (Dia 1)
    inicio_mes = int(agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    # Diário
    cursor.execute('SELECT SUM(valor_pago) FROM registro_vagas WHERE saida >= ? AND saida IS NOT NULL', (inicio_dia,))
    diario = cursor.fetchone()[0] or 0.0
    
    # Semanal
    cursor.execute('SELECT SUM(valor_pago) FROM registro_vagas WHERE saida >= ? AND saida IS NOT NULL', (inicio_semana,))
    semanal = cursor.fetchone()[0] or 0.0
    
    # Mensal
    cursor.execute('SELECT SUM(valor_pago) FROM registro_vagas WHERE saida >= ? AND saida IS NOT NULL', (inicio_mes,))
    mensal = cursor.fetchone()[0] or 0.0
    
    conn.close()
    
    return {
        'diario': round(diario, 2),
        'semanal': round(semanal, 2),
        'mensal': round(mensal, 2)
    }

