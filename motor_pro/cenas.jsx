// Biblioteca de cenas do EffectCraft (modelo de objetos do After Effects).
// O render.py concatena este arquivo + "var D = {...dados...}; montar(D);" e roda com effectcraft-cli script.
// Cada cena vira uma pré-composição; a "Main" junta cenas, legendas, barra de progresso e áudio.

function cor(h) {
  h = h.replace("#", "");
  return [parseInt(h.substr(0, 2), 16) / 255, parseInt(h.substr(2, 2), 16) / 255, parseInt(h.substr(4, 2), 16) / 255];
}
function P(l, nome) { return l.property("Transform").property(nome); }
function fx(l, nome) { return l.property("Effects").addProperty(nome); }
function suave(prop) {
  var e = new KeyframeEase(0, 75);
  for (var k = 1; k <= prop.numKeys; k++) {
    try { prop.setTemporalEaseAtKey(k, [e], [e]); } catch (err) {}
  }
}
function suave3(prop) {
  var e = new KeyframeEase(0, 75);
  for (var k = 1; k <= prop.numKeys; k++) {
    try { prop.setTemporalEaseAtKey(k, [e, e, e], [e, e, e]); } catch (err) {
      try { prop.setTemporalEaseAtKey(k, [e], [e]); } catch (err2) {}
    }
  }
}

// ---------- texto ----------
function texto(comp, str, o) {
  var T = D.tema;
  var l = o.caixa ? comp.layers.addBoxText(o.caixa, str) : comp.layers.addText(str);
  var p = l.property("Text").property("Source Text");
  var d = p.value;
  if (o.caixaAlta) str = str.toUpperCase();
  d.text = str;
  d.font = o.fonte || T.fonte_titulo;
  d.fontSize = o.tam || 100;
  d.fillColor = cor(o.cor || T.texto);
  d.justification = o.just === "esq" ? ParagraphJustification.LEFT_JUSTIFY :
    (o.just === "dir" ? ParagraphJustification.RIGHT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY);
  if (o.entre) d.leading = o.entre;
  if (o.track) d.tracking = o.track;
  if (o.contorno) {
    d.applyStroke = true; d.strokeColor = cor(o.contorno); d.strokeWidth = o.contornoL || 8; d.strokeOverFill = false;
  }
  p.setValue(d);
  // âncora no centro vertical do texto (o padrão é a linha de base)
  var r = l.sourceRectAtTime(0, false);
  var ax = o.just === "esq" ? r.left : (o.just === "dir" ? r.left + r.width : r.left + r.width / 2);
  P(l, "Anchor Point").setValue([ax, r.top + r.height / 2]);
  if (o.max && r.width > o.max) {
    var s = 100 * o.max / r.width; P(l, "Scale").setValue([s, s]);
  }
  P(l, "Position").setValue([o.x, o.y]);
  if (o.sombraReal) {
    // sombra de verdade (desfocada): cara (~100 ms/quadro) - só na miniatura, que é 1 quadro
    var ds = fx(l, "ADBE Drop Shadow");
    ds.property("Opacity").setValue(o.sombraOp || 170);
    ds.property("Distance").setValue(o.sombraD || 6);
    ds.property("Softness").setValue(o.sombraS || 18);
  } else if (o.sombra !== false && !o.caixa) {
    // sombra barata: cópia preta deslocada que segue o texto por expressão
    D._n = (D._n || 0) + 1;
    l.name = "txt" + D._n;
    var sh = comp.layers.addText(str);
    var ps = sh.property("Text").property("Source Text"), ds2 = ps.value;
    ds2.text = d.text; ds2.font = d.font; ds2.fontSize = d.fontSize; ds2.justification = d.justification;
    if (o.entre) ds2.leading = o.entre;
    if (o.track) ds2.tracking = o.track;
    ds2.fillColor = [0, 0, 0];
    ps.setValue(ds2);
    P(sh, "Anchor Point").setValue(P(l, "Anchor Point").value);
    var k = Math.max(3, (o.tam || 100) * 0.045);
    P(sh, "Position").expression = "thisComp.layer('" + l.name + "').transform.position + [" + k + "," + k + "]";
    P(sh, "Scale").expression = "thisComp.layer('" + l.name + "').transform.scale";
    P(sh, "Opacity").expression = "thisComp.layer('" + l.name + "').transform.opacity * 0.55";
    ps.expression = "thisComp.layer('" + l.name + "').text.sourceText";
    sh.moveAfter(l);
  }
  return l;
}
function largura(l) { var r = l.sourceRectAtTime(0, false); return r.width * P(l, "Scale").value[0] / 100; }
function altura(l) { var r = l.sourceRectAtTime(0, false); return r.height * P(l, "Scale").value[1] / 100; }

