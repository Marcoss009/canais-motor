// Estúdio dos Canais - interface. Lê /api/tudo a cada 3 s; ações em /api/acao.
'use strict';

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (n) => n == null ? '—' : Number(n).toLocaleString('pt-BR');

const ETAPA = {
  roteiro: { nome: 'Roteiro escrito', cls: '' },
  conferindo: { nome: 'Conferindo', cls: 'azul' },
  conferencia: { nome: 'Pronto pra render', cls: 'azul' },
  renderizando: { nome: 'Renderizando', cls: 'azul' },
  na_fila: { nome: 'Na fila de render', cls: 'azul' },
  erro: { nome: 'Erro', cls: 'erro' },
  pronto: { nome: 'Subindo pro YouTube', cls: '' },
  enviado: { nome: 'Esperando você', cls: 'alerta' },
  aprovado: { nome: 'Aprovado', cls: 'ok' },
  agendado: { nome: 'Agendado', cls: 'ok' },
  manual: { nome: 'Subir pelo Studio', cls: 'alerta' },
  publicado: { nome: 'No ar', cls: 'ok' },
  recusado: { nome: 'Refazer', cls: 'erro' },
};
const GRUPOS = [
  ['Em andamento', ['renderizando', 'conferindo', 'na_fila']],
  ['Esperando você', ['enviado', 'manual']],
  ['Com problema', ['erro', 'recusado']],
  ['Em preparação', ['roteiro', 'conferencia', 'pronto']],
  ['Aprovados e agendados', ['aprovado', 'agendado']],
  ['No ar', ['publicado']],
];
const PASSOS = [['voz', 'Voz'], ['trilha', 'Trilha'], ['imagens', 'Imagens'], ['cenas', 'Cenas'], ['render', 'Render']];
const NOME_CANAL = { engenhoso: 'Engenhoso', gta6: 'GTAzando' };

let D = null;            // último /api/tudo
let VIEW = 'geral';
let DET = null;          // {canal, id, aba, dados}
let FILTRO = { etapa: '', busca: '' };
let LOG_CANAL = '';

// ---------------- dados ----------------
async function carregar() {
  try {
    const r = await fetch('/api/tudo', { cache: 'no-store' });
    const antes = D;
    D = await r.json();
    if (antes) for (const p of antes.producao) {
      const agora = D.producao.find(x => x.canal === p.canal && x.id === p.id);
      if ((p.etapa === 'renderizando' || p.etapa === 'conferindo') && agora && agora.etapa !== p.etapa)
        toast(agora.etapa === 'erro' ? `Falhou: ${p.titulo}` : `${p.etapa === 'renderizando' ? 'Render concluído' : 'Conferência pronta'}: ${p.titulo}`, agora.etapa === 'erro');
    }
    $('#vivo').textContent = 'ao vivo';
    $('#vivo').classList.add('on');
    preencherCanais();
    atualizar();
  } catch (e) {
    $('#vivo').textContent = 'sem conexão';
    $('#vivo').classList.remove('on');
  }
}
setInterval(carregar, 3000);

function preencherCanais() {
  const sel = $('#canal');
  if (sel.options.length > 1) return;
  for (const [c, info] of Object.entries(D.canais)) {
    const o = document.createElement('option');
    o.value = c; o.textContent = NOME_CANAL[c] || info.nome;
    sel.appendChild(o);
  }
  try { sel.value = localStorage.getItem('canal') || ''; } catch (e) {}
}
const canalSel = () => $('#canal').value;
const prod = () => D.producao.filter(p => !canalSel() || p.canal === canalSel());

