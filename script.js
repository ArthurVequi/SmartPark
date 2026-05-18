/*Script frontend integrado com API Flask*/

const API_URL = 'http://localhost:5000';
const TOTAL_VAGAS = 20;

let listaVagas = [];
let dadosOcupacaoPorHora = gerarDadosHorarios();
let modoOffline = false;

function gerarDadosHorarios() {
  return Array.from({ length: 24 }, (_, hora) => {
    const ocupadas = Math.round(3 + Math.sin((hora - 8) * 0.4) * 6 + Math.random() * 3);
    return Math.max(0, Math.min(TOTAL_VAGAS, ocupadas));
  });
}

async function buscarVagasAPI() {
  try {
    const resposta = await fetch(`${API_URL}/api/vagas`, { signal: AbortSignal.timeout(3000) });
    if (!resposta.ok) throw new Error('Resposta inválida');
    const dados = await resposta.json();
    listaVagas = dados.map(v => ({
      id: v.id,
      situacao: v.situacao,
      horarioEntrada: v.horarioEntrada
        ? new Date(v.horarioEntrada).getTime()
        : Date.now() - Math.floor(Math.random() * 1800000)
    }));
    if (modoOffline) { modoOffline = false; atualizarStatusConexao(true); }
    renderizarGrade();
    atualizarGraficoHoraAtual();
  } catch (erro) {
    console.warn('API indisponível:', erro.message);
    if (!modoOffline) { modoOffline = true; atualizarStatusConexao(false); }
    if (listaVagas.length === 0) {
      listaVagas = Array.from({ length: TOTAL_VAGAS }, (_, i) => ({
        id: i + 1,
        situacao: Math.random() > 0.45 ? 'livre' : 'ocupada',
        horarioEntrada: Date.now() - Math.floor(Math.random() * 3600000)
      }));
    }
    renderizarGrade();
  }
}

function atualizarStatusConexao(online) {
  const dot = document.querySelector('.sidebar-footer .status-dot');
  if (dot) dot.style.background = online ? 'var(--green)' : 'var(--amber)';
}

function atualizarGraficoHoraAtual() {
  if (!graficoHoras) return;
  const totalOcupadas = listaVagas.filter(v => v.situacao === 'ocupada').length;
  const totalVagas = listaVagas.filter(v => v.situacao !== 'indisponivel').length || 20;
  const horaAtual = new Date().getHours();

  if (graficoHoras.data.datasets[1].data && graficoHoras.data.datasets[1].data.length > horaAtual) {
    graficoHoras.data.datasets[1].data[horaAtual] = totalOcupadas;
    graficoHoras.data.datasets[0].data[horaAtual] = Math.max(0, totalVagas - totalOcupadas);
    graficoHoras.update('none');
  }
}

document.querySelectorAll('.nav-item').forEach(itemMenu => {
  itemMenu.addEventListener('click', () => {
    const pagina = itemMenu.dataset.page;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    itemMenu.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + pagina).classList.add('active');
    document.getElementById('topbar-title').textContent = pagina.toUpperCase();
    if (pagina === 'relatorios') inicializarGraficosRelatorio();
  });
});

document.querySelectorAll('.rtab').forEach(aba => {
  aba.addEventListener('click', () => {
    document.querySelectorAll('.rtab').forEach(x => x.classList.remove('active'));
    aba.classList.add('active');
  });
});

document.getElementById('btn-gerar').addEventListener('click', () => {
  const btn = document.getElementById('btn-gerar');
  btn.textContent = '⏳ Gerando...';
  setTimeout(() => {
    const agora = new Date();
    document.getElementById('r-gen-ts').textContent = 'Gerado em: ' + agora.toLocaleDateString('pt-BR') + ' · ' + agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    btn.textContent = '✓ Gerado';
    setTimeout(() => { btn.textContent = '⬇ Gerar Relatório'; }, 2000);
  }, 1200);
});