// ---------- animações de entrada ----------
function entra(l, t0, tipo, dur) {
  dur = dur || 0.45;
  var pos = P(l, "Position"), op = P(l, "Opacity"), sc = P(l, "Scale");
  var p = pos.value, s = sc.value;
  op.setValueAtTime(t0, 0); op.setValueAtTime(t0 + dur * 0.6, 100);
  if (tipo === "sobe") {
    pos.setValueAtTime(t0, [p[0], p[1] + 70]); pos.setValueAtTime(t0 + dur, p); suave3(pos);
  } else if (tipo === "esq") {
    pos.setValueAtTime(t0, [p[0] - 120, p[1]]); pos.setValueAtTime(t0 + dur, p); suave3(pos);
  } else if (tipo === "pop") {
    sc.setValueAtTime(t0, [s[0] * 0.6, s[1] * 0.6]);
    sc.setValueAtTime(t0 + dur * 0.65, [s[0] * 1.06, s[1] * 1.06]);
    sc.setValueAtTime(t0 + dur, s); suave3(sc);
  } else if (tipo === "zoom") {
    sc.setValueAtTime(t0, [s[0] * 1.25, s[1] * 1.25]); sc.setValueAtTime(t0 + dur, s); suave3(sc);
  }
}
function escala(l, t0, dur) {
  var sc = P(l, "Scale"), s = sc.value;
  sc.setValueAtTime(t0, [s[0] * 0.86, s[1] * 0.86]); sc.setValueAtTime(t0 + dur, s); suave3(sc);
}
function barraX(comp, x, y, w, h, c, t0, dur, ancoraEsq) {
  var b = comp.layers.addSolid(cor(c), "barra", Math.max(2, Math.round(w)), Math.max(2, Math.round(h)), 1);
  P(b, "Anchor Point").setValue([ancoraEsq ? 0 : w / 2, h / 2]);
  P(b, "Position").setValue([x, y]);
  var sc = P(b, "Scale");
  sc.setValueAtTime(t0, [0, 100]); sc.setValueAtTime(t0 + (dur || 0.5), [100, 100]); suave3(sc);
  return b;
}