async function acao(dados, botao) {
  if (botao) botao.disabled = true;
  try {
    const r = await fetch('/api/acao', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
    const j = await r.json();
    toast(j.msg || j.erro || 'Feito.', !j.ok);
    await carregar();
    if (DET) abrirDetalhe(DET.canal, DET.id, DET.aba);
  } catch (e) {
    toast('Não consegui falar com o app.', true);
  } finally {
    if (botao) botao.disabled = false;
  }
}

function toast(msg, erro) {
  const t = $('#toast');
  t.textContent = msg; t.className = 'toast' + (erro ? ' erro' : ''); t.hidden = false;
  clearTimeout(t._h); t._h = setTimeout(() => (t.hidden = true), 4200);
}

// ---------------- helpers de tela ----------------
const etq = (etapa) => { const e = ETAPA[etapa] || { nome: etapa, cls: '' }; return `<span class="etq ${e.cls}">${esc(e.nome)}</span>`; };
const canalTag = (c) => `<span class="ponto ${c}"></span>${esc(NOME_CANAL[c] || c)}`;
const mmss = (s) => s == null ? '' : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
const img = (src, cls = '') => src ? `<img src="${src}" alt="" loading="lazy" class="${cls}">` : `<div class="semimg ${cls}">sem miniatura</div>`;
function quando(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}
function eta(seg) {
  if (seg == null) return 'calculando…';
  const fim = new Date(Date.now() + seg * 1000);
  return `faltam ~${Math.max(1, Math.round(seg / 60))} min (termina ${fim.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })})`;
}
function metaLinha(p) {
  const partes = [canalTag(p.canal), p.formato === 'short' ? 'Short' : 'Longo'];
  if (p.duracao) partes.push(mmss(p.duracao));
  if (p.cenas) partes.push(`${p.cenas} cenas`);
  if (p.slot && !['publicado'].includes(p.etapa)) partes.push(`sai ${quando(p.slot)}`);
  if (p.etapa === 'na_fila' && p.fila_pos) partes.push(`${p.fila_pos}º na fila`);
  return partes.join(' · ');
}

// ---------------- roteamento ----------------
function atualizar() {
  const n = D.producao.filter(p => p.etapa === 'enviado' || p.etapa === 'manual').length;
  $('#cont-prod').textContent = n || '';
  if (DET) return atualizarDetalhe();
  if (VIEW === 'metricas' || VIEW === 'atividade' || VIEW === 'agentes') {
    const sig = VIEW + canalSel() + JSON.stringify(D.canais) + (D.log[0] || '') + JSON.stringify(D.tarefas) + JSON.stringify(D.rodada);
    if (sig === atualizar._sig) return;
    atualizar._sig = sig;
  } else atualizar._sig = null;
  ({ geral: telaGeral, producao: telaProducao, agentes: telaAgentes, metricas: telaMetricas, atividade: telaAtividade })[VIEW]();
}
$('#nav').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-v]'); if (!b) return;
  VIEW = b.dataset.v; DET = null; atualizar._sig = null;
  document.querySelectorAll('#nav button').forEach(x => x.classList.toggle('ativo', x === b));
  $('#main').scrollTop = 0;
  atualizar();
});
$('#canal').addEventListener('change', () => { try { localStorage.setItem('canal', canalSel()); } catch (e) {} DET = null; atualizar(); });
$('#cfg').addEventListener('click', (e) => { e.stopPropagation(); $('#menu').hidden = !$('#menu').hidden; });
document.addEventListener('click', () => ($('#menu').hidden = true));
$('#menu').addEventListener('click', (e) => {
  const a = e.target.closest('button')?.dataset.a; if (!a) return;
  if (a === 'tema') {
    const escuro = document.documentElement.dataset.theme === 'dark';
    document.documentElement.dataset.theme = escuro ? 'light' : 'dark';
    try { localStorage.setItem('tema', document.documentElement.dataset.theme); } catch (er) {}
    return;
  }
  if (a === 'entregas') return acao({ acao: 'abrir_arquivo', caminho: 'Entregas' });
  acao({ acao: a });
});
$('#main').addEventListener('click', (e) => {
  const b = e.target.closest('[data-acao]');
  if (b) { e.stopPropagation(); return acao({ ...b.dataset, acao: b.dataset.acao }, b); }
  const ab = e.target.closest('[data-abrir]');
  if (ab) { const [c, i] = ab.dataset.abrir.split('|'); abrirDetalhe(c, i); }
});