function renderizarGrade() {
  const grade = document.getElementById('parking-grid');
  const lista = document.getElementById('status-list');
  grade.innerHTML = '';
  lista.innerHTML = '';

  listaVagas.forEach(vaga => {
    const el = document.createElement('div');
    const cls = vaga.situacao === 'indisponivel' ? 'unavailable' : vaga.situacao === 'livre' ? 'free' : 'occupied';
    el.className = 'spot ' + cls;
    const num = String(vaga.id).padStart(2, '0');
    if (vaga.situacao === 'ocupada') el.innerHTML = `<div class="spot-car">🚗</div><div>${num}</div>`;
    else if (vaga.situacao === 'livre') el.innerHTML = `<div>${num}</div>`;
    else el.innerHTML = `<div style="font-size:8px;">N/D</div>`;
    el.addEventListener('mouseenter', e => exibirTooltip(e, vaga));
    el.addEventListener('mouseleave', ocultarTooltip);
    grade.appendChild(el);

    if (vaga.situacao !== 'indisponivel') {
      const item = document.createElement('div');
      item.className = 'status-item';
      const tempo = vaga.situacao === 'ocupada' ? formatarDuracao(Date.now() - vaga.horarioEntrada) : '';
      item.innerHTML = `
        <div class="spot-id">VAGA ${num}</div>
        <div style="display:flex;align-items:center;gap:8px;">
          ${vaga.situacao === 'ocupada' ? `<span style="font-size:10px;color:var(--muted);">${tempo}</span>` : ''}
          <span class="spot-badge ${vaga.situacao === 'livre' ? 'free' : 'occ'}">${vaga.situacao === 'livre' ? 'LIVRE' : 'OCUPADA'}</span>
        </div>`;
      lista.appendChild(item);
    }
  });
  atualizarEstatisticas();
}

function formatarDuracao(ms) {
  const min = Math.floor(ms / 60000);
  if (min < 60) return min + 'min';
  return Math.floor(min / 60) + 'h ' + (min % 60) + 'm';
}

function atualizarEstatisticas() {
  const livres = listaVagas.filter(v => v.situacao === 'livre').length;
  const ocupadas = listaVagas.filter(v => v.situacao === 'ocupada').length;
  const disponiveis = listaVagas.filter(v => v.situacao !== 'indisponivel').length;

  document.getElementById('s-free').textContent = livres;
  document.getElementById('s-occ').textContent = ocupadas;
  document.getElementById('s-free-pct').textContent = disponiveis > 0 ? Math.round(livres / disponiveis * 100) + '% do total' : '--';
  document.getElementById('s-occ-pct').textContent = disponiveis > 0 ? Math.round(ocupadas / disponiveis * 100) + '% do total' : '--';

  const elTotal = document.getElementById('s-total');
  if (elTotal) elTotal.textContent = disponiveis;

  const vagasOcup = listaVagas.filter(v => v.situacao === 'ocupada');
  if (vagasOcup.length) {
    const media = vagasOcup.reduce((a, v) => a + (Date.now() - v.horarioEntrada), 0) / vagasOcup.length;
    document.getElementById('s-avg').textContent = Math.round(media / 60000) + 'm';
  }
  atualizarDonut(livres, ocupadas);
}

function atualizarRelogio() {
  const agora = new Date();
  const h = String(agora.getHours()).padStart(2, '0');
  const m = String(agora.getMinutes()).padStart(2, '0');
  const s = String(agora.getSeconds()).padStart(2, '0');
  document.getElementById('clock').textContent = h + ':' + m + ':' + s;
  document.getElementById('last-update').textContent = agora.toLocaleDateString('pt-BR') + ' ' + h + ':' + m;
  document.getElementById('map-updated').textContent = 'Atualizado: ' + h + ':' + m + ':' + s;
}

function exibirTooltip(evento, vaga) {
  const el = document.getElementById('tooltip');
  const rotulo = vaga.situacao === 'livre' ? 'Livre' : vaga.situacao === 'ocupada' ? 'Ocupada' : 'Indisponível';
  const tempo = vaga.situacao === 'ocupada' ? '<br>Há: ' + formatarDuracao(Date.now() - vaga.horarioEntrada) : '';
  el.innerHTML = `<strong>Vaga ${String(vaga.id).padStart(2, '0')}</strong><br>${rotulo}${tempo}`;
  el.style.display = 'block';
  el.style.left = (evento.clientX + 12) + 'px';
  el.style.top = (evento.clientY - 30) + 'px';
}

function ocultarTooltip() { document.getElementById('tooltip').style.display = 'none'; }

let graficoHoras, graficoDonut;