// ---------- fundos ----------
function fundo(comp, c1, c2) {
  var T = D.tema;
  var s = comp.layers.addSolid(cor(c1 || T.fundo1), "fundo", comp.width, comp.height, 1);
  var r = fx(s, "ADBE Ramp");
  r.property("Start Color").setValue(cor(c1 || T.fundo1));
  r.property("End Color").setValue(cor(c2 || T.fundo2));
  r.property("Ramp Shape").setValue(2); // radial
  r.property("Start of Ramp").expression = "[" + comp.width * 0.3 + "+" + comp.width * 0.15 + "*Math.sin(time*0.25)," + comp.height * 0.35 + "]";
  r.property("End of Ramp").setValue([comp.width * 1.1, comp.height * 1.2]);
  return s;
}
function foto(comp, arq, t0, dur, mov) {
  var it = D._imgs[arq];
  if (!it) { it = app.project.importFile(new ImportOptions(new File(arq))); D._imgs[arq] = it; }
  var l = comp.layers.add(it);
  var cobre = Math.max(comp.width / l.width, comp.height / l.height) * 100;
  var sc = P(l, "Scale"), pos = P(l, "Position");
  var a = cobre * 1.04, b = cobre * 1.16;
  var dx = comp.width * 0.035;
  mov = mov % 4;
  var z0 = mov === 1 ? b : a, z1 = mov === 1 ? a : b;
  sc.setValueAtTime(t0, [z0, z0]); sc.setValueAtTime(t0 + dur, [z1, z1]);
  var x0 = comp.width / 2 + (mov === 2 ? -dx : (mov === 3 ? dx : 0));
  var x1 = comp.width / 2 + (mov === 2 ? dx : (mov === 3 ? -dx : 0));
  pos.setValueAtTime(t0, [x0, comp.height / 2]); pos.setValueAtTime(t0 + dur, [x1, comp.height / 2]);
  l.inPoint = t0; l.outPoint = t0 + dur;
  return l;
}
function escurecer(comp, op, baixo) {
  var s = comp.layers.addSolid([0, 0, 0], "escuro", comp.width, comp.height, 1);
  P(s, "Opacity").setValue(op);
  if (baixo) {
    var g = comp.layers.addSolid(cor(D.tema.fundo1), "degrade", comp.width, comp.height, 1);
    var w = fx(g, "ADBE Linear Wipe");
    w.property("Transition Completion").setValue(55);
    w.property("Wipe Angle").setValue(0);
    w.property("Feather").setValue(comp.height * 0.45);
    P(g, "Opacity").setValue(92);
  }
}
// cena oficial (trailer etc.): trechos de até 6 s, sem áudio, com leve aproximação e crédito na tela
function clipe(comp, arq, t0, dur) {
  var it = D._imgs[arq];
  if (!it) { it = app.project.importFile(new ImportOptions(new File(arq))); D._imgs[arq] = it; }
  var l = comp.layers.add(it);
  l.startTime = t0; l.inPoint = t0; l.outPoint = t0 + Math.min(dur, it.duration);
  var cobre = Math.max(comp.width / l.width, comp.height / l.height) * 100;
  var sc = P(l, "Scale");
  sc.setValueAtTime(t0, [cobre * 1.0, cobre * 1.0]); sc.setValueAtTime(t0 + dur, [cobre * 1.06, cobre * 1.06]);
  P(l, "Position").setValue([comp.width / 2, comp.height / 2]);
  try { l.audioEnabled = false; } catch (e) {}
  return l;
}
function fotos(comp, v, dur) {
  var cl = v._clipes || [];
  if (cl.length) {
    var m = Math.max(cl.length, Math.ceil(dur / 6));
    var p2 = dur / m;
    for (var j = 0; j < m; j++) clipe(comp, cl[j % cl.length], j * p2, p2 + 0.04);
    if (v._credito) {
      var cr = texto(comp, v._credito, { x: comp.width - 34, y: comp.height - (comp.height > comp.width ? 70 : 34),
        tam: comp.height > comp.width ? 30 : 24, just: "dir", fonte: D.tema.fonte_corpo, cor: "#FFFFFF", sombra: true });
      P(cr, "Opacity").setValue(80);
    }
    return true;
  }
  var lista = v._fotos || [];
  if (!lista.length) { fundo(comp); return false; }
  var n = Math.max(1, Math.min(lista.length, Math.ceil(dur / 4.5)));
  var passo = dur / n;
  for (var i = 0; i < n; i++) foto(comp, lista[i % lista.length], i * passo, passo + 0.05, D._mov++);
  return true;
}

// ---------- cenas ----------
var CENAS = {};

CENAS.gancho = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  fotos(comp, v, dur);
  escurecer(comp, 45, true);
  var linhas = (v.texto || "").split("|");
  var tam = vert ? 150 : 150, y0 = H * (vert ? 0.42 : 0.5) - (linhas.length - 1) * tam * 0.55;
  for (var i = 0; i < linhas.length; i++) {
    var l = texto(comp, linhas[i], { x: W / 2, y: y0 + i * tam * 1.1, tam: tam, caixaAlta: T.caixa_alta,
      cor: i === linhas.length - 1 ? T.destaque : T.texto, max: W * 0.86 });
    entra(l, 0.1 + i * 0.28, "pop", 0.45);
  }
  barraX(comp, W / 2, y0 + linhas.length * tam * 1.1 - tam * 0.35, W * 0.18, 10, T.destaque2, 0.4 + linhas.length * 0.28, 0.5);
};