// ---------------- Visão geral ----------------
function cartaoRender(p) {
  const st = p.status || {};
  const idx = PASSOS.findIndex(x => x[0] === p.sub);
  const passos = PASSOS.map(([k, nome], i) => `<span class="passo ${i < idx ? 'feito' : i === idx ? 'atual' : ''}">${nome}</span>`).join('');
  const modo = p.etapa === 'conferindo' ? 'Conferência rápida (sem o vídeo final)' : 'Render final';
  const barra = p.sub === 'render'
    ? `<div class="barra"><i style="width:${(p.pct * 100).toFixed(1)}%"></i></div>
       <div class="pct num"><span>${(p.pct * 100).toFixed(0)}% do vídeo</span><span>${eta(p.eta)}</span></div>`
    : `<div class="meta">Etapa: ${esc(PASSOS[idx]?.[1] || p.sub)} · começou ${st.desde ? new Date(st.desde * 1000).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : ''}</div>`;
  return `<div class="cartao agora" data-abrir="${p.canal}|${p.id}" style="cursor:pointer">
    ${img(p.thumb)}
    <div><div class="titulo">${esc(p.titulo)}</div><div class="meta">${metaLinha(p)} · ${modo}</div>
    <div class="passos">${passos}</div>${barra}</div></div>`;
}
function telaGeral() {
  const ps = prod();
  const ativos = ps.filter(p => p.etapa === 'renderizando' || p.etapa === 'conferindo');
  const esperando = ps.filter(p => p.etapa === 'enviado' || p.etapa === 'manual');
  const agenda = ps.filter(p => p.etapa === 'agendado' || p.etapa === 'aprovado').sort((a, b) => (a.publica_em || '').localeCompare(b.publica_em || ''));
  const problemas = ps.filter(p => p.etapa === 'erro' || p.etapa === 'recusado');
  const canais = Object.entries(D.canais).filter(([c]) => !canalSel() || c === canalSel());
  const hoje = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });

  $('#main').innerHTML = `
  <div class="topo"><div><h1>Visão geral</h1><p>${hoje}</p></div></div>

  <div class="secao"><h2>Agora</h2>
    ${ativos.length ? ativos.map(cartaoRender).join('') : '<div class="cartao vazio">Nada renderizando agora.</div>'}
  </div>

  <div class="secao"><h2>Esperando você</h2>
    <div class="cartao">${esperando.length ? `<ul class="lista">${esperando.map(p => `
      <li data-abrir="${p.canal}|${p.id}">${img(p.thumb)}
        <div style="min-width:0"><div class="t">${esc(p.titulo)}</div><div class="meta">${metaLinha(p)}</div></div>
        <div class="dir">${p.etapa === 'enviado'
          ? `<button class="bt ok peq" data-acao="aprovar" data-canal="${p.canal}" data-id="${p.id}">Aprovar</button>
             <button class="bt peq" data-acao="recusar" data-canal="${p.canal}" data-id="${p.id}">Refazer</button>`
          : `<button class="bt peq" data-acao="studio" data-youtube_id="${p.youtube_id}">Abrir no Studio</button>`}</div>
      </li>`).join('')}</ul>` : '<div class="vazio">Nada esperando aprovação.</div>'}</div>
  </div>

  ${problemas.length ? `<div class="secao"><h2>Com problema</h2><div class="cartao"><ul class="lista">${problemas.map(p => `
      <li data-abrir="${p.canal}|${p.id}">${img(p.thumb)}
        <div style="min-width:0"><div class="t">${esc(p.titulo)}</div><div class="meta">${esc(p.erro || 'Você pediu para refazer.')}</div></div>
        <div class="dir">${etq(p.etapa)}</div></li>`).join('')}</ul></div></div>` : ''}

  <div class="secao"><h2>Canais</h2><div class="grade2">${canais.map(([c, k]) => `
    <div class="cartao canal">
      <div class="canal-top"><strong>${canalTag(c)}</strong>${k.url ? `<a href="${k.url}" target="_blank" class="meta">abrir canal ↗</a>` : ''}</div>
      <div class="nums num">
        <div><b>${fmt(k.inscritos)}</b><span>inscritos</span></div>
        <div><b>${fmt(k.views)}</b><span>views</span></div>
        <div><b>${fmt(k.videos)}</b><span>vídeos</span></div>
        <div><b>${fmt(k.mediana)}</b><span>mediana</span></div>
      </div>
      <p>Nicho principal: <b>${esc(k.nicho?.principal || '—')}</b></p>
      <p>Testando: ${esc((k.nicho?.testes || []).join(', ') || '—')}</p>
      <p>Regra do nicho: ${esc(k.nicho?.recomendacao?.porque || 'sem avaliação ainda')}</p>
      <p class="meta">Métricas de ${k.coletado ? new Date(k.coletado).toLocaleString('pt-BR') : 'nunca'}${k.token ? '' : ' · <b style="color:var(--erro)">sem acesso ao YouTube</b>'}</p>
    </div>`).join('')}</div></div>

  <div class="secao"><h2>Na agenda</h2>
    <div class="cartao">${agenda.length ? `<ul class="lista">${agenda.map(p => `
      <li data-abrir="${p.canal}|${p.id}">${img(p.thumb)}
        <div style="min-width:0"><div class="t">${esc(p.titulo)}</div><div class="meta">${metaLinha(p)}</div></div>
        <div class="dir"><span class="meta num">${quando(p.publica_em)}</span>${etq(p.etapa)}</div></li>`).join('')}</ul>`
        : '<div class="vazio">Nada agendado.</div>'}</div>
  </div>`;
}