function inicializarGraficosDashboard() {
  const rotulos = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0') + ':00');
  const totalVagas = listaVagas.filter(v => v.situacao !== 'indisponivel').length || 20;

  graficoHoras = new Chart(document.getElementById('chart-hour'), {
    type: 'line',
    data: {
      labels: rotulos,
      datasets: [
        { label: 'Livres', data: Array(24).fill(0), borderColor: '#1D9E75', backgroundColor: 'rgba(29,158,117,.12)', fill: true, tension: .4, pointRadius: 2, borderWidth: 2 },
        { label: 'Ocupadas', data: Array(24).fill(0), borderColor: '#E24B4A', backgroundColor: 'rgba(226,75,74,.10)', fill: true, tension: .4, pointRadius: 2, borderWidth: 2, borderDash: [4, 3] }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { ticks: { color: '#8a8a85', font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }, grid: { color: '#2a2f3a' } },
        y: { min: 0, max: totalVagas, ticks: { color: '#8a8a85', font: { size: 10 }, stepSize: 5 }, grid: { color: '#2a2f3a' } }
      }
    }
  });

  const livres = listaVagas.filter(v => v.situacao === 'livre').length;
  const ocupadas = listaVagas.filter(v => v.situacao === 'ocupada').length;
  graficoDonut = new Chart(document.getElementById('chart-donut'), {
    type: 'doughnut',
    data: { labels: ['Livres', 'Ocupadas'], datasets: [{ data: [livres, ocupadas], backgroundColor: ['#1D9E75', '#E24B4A'], borderColor: ['#04342c', '#2a1515'], borderWidth: 3, hoverOffset: 4 }] },
    options: { responsive: false, cutout: '70%', plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => c.label + ': ' + c.raw } } } }
  });
  atualizarLegendaDonut(livres, ocupadas);
}

function atualizarDonut(livres, ocupadas) {
  if (!graficoDonut) return;
  graficoDonut.data.datasets[0].data = [livres, ocupadas];
  graficoDonut.update();
  const pct = (livres + ocupadas) > 0 ? Math.round(livres / (livres + ocupadas) * 100) : 0;
  document.getElementById('donut-pct').textContent = pct + '%';
  atualizarLegendaDonut(livres, ocupadas);
}

function atualizarLegendaDonut(livres, ocupadas) {
  document.getElementById('donut-legend').innerHTML = `
    <span style="display:flex;align-items:center;gap:4px;color:var(--muted)"><span style="width:10px;height:10px;border-radius:2px;background:#1D9E75;display:inline-block;"></span>Livres (${livres})</span>
    <span style="display:flex;align-items:center;gap:4px;color:var(--muted)"><span style="width:10px;height:10px;border-radius:2px;background:#E24B4A;display:inline-block;"></span>Ocupadas (${ocupadas})</span>`;
}

let rChartLine, rChartBar, rChartTraffic, rChartTipo;
let graficosRelatorioIniciados = false;