CENAS.imagem = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  fotos(comp, v, dur);
  if (v.rotulo) {
    escurecer(comp, 12, true);
    var x = vert ? W * 0.08 : W * 0.06, y = vert ? H * 0.62 : H * 0.78;
    var b = barraX(comp, x, y - 60, 120, 12, T.destaque, 0.25, 0.4, true);
    var l = texto(comp, v.rotulo, { x: x, y: y, tam: vert ? 110 : 96, just: "esq", caixaAlta: T.caixa_alta, max: W * 0.85 });
    entra(l, 0.3, "esq", 0.5);
    if (v.sub) {
      var s = texto(comp, v.sub, { x: x, y: y + (vert ? 95 : 82), tam: vert ? 50 : 44, just: "esq", fonte: T.fonte_corpo,
        cor: T.texto2, max: W * 0.85 });
      entra(s, 0.5, "esq", 0.5);
    }
  }
};

CENAS.numero = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  if (!fotos(comp, v, dur)) {} else escurecer(comp, 62, false);
  var l = texto(comp, String(v.valor), { x: W / 2, y: H * 0.45, tam: vert ? 300 : 280, cor: T.destaque, max: W * 0.9 });
  var pre = (v.prefixo || "").replace(/"/g, '\\"'), suf = (v.sufixo || "").replace(/"/g, '\\"');
  var dec = v.decimais || 0;
  l.property("Text").property("Source Text").expression =
    "var v=linear(time,0.15,1.3,0," + Number(v.valor) + "); var s=v.toFixed(" + dec + ").split('.');" +
    "s[0]=s[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.'); \"" + pre + "\"+s.join(',')+\"" + suf + "\"";
  entra(l, 0.05, "pop", 0.5);
  if (v.rotulo) {
    var r = texto(comp, v.rotulo, { x: W / 2, y: H * 0.45 + (vert ? 230 : 200), tam: vert ? 70 : 64, fonte: T.fonte_corpo,
      max: W * 0.86, caixa: null });
    entra(r, 0.6, "sobe", 0.5);
  }
};

CENAS.lista = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  if (fotos(comp, v, dur)) escurecer(comp, 40, true);
  var x = vert ? W * 0.08 : W * 0.06;
  var nl = texto(comp, "#" + v.n, { x: x, y: vert ? H * 0.5 : H * 0.6, tam: vert ? 260 : 240, just: "esq", cor: T.destaque,
    sombra: true });
  entra(nl, 0.05, "pop", 0.45);
  var t = texto(comp, v.texto, { x: x, y: vert ? H * 0.62 : H * 0.8, tam: vert ? 96 : 92, just: "esq", caixaAlta: T.caixa_alta,
    max: W * 0.86 });
  entra(t, 0.3, "esq", 0.5);
  if (v.sub) {
    var s = texto(comp, v.sub, { x: x, y: (vert ? H * 0.62 : H * 0.8) + (vert ? 90 : 78), tam: vert ? 48 : 44,
      just: "esq", fonte: T.fonte_corpo, cor: T.texto2, max: W * 0.86 });
    entra(s, 0.5, "esq", 0.5);
  }
};

CENAS.fato = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  if (fotos(comp, v, dur)) escurecer(comp, 72, false); else {}
  var q = texto(comp, "“", { x: W / 2, y: H * (vert ? 0.3 : 0.24), tam: 260, cor: T.destaque, fonte: T.fonte_titulo, sombra: false });
  entra(q, 0, "pop", 0.4);
  var t = texto(comp, v.texto, { x: W / 2, y: H * 0.5, tam: vert ? 72 : 66, fonte: T.fonte_corpo,
    caixa: [W * (vert ? 0.84 : 0.72), H * 0.5], entre: (vert ? 72 : 66) * 1.25 });
  entra(t, 0.2, "sobe", 0.55);
  if (v.fonte) {
    var f = texto(comp, "Fonte: " + v.fonte, { x: W / 2, y: H * (vert ? 0.76 : 0.86), tam: vert ? 40 : 34, fonte: T.fonte_corpo,
      cor: T.texto2 });
    entra(f, 0.6, "sobe", 0.4);
  }
};