// ---------------- Produção ----------------
function telaProducao() {
  const foco = document.activeElement?.id;
  let ps = prod();
  if (FILTRO.etapa) ps = ps.filter(p => GRUPOS.find(g => g[0] === FILTRO.etapa)[1].includes(p.etapa));
  if (FILTRO.busca) ps = ps.filter(p => (p.titulo + ' ' + p.id).toLowerCase().includes(FILTRO.busca.toLowerCase()));
  const linha = (p) => `
    <li data-abrir="${p.canal}|${p.id}">${img(p.thumb)}
      <div style="min-width:0"><div class="t">${esc(p.titulo)}</div><div class="meta">${metaLinha(p)}</div>
      ${p.sub === 'render' ? `<div class="barra fina" style="margin-top:6px;max-width:360px"><i style="width:${(p.pct * 100).toFixed(1)}%"></i></div>` : ''}</div>
      <div class="dir">${p.etapa === 'renderizando' || p.etapa === 'conferindo' ? `<span class="meta">${esc(PASSOS.find(x => x[0] === p.sub)?.[1] || '')}${p.sub === 'render' ? ' ' + (p.pct * 100).toFixed(0) + '%' : ''}</span>` : ''}
      ${p.publica_em && p.etapa === 'agendado' ? `<span class="meta num">${quando(p.publica_em)}</span>` : ''}${etq(p.etapa)}</div>
    </li>`;
  const grupos = GRUPOS.map(([nome, ets]) => [nome, ps.filter(p => ets.includes(p.etapa))]).filter(g => g[1].length);
  $('#main').innerHTML = `
  <div class="topo"><div><h1>Produção</h1><p>Do roteiro ao vídeo no ar. Clique num vídeo para ver roteiro, imagens, render e ações.</p></div>
    <div class="filtros">
      <select id="f-etapa"><option value="">Todas as etapas</option>${GRUPOS.map(g => `<option ${FILTRO.etapa === g[0] ? 'selected' : ''}>${g[0]}</option>`).join('')}</select>
      <input id="f-busca" type="search" placeholder="Buscar título…" value="${esc(FILTRO.busca)}">
    </div></div>
  ${grupos.length ? grupos.map(([nome, l]) => `<div class="grupo-tit">${nome}<span class="n">${l.length}</span></div>
    <div class="cartao"><ul class="lista">${l.map(linha).join('')}</ul></div>`).join('') : '<div class="cartao vazio">Nenhum vídeo com esse filtro.</div>'}`;
  $('#f-etapa').onchange = (e) => { FILTRO.etapa = e.target.value; telaProducao(); };
  const b = $('#f-busca');
  b.oninput = (e) => { FILTRO.busca = e.target.value; telaProducao(); };
  if (foco === 'f-busca') { b.focus(); b.setSelectionRange(b.value.length, b.value.length); }
}

