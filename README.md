# 🚗 SmartPark — Gestão Inteligente de Estacionamento por Visão Computacional

Este projeto consiste em um **sistema de monitoramento e gestão inteligente de vagas de estacionamento**, projetado para maquetes físicas ou ambientes reais. Ele combina técnicas avançadas de **Visão Computacional (YOLOv8 & OpenCV)** na camada de detecção com uma **API Flask** e um **painel web administrativo em tempo real** enriquecido com métricas de faturamento e relatórios analíticos completos.

---

## 📂 Organização do Projeto e Pasta

A estrutura de arquivos foi organizada seguindo as melhores práticas de modularidade e separação de conceitos:

```
SmartPark/
├── frontend/             # 💻 Todo o ecossistema do front-end
│   ├── index.html        # Painel Web administrativo (Dashboard, Financeiro, Relatórios)
│   ├── script.js         # Lógica de consumo de API Flask, renderização dinâmica e Chart.js
│   └── style.css         # Identidade visual premium, variáveis HSL, Dark Theme e animações
│
├── Detecção.py           # 🧠 Thread de monitoramento OpenCV + YOLOv8 & Thread de API Flask
├── banco.py              # 🗄️ Camada de persistência, conexão SQLite e queries analíticas
├── .gitignore            # Bloqueia caches python, pesos da rede neural (.pt) e bancos locais (.db)
├── README.md             # Este manual de documentação
└── yolov8m.pt            # Pesos da rede YOLOv8 (ignorado no Git por ser binário pesado)
```

---

## 🧠 Arquitetura Técnica

O SmartPark é sustentado por duas camadas principais de processamento concorrente:

1. **Back-end de Visão & API (Python):**
   * **Módulo de Detecção (`Detecção.py`):** Executa o OpenCV para processar os frames da câmera. A cada `0.1s`, o modelo YOLOv8 detecta objetos da classe `"car"`. É calculada a intersecção de caixas físicas dos carros com os retângulos de vagas mapeadas. Transições de status (*livre <-> ocupada*) disparam gatilhos de banco.
   * **API RESTful (Flask):** Disponibiliza os dados de vagas, logs de auditoria, faturamento consolidado e dashboards analíticos através de endpoints na porta `5000`.
   * **Módulo Banco (`banco.py`):** Gerencia conexões SQLite e centraliza todas as queries de controle de vagas e inteligência de negócios.

2. **Front-end Analítico (HTML5 / Vanilla CSS / JavaScript):**
   * O painel web atualiza-se a cada `2 segundos` de forma assíncrona, apresentando o mapa visual das vagas, dados financeiros acumulados em tempo real e gráficos detalhados.

---

## 🪙 Regra de Negócio e Faturamento

O sistema simula um modelo de negócios de estacionamento comercial de alto padrão:
* **Tarifa Padrão:** **R$ 10,00 por hora** (cobrada linearmente por minuto decorrido).
* **Cobrança Mínima:** **R$ 2,00** (para permanências muito curtas, assegurando viabilidade).
* **Consolidação Financeira:** Agrupamento automático de faturamentos em períodos **Diários, Semanais e Mensais**, além de projeção de receita potencial em tempo real com base nos veículos atualmente estacionados.

---

## 🛠️ Instalação e Configuração

### 1. Requisitos Prévios
Certifique-se de possuir o Python 3.8+ instalado e as seguintes bibliotecas configuradas:

```bash
pip install ultralytics opencv-python flask flask-cors
```

### 2. Passo a Passo para Execução

#### **Passo A: Mapear as Vagas**
Antes de iniciar a detecção, você precisa desenhar os limites das vagas da sua maquete:
1. Execute o script no terminal:
   ```bash
   python Detecção.py
   ```
2. O terminal solicitará o modo. Digite `M` e pressione `[Enter]`.
3. Na janela do OpenCV:
   * **Clique duplo com o botão esquerdo:** Marca os cantos diagonalmente opostos da vaga (primeiro clique no canto superior esquerdo e segundo clique no canto inferior direito). A vaga será numerada e salva de imediato no SQLite.
   * **Tecla `Z`:** Remove a última vaga desenhada do banco.
   * **Tecla `ESC`:** Fecha o mapeador e salva a grade.

#### **Passo B: Iniciar o Monitoramento**
1. Com as vagas mapeadas, execute o script novamente:
   ```bash
   python Detecção.py
   ```
2. Apenas pressione `[Enter]` no terminal para escolher o modo padrão (Detecção).
3. O modelo YOLOv8m será carregado e a API REST subirá automaticamente na URL: `http://localhost:5000`.

#### **Passo C: Abrir a Interface Web**
1. Vá até a pasta `frontend/`.
2. Dê um duplo clique no arquivo `index.html` para abri-lo no seu navegador.
3. Navegue entre as abas:
   * **Dashboard:** Acompanhe a grade física em tempo real, as estatísticas de vagas livres/ocupadas e o gráfico de pico diário.
   * **Financeiro:** Visualize o caixa dinâmico diário/semanal/mensal e acompanhe a cobrança em tempo real de cada carro que estiver na vaga.
   * **Relatórios:** Veja médias de permanência, ocupação mensal histórica, tabelas completas de auditoria e gráficos detalhados de tráfego de entradas/saídas por dia.

---

## 🎯 Objetivo Pedagógico

Este sistema foi desenvolvido como critério de avaliação prática e obtenção de nota para a matéria de **Projeto Interdisciplinar 3 (P.I 3)**, comprovando o uso prático de automação, visão computacional e desenvolvimento de software integrado a banco de dados.