CENAS.comparar = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  fundo(comp);
  var lados = [v.a, v.b];
  for (var i = 0; i < 2; i++) {
    var cx = vert ? W / 2 : W * (0.27 + i * 0.46), cy = vert ? H * (0.3 + i * 0.4) : H * 0.5;
    var cx0 = vert ? W * 0.1 : W * (0.06 + i * 0.5);
    var painel = comp.layers.addSolid(cor(i ? T.destaque2 : T.destaque), "painel", Math.round(vert ? W * 0.84 : W * 0.42),
      Math.round(vert ? H * 0.3 : H * 0.62), 1);
    P(painel, "Position").setValue([cx, cy]); P(painel, "Opacity").setValue(16);
    escala(painel, 0.05 + i * 0.25, 0.4);  // só escala: "entra" forçaria a opacidade a 100%
    var r = texto(comp, lados[i].rotulo, { x: cx, y: cy - (vert ? 150 : 170), tam: vert ? 80 : 76, caixaAlta: T.caixa_alta,
      cor: i ? T.destaque2 : T.destaque, max: (vert ? W * 0.8 : W * 0.38) });
    entra(r, 0.15 + i * 0.25, "sobe", 0.45);
    var val = texto(comp, lados[i].valor, { x: cx, y: cy + (vert ? 10 : 0), tam: vert ? 120 : 120, max: (vert ? W * 0.78 : W * 0.38) });
    entra(val, 0.3 + i * 0.25, "pop", 0.45);
    if (lados[i].sub) {
      var s = texto(comp, lados[i].sub, { x: cx, y: cy + (vert ? 120 : 130), tam: 44, fonte: T.fonte_corpo, cor: T.texto2,
        max: (vert ? W * 0.78 : W * 0.38) });
      entra(s, 0.45 + i * 0.25, "sobe", 0.4);
    }
  }
  var vs = texto(comp, "VS", { x: W / 2, y: vert ? H * 0.5 : H * 0.5, tam: 110, cor: T.texto });
  entra(vs, 0.6, "pop", 0.4);
};

CENAS.barras = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  fundo(comp);
  var tt = texto(comp, v.titulo || "", { x: W / 2, y: H * (vert ? 0.2 : 0.14), tam: vert ? 80 : 72, caixaAlta: T.caixa_alta,
    max: W * 0.9 });
  entra(tt, 0, "sobe", 0.4);
  var itens = v.itens, mx = 0;
  for (var i = 0; i < itens.length; i++) mx = Math.max(mx, Number(itens[i][1]));
  var x0 = vert ? W * 0.08 : W * 0.24, wmax = vert ? W * 0.62 : W * 0.56;
  var topo = H * (vert ? 0.3 : 0.27), passo = Math.min(H * (vert ? 0.11 : 0.13), (H * (vert ? 0.55 : 0.65)) / itens.length);
  for (var i = 0; i < itens.length; i++) {
    var y = topo + i * passo + passo / 2;
    var rot = texto(comp, String(itens[i][0]), { x: vert ? x0 : x0 - 30, y: vert ? y - passo * 0.32 : y, tam: vert ? 46 : 46,
      just: vert ? "esq" : "dir", fonte: T.fonte_corpo, sombra: false, max: vert ? W * 0.8 : W * 0.2 });
    entra(rot, 0.2 + i * 0.15, "sobe", 0.35);
    var wb = Math.max(8, wmax * Number(itens[i][1]) / (mx || 1));
    var by = vert ? y + passo * 0.12 : y;
    barraX(comp, x0, by, wb, passo * (vert ? 0.34 : 0.55), i === v.destaque ? T.destaque2 : T.destaque, 0.3 + i * 0.15, 0.7, true);
    var val = texto(comp, String(itens[i][2] || itens[i][1]), { x: x0 + wb + 24, y: by, tam: vert ? 50 : 50, just: "esq",
      sombra: false });
    entra(val, 0.8 + i * 0.15, "esq", 0.35);
  }
  if (v.fonte) {
    var f = texto(comp, "Fonte: " + v.fonte, { x: W / 2, y: H * 0.94, tam: 30, fonte: T.fonte_corpo, cor: T.texto2, sombra: false });
  }
};