// ---------------- Detalhe ----------------
async function abrirDetalhe(canal, id, aba) {
  const r = await fetch(`/api/item?canal=${encodeURIComponent(canal)}&id=${encodeURIComponent(id)}`, { cache: 'no-store' });
  const dados = await r.json();
  const mesmo = DET && DET.canal === canal && DET.id === id;
  DET = { canal, id, aba: aba || (mesmo ? DET.aba : null) || 'video', dados };
  telaDetalhe();
  if (!mesmo) $('#main').scrollTop = 0;
}
function atualizarDetalhe() {
  // só o cabeçalho (status/ações) muda sozinho; o conteúdo (vídeo tocando) fica
  const p = D.producao.find(x => x.canal === DET.canal && x.id === DET.id);
  if (!p) return;
  const antes = DET.etapa;
  DET.p = p;
  if (antes && antes !== p.etapa) return abrirDetalhe(DET.canal, DET.id);   // mudou de etapa: recarrega tudo
  DET.etapa = p.etapa;
  const cab = $('#det-cab'); if (cab) cab.innerHTML = cabecalho(p);
}
function cabecalho(p) {
  const bt = [];
  const d = { canal: p.canal, id: p.id };
  const b = (a, txt, cls = '') => `<button class="bt ${cls}" data-acao="${a}" data-canal="${d.canal}" data-id="${d.id}">${txt}</button>`;
  if (p.motor === 'pro' && ['roteiro', 'erro', 'conferencia', 'recusado'].includes(p.etapa)) bt.push(b('conferir', p.etapa === 'conferencia' ? 'Conferir de novo' : 'Conferir (rápido)', p.etapa === 'conferencia' ? '' : 'pri'));
  if (p.motor === 'pro' && p.etapa === 'conferencia') bt.push(b('renderizar', 'Render final', 'pri'));
  if (p.etapa === 'enviado') { bt.push(b('aprovar', 'Aprovar', 'ok')); bt.push(b('recusar', 'Refazer')); }
  if (['pronto', 'aprovado', 'agendado'].includes(p.etapa)) bt.push(b('vetar', 'Vetar (tirar do ar)'));
  if (p.youtube_id) bt.push(`<button class="bt" data-acao="studio" data-youtube_id="${p.youtube_id}">Abrir no Studio ↗</button>`);
  bt.push(b('abrir', 'Abrir pasta'));
  const ativo = p.etapa === 'renderizando' || p.etapa === 'conferindo';
  const prog = ativo ? `<div style="margin-top:12px;max-width:620px">${cartaoProgresso(p)}</div>` : '';
  return `<div class="det-top"><div><h1>${esc(p.titulo)}</h1>
    <div class="meta" style="margin-top:6px">${metaLinha(p)} · ${etq(p.etapa)} ${p.publica_em && p.etapa === 'agendado' ? '· vai ao ar ' + quando(p.publica_em) : ''}</div>${prog}</div>
    <div class="acoes">${bt.join('')}</div></div>
    ${p.etapa === 'erro' ? `<div class="erro-box">${esc(p.erro)}</div>` : ''}`;
}
function cartaoProgresso(p) {
  const idx = PASSOS.findIndex(x => x[0] === p.sub);
  return `<div class="passos">${PASSOS.map(([k, n], i) => `<span class="passo ${i < idx ? 'feito' : i === idx ? 'atual' : ''}">${n}</span>`).join('')}</div>
    ${p.sub === 'render' ? `<div class="barra"><i style="width:${(p.pct * 100).toFixed(1)}%"></i></div><div class="pct num"><span>${(p.pct * 100).toFixed(0)}%</span><span>${eta(p.eta)}</span></div>` : ''}`;
}
function telaDetalhe() {
  const { dados, aba } = DET;
  const p = D.producao.find(x => x.canal === DET.canal && x.id === DET.id) || { canal: DET.canal, id: DET.id, titulo: dados.roteiro.titulo || DET.id, etapa: 'roteiro' };
  DET.etapa = p.etapa;
  const abas = [['video', 'Vídeo'], ['roteiro', 'Roteiro'], ['imagens', 'Imagens e quadros'], ['descricao', 'Descrição'], ['historico', 'Histórico e log']];
  $('#main').innerHTML = `
    <button class="voltar" id="voltar">← ${VIEW === 'geral' ? 'Visão geral' : 'Produção'}</button>
    <div id="det-cab">${cabecalho(p)}</div>
    <div class="abas">${abas.map(([k, n]) => `<button data-aba="${k}" class="${aba === k ? 'ativo' : ''}">${n}</button>`).join('')}</div>
    <div id="det-corpo">${({ video: abaVideo, roteiro: abaRoteiro, imagens: abaImagens, descricao: abaDescricao, historico: abaHistorico })[aba](dados, p)}</div>`;
  $('#voltar').onclick = () => { DET = null; atualizar(); };
  document.querySelectorAll('.abas button').forEach(b => b.onclick = () => { DET.aba = b.dataset.aba; telaDetalhe(); });
}
function abaVideo(d, p) {
  const r = d.roteiro, f = d.final;
  const titulos = r.titulos_alternativos || [];
  const caps = (r.cenas || []).filter(c => c.capitulo).map(c => c.capitulo);
  return `<div class="det-grid">
    <div>${d.video ? `<video controls preload="metadata" poster="${d.thumb || ''}" src="${d.video}"></video>`
      : d.thumb ? `<img class="grande" src="${d.thumb}" alt="miniatura">` : '<div class="cartao vazio">Ainda sem vídeo nem miniatura — rode a conferência.</div>'}
      ${d.video && d.thumb ? `<h2 style="margin-top:18px">Miniatura</h2><img class="grande" src="${d.thumb}" alt="miniatura" style="max-width:420px">` : ''}</div>
    <div class="cartao fatos"><dl>
      <dt>Canal</dt><dd>${canalTag(p.canal)}</dd>
      <dt>Formato</dt><dd>${r.formato === 'short' ? 'Short' : 'Longo'}</dd>
      <dt>Duração</dt><dd class="num">${f.duracao ? mmss(f.duracao) : p.duracao ? mmss(p.duracao) : '—'}</dd>
      <dt>Cenas</dt><dd>${(r.cenas || r.slides || []).length}</dd>
      <dt>Nicho</dt><dd>${esc(r.nicho || '—')}</dd>
      <dt>Miniatura</dt><dd>${esc((r.miniatura?.texto || '—').replace('|', ' / '))}</dd>
    </dl>
    ${titulos.length ? `<h2 style="margin-top:16px">Títulos (o 1º é o usado)</h2><ol>${titulos.map(t => `<li>${esc(t)}</li>`).join('')}</ol>` : ''}
    ${caps.length ? `<h2 style="margin-top:16px">Capítulos</h2><ol>${caps.map(t => `<li>${esc(t)}</li>`).join('')}</ol>` : ''}
    </div></div>`;
}
function abaRoteiro(d) {
  const cenas = d.roteiro.cenas;
  if (!cenas) return '<div class="cartao vazio">Este vídeo é do motor antigo (sem roteiro por cenas).</div>';
  const vis = (v) => {
    const t = v.texto || v.rotulo || (v.valor != null ? `${v.prefixo || ''}${v.valor}${v.sufixo || ''}` : '') || v.titulo || (v.a ? `${v.a.rotulo} × ${v.b.rotulo}` : '');
    const imgs = (v.imagens || (v.imagem ? [v.imagem] : [])).join(' · ');
    return `<span class="tipo">${esc(v.tipo)}</span>${esc(String(t).replace(/\|/g, ' / '))}${imgs ? `<div class="meta">fotos: ${esc(imgs)}</div>` : ''}`;
  };
  let n = 0, palavras = 0;
  const linhas = cenas.map(c => {
    n++; palavras += c.fala.split(/\s+/).length;
    const fala = esc(c.fala).replace(/\[(pausa longa|pausa)\]/g, '<span class="pausa">[$1]</span>');
    return `${c.capitulo ? `<tr class="cap"><td colspan="3">${esc(c.capitulo)}</td></tr>` : ''}
      <tr><td class="meta num">${n}</td><td>${fala}</td><td class="vis">${vis(c.visual || {})}</td></tr>`;
  }).join('');
  return `<p class="meta">${cenas.length} cenas · ${fmt(palavras)} palavras (≈ ${Math.round(palavras / 175)} min de fala) ·
    <a href="#" id="abrir-json">abrir o arquivo do roteiro</a></p>
    <div class="cartao" style="overflow:hidden"><table class="cenas"><thead><tr><th>#</th><th>Fala</th><th>O que aparece</th></tr></thead><tbody>${linhas}</tbody></table></div>`;
}
document.addEventListener('click', (e) => {
  if (e.target.id === 'abrir-json') { e.preventDefault(); acao({ acao: 'abrir_arquivo', caminho: `episodios/${DET.canal}/${DET.id}.json` }); }
});
function abaImagens(d) {
  if (!d.imagens && !d.confere.length) return '<div class="cartao vazio">Ainda não conferido. Use "Conferir (rápido)": gera voz, busca as imagens, a miniatura e 3 quadros do vídeo.</div>';
  return `${d.confere.length ? `<h2>Quadros de conferência (início, meio e fim)</h2><div class="quadros">${d.confere.map(q => `<img src="${q}" alt="">`).join('')}${d.thumb ? `<img src="${d.thumb}" alt="miniatura">` : ''}</div>` : ''}
    ${d.imagens ? `<h2 style="margin-top:24px">Todas as fotos usadas (por cena)</h2><img class="folha" src="${d.imagens}" alt="folha de contato">` : ''}`;
}
function abaDescricao(d) {
  const r = d.roteiro, f = d.final;
  const desc = f.descricao_final || d.item?.descricao || r.descricao || '';
  return `<div class="det-grid"><div><pre class="texto">${esc(desc)}</pre>
    ${f.descricao_final ? '' : '<p class="meta">Capítulos, fontes e créditos das imagens entram aqui depois do render final.</p>'}</div>
    <div class="cartao fatos"><h2>Tags</h2><div class="tags">${(r.tags || []).map(t => `<span class="etq">${esc(t)}</span>`).join('')}</div>
    ${r.fontes ? `<h2 style="margin-top:14px">Fontes</h2><ol>${r.fontes.map(x => `<li>${esc(x)}</li>`).join('')}</ol>` : ''}
    ${d.legendas ? `<p style="margin-top:14px"><a href="${d.legendas}" target="_blank">legendas.srt</a> (para subir no Studio, se quiser)</p>` : ''}</div></div>`;
}
function abaHistorico(d) {
  const h = d.item?.historico || [];
  const st = d.status;
  return `<div class="det-grid"><div>
    <h2>Linha do tempo</h2>
    ${h.length ? `<ul class="linha-tempo">${h.map(x => `<li><b>${esc((ETAPA[x.para] || { nome: x.para }).nome)}</b> <span class="meta">${new Date(x.quando).toLocaleString('pt-BR')}</span><div class="meta">${esc(x.nota || '')}</div></li>`).join('')}</ul>`
      : '<div class="cartao vazio">Ainda não entrou na fila do YouTube.</div>'}
    ${d.logs.map(l => `<h2 style="margin-top:20px">Log (${esc(l.nome)})</h2><pre class="log">${esc(l.texto)}</pre>`).join('')}
  </div><div class="cartao fatos"><h2>Último processamento</h2>${st ? `<dl>
    <dt>Modo</dt><dd>${st.modo === 'final' ? 'Render final' : 'Conferência'}</dd>
    <dt>Etapa</dt><dd>${esc(st.etapa)}</dd>
    <dt>Início</dt><dd>${st.inicio ? new Date(st.inicio * 1000).toLocaleString('pt-BR') : '—'}</dd>
    <dt>Atualizado</dt><dd>${st.atualizado ? new Date(st.atualizado * 1000).toLocaleString('pt-BR') : '—'}</dd>
    ${st.msg ? `<dt>Mensagem</dt><dd>${esc(st.msg)}</dd>` : ''}</dl>` : '<p class="meta">Nunca processado pelo motor novo.</p>'}</div></div>`;
}

