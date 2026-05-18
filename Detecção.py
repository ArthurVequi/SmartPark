from ultralytics import YOLO
import cv2
import time
import threading
import sqlite3
import datetime
from flask import Flask, jsonify
from flask_cors import CORS
import banco

# =============================================================
# API FLASK
# =============================================================
app = Flask(__name__)
CORS(app)

estado_vagas = []
lock = threading.Lock()

# Rotas da API

@app.route('/')
def home():
    return "API SmartPark rodando 🚀"

@app.route('/api/vagas', methods=['GET'])
def get_vagas():
    with lock:
        return jsonify(estado_vagas)

@app.route('/api/resumo', methods=['GET'])
def get_resumo():
    with lock:
        total    = len(estado_vagas)
        ocupadas = sum(1 for v in estado_vagas if v['situacao'] == 'ocupada')
        livres   = total - ocupadas
        return jsonify({ 'total': total, 'livres': livres, 'ocupadas': ocupadas })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(banco.obter_logs())

@app.route('/api/financeiro', methods=['GET'])
def get_financeiro():
    resumo = banco.obter_resumo_financeiro()
    sessoes_ativas = banco.obter_sessoes_ativas()
    
    ativos_respostas = []
    agora_ts = int(time.time())
    
    for sessao in sessoes_ativas:
        vid = sessao['vaga_id']
        entrada_ts = sessao['entrada']
        
        duracao = agora_ts - entrada_ts
        minutos = duracao // 60
        if minutos < 60:
            duracao_str = f"{minutos}min"
        else:
            horas = minutos // 60
            mins = minutos % 60
            duracao_str = f"{horas}h {mins}m"
            
        # Tarifa de R$ 10.00/hora, mínimo de R$ 2.00
        valor_atual = round(max(2.00, (duracao / 3600.0) * 10.0), 2)
        
        entrada_formatada = datetime.datetime.fromtimestamp(entrada_ts).strftime('%H:%M:%S')
        
        ativos_respostas.append({
            'vaga_id': f"{vid:02d}",
            'entrada': entrada_formatada,
            'duracao': duracao_str,
            'valor_a_pagar': valor_atual
        })
        
    return jsonify({
        'resumo': resumo,
        'ativos': ativos_respostas
    })

def iniciar_api():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# =============================================================
# INICIALIZAÇÃO E ESCOLHA DE MODO
# =============================================================
banco.init_db()
vagas = banco.carregar_vagas()
pontos = []

modo = input("Digite 'M' para mapear ou pressione [Enter] para detectar: ").strip().upper()

cap = cv2.VideoCapture(0)