CENAS.titulo = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  if (fotos(comp, v, dur)) escurecer(comp, 66, false); else fundo(comp);
  var faixa = barraX(comp, W / 2, H * 0.5, W * 1.1, vert ? 360 : 300, T.destaque, 0, 0.45, false);
  P(faixa, "Opacity").setValue(92);
  if (v.antes) {
    var a = texto(comp, v.antes, { x: W / 2, y: H * 0.5 - (vert ? 110 : 95), tam: vert ? 50 : 44, fonte: T.fonte_corpo,
      cor: T.fundo1, sombra: false, track: 200 });
    entra(a, 0.3, "sobe", 0.4);
  }
  var t = texto(comp, v.texto, { x: W / 2, y: H * 0.5 + (v.antes ? 25 : 0), tam: vert ? 130 : 130, caixaAlta: T.caixa_alta,
    cor: T.fundo1, sombra: false, max: W * 0.88 });
  entra(t, 0.35, "pop", 0.45);
};

// tela final (12 s): espaço livre para os elementos de "próximo vídeo" e "inscrever-se" do YouTube Studio
CENAS.telafinal = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height;
  fundo(comp);
  var t = texto(comp, v.texto || "Assista também", { x: W / 2, y: H * 0.13, tam: 84, caixaAlta: T.caixa_alta });
  entra(t, 0.1, "sobe", 0.5);
  // moldura do vídeo sugerido (esquerda) e do botão do canal (direita), nas posições padrão do Studio
  var molduras = [[W * 0.33, H * 0.55, W * 0.42, W * 0.42 * 9 / 16], [W * 0.74, H * 0.55, H * 0.3, H * 0.3]];
  for (var i = 0; i < 2; i++) {
    var m = molduras[i];
    var b = comp.layers.addSolid(cor(i ? T.destaque2 : T.destaque), "moldura", Math.round(m[2] + 16), Math.round(m[3] + 16), 1);
    P(b, "Position").setValue([m[0], m[1]]); P(b, "Opacity").setValue(85);
    entra(b, 0.2 + i * 0.2, "zoom", 0.45);
    var dentro = comp.layers.addSolid(cor(T.fundo1), "vazio", Math.round(m[2]), Math.round(m[3]), 1);
    P(dentro, "Position").setValue([m[0], m[1]]);
    entra(dentro, 0.2 + i * 0.2, "zoom", 0.45);
  }
  if (v.sub) {
    var s = texto(comp, v.sub, { x: W / 2, y: H * 0.88, tam: 44, fonte: T.fonte_corpo, cor: T.texto2 });
    entra(s, 0.6, "sobe", 0.4);
  }
};

CENAS.cta = function (comp, v, dur) {
  var T = D.tema, W = comp.width, H = comp.height, vert = H > W;
  if (fotos(comp, v, dur)) escurecer(comp, 70, false); else fundo(comp);
  var t = texto(comp, v.texto || "", { x: W / 2, y: H * 0.42, tam: vert ? 96 : 88, caixaAlta: T.caixa_alta, max: W * 0.86 });
  entra(t, 0.1, "sobe", 0.5);
  if (v.sub) {
    var s = texto(comp, v.sub, { x: W / 2, y: H * 0.42 + (vert ? 120 : 105), tam: vert ? 56 : 50, fonte: T.fonte_corpo,
      cor: T.destaque, max: W * 0.86 });
    entra(s, 0.4, "sobe", 0.5);
  }
};