// ---------------- Agentes ----------------
const MODELO = { opus: ['Opus', 'o mais capaz: criação'], sonnet: ['Sonnet', 'julgamento + visão'], haiku: ['Haiku', 'rápido: tarefas de regra'] };
function telaAgentes() {
  const r = D.rodada || { passos: [] };
  const feitos = r.passos.filter(x => x.feito === true).length, comStatus = r.passos.filter(x => x.feito !== null).length;
  $('#main').innerHTML = `<div class="topo"><div><h1>Agentes</h1><p>A equipe que produz os dois canais sozinha: rodada diária às 06:30, render no Windows, envio e agendamento automáticos (longo 19:00, Short 20:00).</p></div></div>
  <div class="secao"><h2>Rodada de hoje (${new Date(r.data + 'T12:00').toLocaleDateString('pt-BR')})</h2>
    <div class="cartao"><ul class="lista">${r.passos.map(x => `<li style="grid-template-columns:28px 1fr auto;cursor:default">
      <span style="font-size:16px">${x.feito === true ? '✅' : x.feito === false ? '⏳' : '•'}</span>
      <div><div class="t">${esc(x.nome)}</div><div class="meta">${esc(x.agente)}</div></div><div></div></li>`).join('')}</ul></div>
    ${r.resumo ? `<h2 style="margin-top:18px">Resumo do maestro</h2><pre class="texto">${esc(r.resumo)}</pre>` : `<p class="meta">${feitos} de ${comStatus} etapas com arquivo entregue · ${r.pedidos} pedido(s) de render hoje.</p>`}
  </div>
  <div class="secao"><h2>A equipe</h2><div class="grade2">${(D.agentes || []).map(a => {
    const m = MODELO[a.modelo] || [a.modelo, ''];
    return `<div class="cartao canal"><div class="canal-top"><strong>${esc(a.nome)}</strong><span class="etq ${a.modelo === 'opus' ? 'alerta' : a.modelo === 'sonnet' ? 'azul' : ''}">${esc(m[0])}</span></div>
      <p>${esc(a.descricao)}</p><p class="meta">${esc(m[1])}</p></div>`;
  }).join('')}</div></div>`;
}