if modo == 'M':
    print("Modo de mapeamento iniciado. Clique 2x para criar vagas, aperte 'Z' para desfazer a ultima, e 'ESC' para sair.")
    
    def mouse_click(event, x, y, flags, param):
        global pontos, vagas
        if event == cv2.EVENT_LBUTTONDOWN:
            pontos.append((x, y))
            if len(pontos) == 2:
                x1, y1 = pontos[0]
                x2, y2 = pontos[1]
                vaga_id = banco.salvar_vaga(x1, y1, x2, y2)
                vagas.append((vaga_id, x1, y1, x2, y2))
                print(f"Vaga salva no banco: ID {vaga_id} -> {(x1, y1, x2, y2)}")
                pontos = []

    cv2.namedWindow("Mapeamento de Vagas")
    cv2.setMouseCallback("Mapeamento de Vagas", mouse_click)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        for p in pontos:
            cv2.circle(frame, p, 5, (255, 0, 0), -1)
            
        for vaga in vagas:
            vid, vx1, vy1, vx2, vy2 = vaga
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (0, 255, 0), 2)
            cv2.putText(frame, f"Vaga {vid}", (vx1, vy1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
        cv2.imshow("Mapeamento de Vagas", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27: # ESC
            break
        elif key == ord('z'):
            if vagas:
                removida = vagas.pop()
                banco.remover_vaga(removida[0])
                print(f"Removida do banco: ID {removida[0]}")

    cap.release()
    cv2.destroyAllWindows()
    print("\nMapeamento finalizado. Vagas atuais no banco:")
    for vaga in vagas:
        print(f"    ID: {vaga[0]} -> Coord: ({vaga[1]}, {vaga[2]}, {vaga[3]}, {vaga[4]})")
    print("\nExecute o script novamente e aperte [Enter] para iniciar a detecção.")

else:
    print("Iniciando modo de detecção. Aguarde o carregamento do modelo...")
    model = YOLO("yolov8m.pt")
    ultimo_frame = 0

    with lock:
        estado_vagas = [{'id': vaga[0], 'situacao': 'livre'} for vaga in vagas]

    # Inicia API em thread separada
    thread_api = threading.Thread(target=iniciar_api, daemon=True)
    thread_api.start()
    print("✅ API rodando em http://localhost:5000")
    print("Pressione 'ESC' na janela do OpenCV para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        agora = time.time()
        if agora - ultimo_frame >= 0.1:
            ultimo_frame = agora

            results = model(frame)
            carros  = []

            for r in results:
                for box in r.boxes:
                    cls  = int(box.cls[0])
                    name = model.names[cls]
                    if name == "car":
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        carros.append((x1, y1, x2, y2))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

            ocupadas = 0
            novo_estado = []

            for idx, vaga in enumerate(vagas):
                vid, vx1, vy1, vx2, vy2 = vaga
                ocupada = False

                for carro in carros:
                    cx1, cy1, cx2, cy2 = carro
                    if cx1 < vx2 and cx2 > vx1 and cy1 < vy2 and cy2 > vy1:
                        ocupada = True
                        break

                situacao = 'ocupada' if ocupada else 'livre'
                novo_estado.append({'id': vid, 'situacao': situacao})

                cor = (0, 0, 255) if ocupada else (0, 255, 0)
                if ocupada:
                    ocupadas += 1

                cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), cor, 2)
                cv2.putText(frame, str(vid), (vx1, vy1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1)

            with lock:
                # Compara mudanças de estado para gravar logs de entrada/saída no banco
                dict_antigo = {v['id']: v['situacao'] for v in estado_vagas}
                
                for v in novo_estado:
                    vid = v['id']
                    situacao_nova = v['situacao']
                    situacao_antiga = dict_antigo.get(vid, 'livre')
                    
                    if situacao_antiga == 'livre' and situacao_nova == 'ocupada':
                        print(f"🚗 DETECTADO: Entrada na Vaga {vid}")
                        banco.registrar_entrada(vid, int(time.time()))
                    elif situacao_antiga == 'ocupada' and situacao_nova == 'livre':
                        print(f"🚙 DETECTADO: Saída da Vaga {vid}")
                        
                        # Consulta o banco para saber o horário de entrada ativo
                        conn = sqlite3.connect('estacionamento.db', timeout=10.0)
                        cursor = conn.cursor()
                        cursor.execute('SELECT entrada FROM registro_vagas WHERE vaga_id = ? AND saida IS NULL ORDER BY entrada DESC LIMIT 1', (vid,))
                        row = cursor.fetchone()
                        conn.close()
                        
                        saida_ts = int(time.time())
                        valor_pago = 0.0
                        if row:
                            entrada_ts = row[0]
                            duracao = saida_ts - entrada_ts
                            # R$ 10.00 por hora, mínimo de R$ 2.00
                            valor_pago = round(max(2.00, (duracao / 3600.0) * 10.0), 2)
                        else:
                            # Caso não tenha registro de entrada, cria uma retroativa fictícia (5 min atrás)
                            entrada_ts = saida_ts - 300
                            banco.registrar_entrada(vid, entrada_ts)
                            duracao = 300
                            valor_pago = 2.00
                            
                        banco.registrar_saida(vid, saida_ts, valor_pago)
                
                estado_vagas = novo_estado

            livres = len(vagas) - ocupadas

            cv2.putText(frame, f"Ocupadas: {ocupadas}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(frame, f"Livres: {livres}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, "API: localhost:5000", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow("Estacionamento Inteligente - Deteccao", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()