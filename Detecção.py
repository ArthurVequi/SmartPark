import cv2
import time
import threading
import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import banco

# Configura o servidor Flask
app = Flask(__name__)
CORS(app)

estado_vagas = []
lock = threading.Lock()

# Rota raiz da API
@app.route('/')
def home():
    return "API SmartPark rodando 🚀"

# Retorna a situacao de todas as vagas
@app.route('/api/vagas', methods=['GET'])
def get_vagas():
    with lock:
        return jsonify(estado_vagas)

# Retorna contagem de livres e ocupadas
@app.route('/api/resumo', methods=['GET'])
def get_resumo():
    with lock:
        total = len(estado_vagas)
        ocupadas = sum(1 for v in estado_vagas if v['situacao'] == 'ocupada')
        livres = total - ocupadas
        return jsonify({'total': total, 'livres': livres, 'ocupadas': ocupadas})

# Retorna logs de auditoria de entrada e saida
@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(banco.obter_logs())

# Retorna resumo financeiro e tarifas acumuladas dos veiculos ativos
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
        
        # Converte a duracao para texto formatado
        if minutos < 60:
            duracao_str = f"{minutos}min"
        else:
            horas = minutos // 60
            mins = minutos % 60
            duracao_str = f"{horas}h {mins}m"
            
        # Cobranca de R$ 10.00 por hora linear, com minimo de R$ 2.00
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

# Retorna os datasets completos para os graficos e cards de estatisticas da interface
@app.route('/api/relatorios-resumo', methods=['GET'])
def get_relatorios_resumo():
    return jsonify(banco.obter_resumo_relatorios())

# Inicia o servidor local Flask
def iniciar_api():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Inicializa o banco de dados e carrega as vagas salvas
banco.init_db()
vagas = banco.carregar_vagas()
pontos = []

# Escolha do modo de operacao pelo terminal
modo = input("Digite 'M' para mapear ou pressione [Enter] para detectar: ").strip().upper()

cap = cv2.VideoCapture(0)

# Fluxo de Mapeamento Manual
if modo == 'M':
    print("Modo de mapeamento iniciado. Clique 2x para criar vagas, aperte 'Z' para desfazer, e 'ESC' para sair.")
    
    # Callback do clique do mouse para registrar coordenadas
    def mouse_click(event, x, y, flags, param):
        global pontos, vagas
        if event == cv2.EVENT_LBUTTONDOWN:
            pontos.append((x, y))
            if len(pontos) == 2:
                x1, y1 = pontos[0]
                x2, y2 = pontos[1]
                vaga_id = banco.salvar_vaga(x1, y1, x2, y2)
                vagas.append((vaga_id, x1, y1, x2, y2))
                print(f"Vaga salva: ID {vaga_id} -> {(x1, y1, x2, y2)}")
                pontos = []

    cv2.namedWindow("Mapeamento de Vagas")
    cv2.setMouseCallback("Mapeamento de Vagas", mouse_click)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Desenha marcadores de clique
        for p in pontos:
            cv2.circle(frame, p, 5, (255, 0, 0), -1)
            
        # Desenha retangulos das vagas salvas
        for vaga in vagas:
            vid, vx1, vy1, vx2, vy2 = vaga
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (0, 255, 0), 2)
            cv2.putText(frame, f"Vaga {vid}", (vx1, vy1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
        cv2.imshow("Mapeamento de Vagas", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC sai do loop
            break
        elif key == ord('z'):  # Z remove a ultima vaga
            if vagas:
                removida = vagas.pop()
                banco.remover_vaga(removida[0])
                print(f"Vaga ID {removida[0]} removida.")

    cap.release()
    cv2.destroyAllWindows()
    print("\nMapeamento finalizado.")

# Fluxo de Detecao de Veiculos
else:
    print("Carregando modelo de Inteligencia Artificial YOLOv8...")
    model = YOLO("yolov8m.pt")
    ultimo_frame = 0

    # Inicializa o estado das vagas na memoria
    with lock:
        estado_vagas = [{'id': vaga[0], 'situacao': 'livre'} for vaga in vagas]

    # Inicia a API Flask em uma thread paralela
    thread_api = threading.Thread(target=iniciar_api, daemon=True)
    thread_api.start()
    print("✅ API rodando em http://localhost:5000")
    print("Pressione 'ESC' na janela do OpenCV para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Limita processamento a cada 0.1s para otimizacao de CPU/GPU
        agora = time.time()
        if agora - ultimo_frame >= 0.1:
            ultimo_frame = agora

            # Inferência da rede YOLOv8
            results = model(frame)
            carros = []

            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    name = model.names[cls]
                    # Filtra somente objetos da classe carro
                    if name == "car":
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        carros.append((x1, y1, x2, y2))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

            ocupadas = 0
            novo_estado = []

            # Verifica sobreposicao fisica entre carros e vagas
            for vaga in vagas:
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
                # Compara mudancas de estado para gravar logs de entrada/saida
                dict_antigo = {v['id']: v['situacao'] for v in estado_vagas}
                
                for v in novo_estado:
                    vid = v['id']
                    situacao_nova = v['situacao']
                    situacao_antiga = dict_antigo.get(vid, 'livre')
                    
                    # Entrada detectada
                    if situacao_antiga == 'livre' and situacao_nova == 'ocupada':
                        print(f"🚗 Entrada na Vaga {vid}")
                        banco.registrar_entrada(vid, int(time.time()))
                    # Saida detectada
                    elif situacao_antiga == 'ocupada' and situacao_nova == 'livre':
                        print(f"🚙 Saída da Vaga {vid}")
                        entrada_ts = banco.obter_entrada_ativa(vid)
                        saida_ts = int(time.time())
                        valor_pago = 0.0
                        
                        if entrada_ts is not None:
                            duracao = saida_ts - entrada_ts
                            # R$ 10.00/hora, minimo R$ 2.00
                            valor_pago = round(max(2.00, (duracao / 3600.0) * 10.0), 2)
                        else:
                            # Entrada retroativa simulada caso nao haja registro previo
                            entrada_ts = saida_ts - 300
                            banco.registrar_entrada(vid, entrada_ts)
                            valor_pago = 2.00
                            
                        banco.registrar_saida(vid, saida_ts, valor_pago)
                
                estado_vagas = novo_estado

            livres = len(vagas) - ocupadas

            # Renderiza dados estatisticos na tela da camera
            cv2.putText(frame, f"Ocupadas: {ocupadas}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(frame, f"Livres: {livres}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, "API: localhost:5000", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow("Estacionamento Inteligente - Deteccao", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC para fechar
            break

    cap.release()
    cv2.destroyAllWindows()