// ---------------- Métricas ----------------
function grafico(dias, cor) {
  const W = 760, H = 200, ml = 44, mb = 24, mt = 8;
  const vals = dias.map(d => d.views || 0);
  const max = Math.max(4, ...vals);
  const passo = Math.pow(10, Math.floor(Math.log10(max))) * (max / Math.pow(10, Math.floor(Math.log10(max))) > 5 ? 2 : 1);
  const topo = Math.ceil(max / passo) * passo;
  const x = (i) => ml + i * ((W - ml - 8) / Math.max(1, dias.length - 1));
  const y = (v) => mt + (H - mt - mb) * (1 - v / topo);
  const marcas = []; for (let v = 0; v <= topo; v += topo / 4) marcas.push(v);
  const pts = vals.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" data-dias='${esc(JSON.stringify(dias.map(d => [d.day, d.views || 0])))}'>
    ${marcas.map(v => `<line class="grade" x1="${ml}" x2="${W - 8}" y1="${y(v)}" y2="${y(v)}"/><text x="${ml - 8}" y="${y(v) + 4}" text-anchor="end">${fmt(Math.round(v))}</text>`).join('')}
    ${dias.map((d, i) => i % 7 === 0 ? `<text x="${x(i)}" y="${H - 6}" text-anchor="middle">${d.day.slice(8, 10)}/${d.day.slice(5, 7)}</text>` : '').join('')}
    <polygon class="area" fill="${cor}" points="${ml},${y(0)} ${pts} ${x(vals.length - 1)},${y(0)}"/>
    <polyline class="serie" stroke="${cor}" points="${pts}" stroke-linejoin="round" stroke-linecap="round"/>
    <line class="cursor" x1="0" x2="0" y1="${mt}" y2="${H - mb}" stroke="var(--tinta3)" stroke-dasharray="3 3" visibility="hidden"/>
    <circle class="mk" r="4.5" fill="${cor}" stroke="var(--sup)" stroke-width="2" visibility="hidden"/>
    <rect x="${ml}" y="0" width="${W - ml}" height="${H}" fill="transparent" class="alvo"/>
  </svg>`;
}
function ligarDica(svg) {
  const dias = JSON.parse(svg.dataset.dias), W = 760, ml = 44;
  const alvo = svg.querySelector('.alvo'), cur = svg.querySelector('.cursor'), mk = svg.querySelector('.mk'), dica = $('#dica');
  const poly = svg.querySelector('.serie').getAttribute('points').split(' ').map(s => s.split(',').map(Number));
  alvo.addEventListener('mousemove', (e) => {
    const r = svg.getBoundingClientRect();
    const vx = (e.clientX - r.left) * W / r.width;
    const i = Math.max(0, Math.min(dias.length - 1, Math.round((vx - ml) / ((W - ml - 8) / Math.max(1, dias.length - 1)))));
    const [px, py] = poly[i];
    cur.setAttribute('x1', px); cur.setAttribute('x2', px); cur.setAttribute('visibility', 'visible');
    mk.setAttribute('cx', px); mk.setAttribute('cy', py); mk.setAttribute('visibility', 'visible');
    const [dia, v] = dias[i];
    dica.innerHTML = `${new Date(dia + 'T12:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} · <b>${fmt(v)}</b> views`;
    dica.hidden = false; dica.style.left = (e.clientX + 12) + 'px'; dica.style.top = (e.clientY - 34) + 'px';
  });
  alvo.addEventListener('mouseleave', () => { cur.setAttribute('visibility', 'hidden'); mk.setAttribute('visibility', 'hidden'); dica.hidden = true; });
}
function telaMetricas() {
  const canais = Object.entries(D.canais).filter(([c]) => !canalSel() || c === canalSel());
  const corDe = (c) => getComputedStyle(document.documentElement).getPropertyValue(c === 'gta6' ? '--gta6' : '--eng').trim();
  $('#main').innerHTML = `<div class="topo"><div><h1>Métricas</h1><p>Views por dia (últimos 28 dias) e desempenho de cada vídeo. Atualiza todo dia às 09:00 — ou pelo ⚙.</p></div></div>
  ${canais.map(([c, k]) => {
    const dias = (k.diario || []).slice(-28);
    const tot = dias.reduce((s, d) => s + (d.views || 0), 0);
    const lista = [...(k.lista || [])].sort((a, b) => (b.publicado || '').localeCompare(a.publicado || ''));
    return `<div class="secao"><h2>${canalTag(c)}</h2>
      <div class="cartao graf"><div class="meta" style="margin-bottom:6px">${fmt(tot)} views em ${dias.length} dias</div>
        ${dias.length ? grafico(dias, corDe(c)) : '<div class="vazio">Sem dados diários ainda.</div>'}</div>
      <div class="cartao" style="margin-top:12px;overflow:auto"><table class="tabela num">
        <thead><tr><th>Vídeo</th><th>Formato</th><th>Publicado</th><th class="n">Views</th><th class="n">x mediana</th><th>Nicho</th><th>Status</th></tr></thead>
        <tbody>${lista.length ? lista.map(v => `<tr><td>${esc(v.titulo)}</td><td>${v.formato === 'short' ? 'Short' : 'Longo'}</td>
          <td>${v.publicado ? new Date(v.publicado).toLocaleDateString('pt-BR') : '—'}</td><td class="n">${fmt(v.views)}</td>
          <td class="n">${v.multiplo != null ? v.multiplo.toFixed(1) + 'x' : '—'}</td><td>${esc(v.nicho || '—')}</td>
          <td>${v.privacidade === 'public' ? '<span class="etq ok">público</span>' : `<span class="etq">${esc(v.privacidade || '—')}</span>`}</td></tr>`).join('')
          : '<tr><td colspan="7" class="meta">Nenhum vídeo no canal ainda.</td></tr>'}</tbody></table></div></div>`;
  }).join('')}`;
  document.querySelectorAll('.graf svg').forEach(ligarDica);
}