function inicializarGraficosRelatorio() {
  if (graficosRelatorioIniciados) return;
  graficosRelatorioIniciados = true;

  const horasR = ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'];
  rChartLine = new Chart(document.getElementById('r-chart-line'), {
    type: 'line',
    data: {
      labels: horasR, datasets: [
        { label: 'Ocupação %', data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], borderColor: '#1D9E75', backgroundColor: 'rgba(29,158,117,.15)', fill: true, tension: .4, pointRadius: 2, borderWidth: 2 },
        { label: 'Ocupadas (Média)', data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], borderColor: '#E24B4A', backgroundColor: 'rgba(226,75,74,.10)', fill: true, tension: .4, pointRadius: 2, borderWidth: 2 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#8a8a85', font: { size: 10 } }, grid: { color: '#2a2f3a' } }, y: { min: 0, max: 100, ticks: { color: '#8a8a85', font: { size: 10 } }, grid: { color: '#2a2f3a' } } } }
  });

  const dias = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
  rChartBar = new Chart(document.getElementById('r-chart-bar'), {
    type: 'bar',
    data: {
      labels: dias, datasets: [
        { label: 'Curta (méd. min)', data: [0, 0, 0, 0, 0, 0, 0], backgroundColor: '#1D9E75', borderRadius: 3, borderSkipped: false },
        { label: 'Longa (méd. min)', data: [0, 0, 0, 0, 0, 0, 0], backgroundColor: '#E24B4A', borderRadius: 3, borderSkipped: false }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { stacked: true, ticks: { color: '#8a8a85', font: { size: 10 } }, grid: { color: '#2a2f3a' } }, y: { stacked: true, ticks: { color: '#8a8a85', font: { size: 10 } }, grid: { color: '#2a2f3a' } } } }
  });

  rChartTraffic = new Chart(document.getElementById('r-chart-traffic'), {
    type: 'bar',
    data: {
      labels: dias, datasets: [
        { label: 'Entradas', data: [0, 0, 0, 0, 0, 0, 0], backgroundColor: '#1D9E75', borderRadius: 3, borderSkipped: false },
        { label: 'Saídas', data: [0, 0, 0, 0, 0, 0, 0], backgroundColor: '#E24B4A', borderRadius: 3, borderSkipped: false }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { stacked: true, ticks: { color: '#8a8a85', font: { size: 9 } }, grid: { color: '#2a2f3a' } }, y: { stacked: true, ticks: { color: '#8a8a85', font: { size: 9 } }, grid: { color: '#2a2f3a' } } } }
  });

  rChartTipo = new Chart(document.getElementById('r-chart-tipo'), {
    type: 'doughnut',
    data: { labels: ['Curta', 'Longa'], datasets: [{ data: [0, 0], backgroundColor: ['#1D9E75', '#E24B4A'], borderColor: ['#04342c', '#2a1515'], borderWidth: 3, hoverOffset: 4 }] },
    options: { responsive: false, cutout: '68%', plugins: { legend: { display: false } } }
  });

  const agora = new Date();
  document.getElementById('r-gen-ts').textContent = 'Gerado em: ' + agora.toLocaleDateString('pt-BR') + ' · ' + agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

async function buscarLogsAPI() {
  try {
    const resposta = await fetch(`${API_URL}/api/logs`, { signal: AbortSignal.timeout(3000) });
    if (!resposta.ok) throw new Error('Resposta inválida');
    const dados = await resposta.json();
    const tbody = document.getElementById('logs-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (dados.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="4" style="text-align:center; color:var(--muted); padding: 15px;">Nenhum evento registrado ainda.</td>`;
      tbody.appendChild(tr);
    } else {
      dados.forEach(r => {
        const tr = document.createElement('tr');
        const badgeClass = r.acao === 'Entrada' ? 'badge-entrada' : 'badge-saida';
        tr.innerHTML = `
          <td class="mono" style="color:var(--muted)">${r.data_hora}</td>
          <td class="mono">VAGA ${r.vaga_id}</td>
          <td><span class="${badgeClass}">${r.acao.toUpperCase()}</span></td>
          <td class="mono" style="color:var(--muted)">${r.duracao}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (erro) {
    console.warn('Erro ao carregar logs:', erro.message);
  }
}

async function buscarFinanceiroAPI() {
  try {
    const resposta = await fetch(`${API_URL}/api/financeiro`, { signal: AbortSignal.timeout(3000) });
    if (!resposta.ok) throw new Error('Resposta inválida');
    const dados = await resposta.json();

    // Atualiza faturamentos nas tags HTML do menu financeiro
    document.getElementById('fin-diario').textContent = formatarMoeda(dados.resumo.diario);
    document.getElementById('fin-semanal').textContent = formatarMoeda(dados.resumo.semanal);
    document.getElementById('fin-mensal').textContent = formatarMoeda(dados.resumo.mensal);

    // Atualiza tabela de veículos ativos
    const tbody = document.getElementById('financeiro-tbody');
    if (tbody) {
      tbody.innerHTML = '';
      let totalPotencial = 0;

      if (dados.ativos.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="5" style="text-align:center; color:var(--muted); padding: 20px;">Nenhum veículo estacionado no momento.</td>`;
        tbody.appendChild(tr);
      } else {
        dados.ativos.forEach(a => {
          totalPotencial += a.valor_a_pagar;
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td class="mono">VAGA ${a.vaga_id}</td>
            <td class="mono" style="color:var(--muted)">${a.entrada}</td>
            <td class="mono" style="color:var(--muted)">${a.duracao}</td>
            <td class="mono" style="color:var(--green); font-weight:700;">${formatarMoeda(a.valor_a_pagar)}</td>
            <td><span class="spot-badge occ">PARKED</span></td>
          `;
          tbody.appendChild(tr);
        });
      }

      // Atualiza o total potencial na barra lateral
      document.getElementById('fin-potencial').textContent = formatarMoeda(totalPotencial);
    }
  } catch (erro) {
    console.warn('Erro ao carregar dados financeiros:', erro.message);
  }
}

function formatarMoeda(valor) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
}

async function buscarRelatoriosResumoAPI() {
  try {
    const resposta = await fetch(`${API_URL}/api/relatorios-resumo`, { signal: AbortSignal.timeout(3000) });
    if (!resposta.ok) throw new Error('Resposta inválida');
    const dados = await resposta.json();

    const elOcupacao = document.getElementById('rep-media-ocupacao');
    const elPermanencia = document.getElementById('rep-media-permanencia');
    const elMovimento = document.getElementById('rep-maior-movimento');
    const elMovimentoData = document.getElementById('r-gen-date');

    if (elOcupacao) elOcupacao.textContent = dados.resumo.taxa_ocupacao;
    if (elPermanencia) elPermanencia.textContent = dados.resumo.media_permanencia;
    if (elMovimento) elMovimento.textContent = dados.resumo.dia_maior_movimento;
    if (elMovimentoData) elMovimentoData.textContent = dados.resumo.dia_maior_movimento_data;

    // Inicializa os gráficos antes de atualizar (se ainda não foram)
    inicializarGraficosRelatorio();

    // 1. Atualiza Gráfico de Linha (Ocupação e Horários de Pico)
    if (rChartLine) {
      rChartLine.data.labels = dados.grafico_linha.labels;
      rChartLine.data.datasets[0].data = dados.grafico_linha.ocupacao_pct;
      rChartLine.data.datasets[1].data = dados.grafico_linha.ocupadas_qtd;
      rChartLine.update();
    }

    // 2. Atualiza Gráfico de Barras por Dia (Média Permanência)
    if (rChartBar) {
      rChartBar.data.labels = dados.grafico_barras_dia.labels;
      rChartBar.data.datasets[0].data = dados.grafico_barras_dia.curta;
      rChartBar.data.datasets[1].data = dados.grafico_barras_dia.longa;

      const maxVal = Math.max(...dados.grafico_barras_dia.curta.concat(dados.grafico_barras_dia.longa));
      if (rChartBar.options.scales.y) {
        rChartBar.options.scales.y.max = maxVal > 0 ? Math.ceil(maxVal * 1.2) : 40;
      }
      rChartBar.update();
    }

    // 3. Atualiza Gráfico de Tráfego (Entrada vs Saída)
    if (rChartTraffic) {
      rChartTraffic.data.labels = dados.grafico_trafego.labels;
      rChartTraffic.data.datasets[0].data = dados.grafico_trafego.entradas;
      rChartTraffic.data.datasets[1].data = dados.grafico_trafego.saidas;

      const maxTrafego = Math.max(...dados.grafico_trafego.entradas.concat(dados.grafico_trafego.saidas));
      if (rChartTraffic.options.scales.y) {
        rChartTraffic.options.scales.y.max = maxTrafego > 0 ? Math.ceil(maxTrafego * 1.2) : 10;
      }
      rChartTraffic.update();
    }

    // 4. Atualiza Gráfico Doughnut (Distribuição por Tipo)
    if (rChartTipo) {
      rChartTipo.data.datasets[0].data = [dados.grafico_tipo.curta_qtd, dados.grafico_tipo.longa_qtd];

      const elCurtaLabel = document.querySelector('.dl-item:nth-child(1) span');
      const elLongaLabel = document.querySelector('.dl-item:nth-child(2) span');
      if (elCurtaLabel) elCurtaLabel.textContent = `Curta Duração (${dados.grafico_tipo.curta_qtd})`;
      if (elLongaLabel) elLongaLabel.textContent = `Longa Duração (${dados.grafico_tipo.longa_qtd})`;

      const elTipoTotal = document.getElementById('r-tipo-total');
      if (elTipoTotal) elTipoTotal.textContent = dados.grafico_tipo.total;

      rChartTipo.update();
    }

    // 5. Atualiza Gráfico Horas do Dashboard (Ocupação por Hora Real)
    if (graficoHoras && dados.grafico_linha_24h) {
      const totalVagas = listaVagas.filter(v => v.situacao !== 'indisponivel').length || 20;
      if (graficoHoras.options.scales.y) {
        graficoHoras.options.scales.y.max = totalVagas;
      }
      graficoHoras.data.datasets[1].data = dados.grafico_linha_24h;
      graficoHoras.data.datasets[0].data = dados.grafico_linha_24h.map(ocp => Math.max(0, totalVagas - ocp));
      graficoHoras.update();

      // Garante que o ponto da hora atual reflete o estado atual exato do estacionamento
      atualizarGraficoHoraAtual();
    }
  } catch (erro) {
    console.warn('Erro ao carregar resumo de relatórios:', erro.message);
  }
}

/* INICIALIZAÇÃO */
atualizarRelogio();
setInterval(atualizarRelogio, 1000);

window.addEventListener('load', async () => {
  await buscarVagasAPI();
  await buscarLogsAPI();
  await buscarFinanceiroAPI();
  await buscarRelatoriosResumoAPI();
  inicializarGraficosDashboard();
  setInterval(async () => {
    await buscarVagasAPI();
    await buscarLogsAPI();
    await buscarFinanceiroAPI();
    await buscarRelatoriosResumoAPI();
  }, 2000);
});