// ---------- montagem ----------
function montar(D) {
  D._imgs = {}; D._mov = 0;
  var W = D.W, H = D.H, fps = D.fps, total = D.total;
  var main = app.project.items.addComp("Main", W, H, 1, total, fps);
  var base = main.layers.addSolid(cor(D.tema.fundo1), "base", W, H, 1);
  for (var i = 0; i < D.cenas.length; i++) {
    var c = D.cenas[i];
    var dur = c.fim - c.ini;
    var sub = app.project.items.addComp("Cena " + (i + 1) + " " + c.visual.tipo, W, H, 1, dur + 0.5, fps);
    (CENAS[c.visual.tipo] || CENAS.imagem)(sub, c.visual, dur);
    var l = main.layers.add(sub);
    l.startTime = c.ini; l.inPoint = c.ini; l.outPoint = c.fim;
    // "punch-in" na troca de cena
    if (i > 0) {
      var sc = P(l, "Scale");
      sc.setValueAtTime(c.ini, [107, 107]); sc.setValueAtTime(c.ini + 0.3, [100, 100]); suave3(sc);
    }
  }
  // acabamento: vinheta + grão leve
  var acab = main.layers.addSolid([1, 1, 1], "acabamento", W, H, 1);
  acab.adjustmentLayer = true;
  var vg = fx(acab, "ec.stylize.ccvignette"); vg.property("Amount").setValue(D.tema.vinheta || 45);
  // legendas palavra a palavra (Shorts)
  if (D.legendas) {
    for (var j = 0; j < D.legendas.length; j++) {
      var g = D.legendas[j];
      var lg = texto(main, g.t, { x: W / 2, y: H * D.tema.legenda_y, tam: D.tema.legenda_tam, cor: g.d ? D.tema.destaque : "#FFFFFF",
        caixaAlta: true, contorno: "#000000", contornoL: 10, max: W * 0.9, sombra: false });
      lg.inPoint = g.i; lg.outPoint = g.f;
      var s = P(lg, "Scale"), s0 = s.value;
      s.setValueAtTime(g.i, [s0[0] * 0.82, s0[1] * 0.82]); s.setValueAtTime(g.i + 0.09, s0); suave3(s);
    }
  }
  // barra de progresso (longos)
  if (D.progresso) {
    var pb = main.layers.addSolid(cor(D.tema.destaque), "progresso", W, 7, 1);
    P(pb, "Anchor Point").setValue([0, 3.5]); P(pb, "Position").setValue([0, H - 3.5]);
    P(pb, "Scale").expression = "[time/thisComp.duration*100, 100]";
    P(pb, "Opacity").setValue(85);
  }
  // marca do canal
  if (D.marca) {
    var mk = texto(main, D.marca, { x: W - 40, y: 52, tam: 34, just: "dir", fonte: D.tema.fonte_titulo, cor: D.tema.texto,
      sombra: false });
    P(mk, "Opacity").setValue(70);
  }
  var au = app.project.importFile(new ImportOptions(new File(D.audio)));
  main.layers.add(au);

  // miniatura
  var M = D.miniatura, TW = 1280, TH = 720;
  var th = app.project.items.addComp("Thumb", TW, TH, 1, 2, fps);
  if (M.foto) foto(th, M.foto, 0, 2, 0); else fundo(th);
  var hs = fx(th.layers.addSolid([1, 1, 1], "pop", TW, TH, 1), "ADBE Brightness & Contrast 2");
  th.layer(1).adjustmentLayer = true; hs.property(1).setValue(M.brilho || 12); hs.property(2).setValue(28);
  var esc = th.layers.addSolid([0, 0, 0], "lado", TW, TH, 1);
  var lw = fx(esc, "ADBE Linear Wipe");
  lw.property("Transition Completion").setValue(45); lw.property("Wipe Angle").setValue(90); lw.property("Feather").setValue(500);
  P(esc, "Opacity").setValue(85);
  var lin = M.texto.split("|"), tm = M.tam || 150;
  for (var k = 0; k < lin.length; k++) {
    texto(th, lin[k], { x: 60, y: TH * 0.5 - (lin.length - 1) * tm * 0.55 + k * tm * 1.08, tam: tm, just: "esq", caixaAlta: true,
      cor: k === lin.length - 1 ? D.tema.destaque : "#FFFFFF", contorno: "#000000", contornoL: 12, max: TW * 0.62,
      sombraReal: true, sombraOp: 220, sombraD: 10, sombraS: 25 });
  }
  if (M.selo) {
    var sl = th.layers.addSolid(cor(D.tema.destaque2), "selo", 420, 84, 1);
    P(sl, "Position").setValue([60 + 210, 70]); P(sl, "Rotation").setValue(-3);
    var st = texto(th, M.selo, { x: 60 + 210, y: 72, tam: 54, cor: "#FFFFFF", caixaAlta: true, max: 390, sombra: false });
    P(st, "Rotation").setValue(-3);
  }
  var vgt = th.layers.addSolid([1, 1, 1], "vin", TW, TH, 1); vgt.adjustmentLayer = true;
  fx(vgt, "ec.stylize.ccvignette").property("Amount").setValue(55);

  app.project.save(new File(D.projeto));
  writeLn("OK " + D.cenas.length + " cenas, " + total.toFixed(1) + "s");
}