// ---------------- Atividade ----------------
function telaAtividade() {
  const linhas = D.log.filter(l => !LOG_CANAL || l.includes(`[${LOG_CANAL}]`)).slice(0, 250);
  $('#main').innerHTML = `<div class="topo"><div><h1>Atividade</h1><p>Tudo o que os agentes fizeram, do mais recente para o mais antigo.</p></div>
    <div class="filtros"><select id="f-log"><option value="">Todos</option>${['engenhoso', 'gta6', 'kids'].map(c => `<option value="${c}" ${LOG_CANAL === c ? 'selected' : ''}>${NOME_CANAL[c] || 'SuperKids (antigo)'}</option>`).join('')}</select></div></div>
  <div class="secao"><h2>Rotinas automáticas</h2><div class="cartao" style="overflow:auto"><table class="tabela">
    <thead><tr><th>Rotina</th><th>Próxima execução</th><th>Situação</th><th>Última</th></tr></thead>
    <tbody>${D.tarefas.map(t => `<tr><td>${esc(t.nome)}</td><td class="num">${esc(t.proxima || '—')}</td><td>${esc(t.status || t.erro || '—')}</td><td class="num">${esc(t.ultima || '—')}</td></tr>`).join('')}</tbody></table></div></div>
  <div class="secao"><h2>Log dos agentes</h2><div class="cartao log-lista">${linhas.length ? linhas.map(l => {
    const m = l.match(/^(\S+)\s+(.*)$/);
    return `<div><span class="q">${esc(m ? new Date(m[1]).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '')}</span>${esc(m ? m[2] : l)}</div>`;
  }).join('') : '<div class="meta">Nada registrado.</div>'}</div></div>`;
  $('#f-log').onchange = (e) => { LOG_CANAL = e.target.value; atualizar._sig = null; telaAtividade(); };
}

carregar();
