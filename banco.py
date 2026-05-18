# Camada de banco de dados SQLite e cálculos de estatísticas analíticas

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

def obter_entrada_ativa(vaga_id):
    """
    Retorna o timestamp de entrada ativo (sem saída registrada) para uma vaga específica, ou None.
    """
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    cursor.execute('SELECT entrada FROM registro_vagas WHERE vaga_id = ? AND saida IS NULL ORDER BY entrada DESC LIMIT 1', (vaga_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

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

def obter_resumo_relatorios():
    conn = sqlite3.connect('estacionamento.db', timeout=10.0)
    cursor = conn.cursor()
    
    agora = datetime.datetime.now()
    agora_ts = int(time.time())
    trinta_dias_atras = agora_ts - 30 * 86400
    
    # 1. Média de Permanência (últimos 30 dias)
    cursor.execute('SELECT AVG(saida - entrada) FROM registro_vagas WHERE saida IS NOT NULL AND entrada >= ?', (trinta_dias_atras,))
    avg_perm = cursor.fetchone()[0]
    if avg_perm is None:
        cursor.execute('SELECT AVG(saida - entrada) FROM registro_vagas WHERE saida IS NOT NULL')
        avg_perm = cursor.fetchone()[0] or 0.0
        
    avg_perm_seg = int(avg_perm)
    if avg_perm_seg == 0:
        perm_str = "0min"
    else:
        minutos = avg_perm_seg // 60
        if minutos < 60:
            perm_str = f"{minutos}min"
        else:
            horas = minutos // 60
            mins = minutos % 60
            perm_str = f"{horas}h {mins}m"
            
    # 2. Média de Ocupação Diária
    cursor.execute('SELECT COUNT(*) FROM vagas')
    total_vagas = cursor.fetchone()[0] or 0
    
    taxa_ocupacao_str = "0.0%"
    janela_tempo = 30 * 86400
    if total_vagas > 0:
        cursor.execute('SELECT MIN(entrada) FROM registro_vagas')
        primeiro_registro = cursor.fetchone()[0]
        
        if primeiro_registro:
            tempo_decorrido = agora_ts - primeiro_registro
            janela_tempo = min(30 * 86400, max(3600, tempo_decorrido)) # Mínimo de 1h de janela
        else:
            janela_tempo = 30 * 86400
            
        cursor.execute('''
            SELECT SUM(
                CASE 
                    WHEN saida IS NOT NULL THEN (saida - MAX(entrada, ?))
                    ELSE (? - MAX(entrada, ?))
                END
            ) 
            FROM registro_vagas 
            WHERE (saida IS NULL OR saida >= ?) AND entrada <= ?
        ''', (trinta_dias_atras, agora_ts, trinta_dias_atras, trinta_dias_atras, agora_ts))
        
        segundos_ocupados = cursor.fetchone()[0] or 0.0
        segundos_totais_disponiveis = total_vagas * janela_tempo
        
        taxa_ocupacao = (segundos_ocupados / segundos_totais_disponiveis) * 100
        taxa_ocupacao = min(100.0, taxa_ocupacao)
        taxa_ocupacao_str = f"{taxa_ocupacao:.1f}%"
        
    # 3. Dia de Maior Movimento
    cursor.execute('''
        SELECT 
            strftime('%Y-%m-%d', datetime(entrada, 'unixepoch', 'localtime')) as dia, 
            COUNT(*) as qtd 
        FROM registro_vagas 
        WHERE entrada >= ?
        GROUP BY dia 
        ORDER BY qtd DESC, dia DESC
        LIMIT 1
    ''', (trinta_dias_atras,))
    
    row_dia = cursor.fetchone()
    dia_str = "N/A"
    dia_data = "N/A"
    
    if row_dia:
        dia_yyyy_mm_dd = row_dia[0]
        try:
            dt = datetime.datetime.strptime(dia_yyyy_mm_dd, '%Y-%m-%d')
            dias_semana_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            dia_semana_str = dias_semana_pt[dt.weekday()]
            dia_str = f"{dia_semana_str}, {dt.strftime('%d/%m')}"
            dia_data = dt.strftime('%d/%m/%Y')
        except Exception:
            dia_str = dia_yyyy_mm_dd
            dia_data = dia_yyyy_mm_dd

    # =============================================================
    # CÁLCULOS DOS GRÁFICOS DINÂMICOS
    # =============================================================
    
    # Busca todas as sessões dos últimos 30 dias para processar em memória
    cursor.execute('SELECT entrada, saida FROM registro_vagas WHERE entrada >= ?', (trinta_dias_atras,))
    sessoes = [{'entrada': r[0], 'saida': r[1]} for r in cursor.fetchall()]
    
    # A. Gráfico de Linha (Ocupação e Horários de Pico)
    # Contamos o acúmulo de veículos para cada hora do dia (0 a 23)
    horas_contagem = [0] * 24
    for s in sessoes:
        ent_ts = s['entrada']
        sai_ts = s['saida'] or agora_ts
        
        # Converte para local
        dt_ent = datetime.datetime.fromtimestamp(ent_ts)
        dt_sai = datetime.datetime.fromtimestamp(sai_ts)
        
        h_ent = dt_ent.hour
        h_sai = dt_sai.hour
        
        if dt_ent.date() == dt_sai.date():
            for h in range(h_ent, h_sai + 1):
                if h < 24:
                    horas_contagem[h] += 1
        else:
            # Caso passe de um dia para outro
            for h in range(24):
                horas_contagem[h] += 1

    # Labels de 2 em 2 horas
    labels_linha = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    ocupadas_qtd = [horas_contagem[0], horas_contagem[2], horas_contagem[4], horas_contagem[6], horas_contagem[8], horas_contagem[10], horas_contagem[12], horas_contagem[14], horas_contagem[16], horas_contagem[18], horas_contagem[20], horas_contagem[22]]
    
    # Média diária de carros estacionados naquele horário
    n_dias = max(1.0, janela_tempo / 86400.0)
    ocupadas_medias = [round(qtd / n_dias, 1) for qtd in ocupadas_qtd]
    
    # Ocupação em %
    ocupacao_pct = [round((c / max(1, total_vagas)) * 100, 1) for c in ocupadas_medias]
    
    grafico_linha = {
        'labels': labels_linha,
        'ocupacao_pct': ocupacao_pct,
        'ocupadas_qtd': ocupadas_medias
    }
    
    # Média de 24 horas para o dashboard (uma média por hora de 0 a 23)
    ocupadas_medias_24h = [round(qtd / n_dias, 1) for qtd in horas_contagem]
    
    # B. Gráfico de Barras por Dia da Semana (Média Permanência Curta vs Longa)
    somas_curta = [0.0] * 7
    somas_longa = [0.0] * 7
    counts_curta = [0] * 7
    counts_longa = [0] * 7
    
    for s in sessoes:
        if s['saida'] is not None:
            dt_sai = datetime.datetime.fromtimestamp(s['saida'])
            # Mapeia weekday do python (Seg=0...Dom=6) para nosso índice (Dom=0, Seg=1...Sáb=6)
            python_w = dt_sai.weekday()
            idx_w = (python_w + 1) if python_w < 6 else 0
            
            duracao_min = (s['saida'] - s['entrada']) / 60.0
            
            if duracao_min < 60.0:
                somas_curta[idx_w] += duracao_min
                counts_curta[idx_w] += 1
            else:
                somas_longa[idx_w] += duracao_min
                counts_longa[idx_w] += 1
                
    medias_curta = [round(somas_curta[i] / counts_curta[i], 1) if counts_curta[i] > 0 else 0.0 for i in range(7)]
    medias_longa = [round(somas_longa[i] / counts_longa[i], 1) if counts_longa[i] > 0 else 0.0 for i in range(7)]
    
    grafico_barras_dia = {
        'labels': ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"],
        'curta': medias_curta,
        'longa': medias_longa
    }
    
    # C. Gráfico de Tráfego (Entrada vs Saída nos últimos 7 dias)
    labels_trafego = []
    entradas_trafego = []
    saidas_trafego = []
    
    dias_semana_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    
    for i in range(6, -1, -1):
        dt_dia = agora - datetime.timedelta(days=i)
        dia_inicio_ts = int(dt_dia.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        dia_fim_ts = dia_inicio_ts + 86400
        
        # Nome do dia da semana
        w_name = dias_semana_pt[dt_dia.weekday()]
        labels_trafego.append(f"{w_name} {dt_dia.strftime('%d/%m')}")
        
        # Entradas nesse dia
        cursor.execute('SELECT COUNT(*) FROM registro_vagas WHERE entrada >= ? AND entrada < ?', (dia_inicio_ts, dia_fim_ts))
        ent_qtd = cursor.fetchone()[0] or 0
        entradas_trafego.append(ent_qtd)
        
        # Saídas nesse dia
        cursor.execute('SELECT COUNT(*) FROM registro_vagas WHERE saida >= ? AND saida < ? AND saida IS NOT NULL', (dia_inicio_ts, dia_fim_ts))
        sai_qtd = cursor.fetchone()[0] or 0
        saidas_trafego.append(sai_qtd)
        
    grafico_trafego = {
        'labels': labels_trafego,
        'entradas': entradas_trafego,
        'saidas': saidas_trafego
    }
    
    # D. Gráfico de Distribuição por Tipo (Doughnut)
    curta_total = 0
    longa_total = 0
    for s in sessoes:
        if s['saida'] is not None:
            duracao_min = (s['saida'] - s['entrada']) / 60.0
            if duracao_min < 60.0:
                curta_total += 1
            else:
                longa_total += 1
                
    grafico_tipo = {
        'curta_qtd': curta_total,
        'longa_qtd': longa_total,
        'total': curta_total + longa_total
    }
    
    conn.close()
    
    return {
        'resumo': {
            'media_permanencia': perm_str,
            'taxa_ocupacao': taxa_ocupacao_str,
            'dia_maior_movimento': dia_str,
            'dia_maior_movimento_data': dia_data
        },
        'grafico_linha': grafico_linha,
        'grafico_linha_24h': ocupadas_medias_24h,
        'grafico_barras_dia': grafico_barras_dia,
        'grafico_trafego': grafico_trafego,
        'grafico_tipo': grafico_tipo
    }


