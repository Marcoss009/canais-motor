# Agentes de YouTube — memória do projeto (leia antes de qualquer tarefa)

Dono: Vinicius (pt-BR, trabalha + faculdade à noite; quer **piloto automático**, pouca manutenção).
Pasta: `C:\Users\vinic\Projects\YouTube_Agentes`. Rode Python sempre com `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.
Python: `C:\Users\vinic\AppData\Local\Programs\Python\Python312\python.exe`. ffmpeg: caminho em `config.json`.

## Canais
| chave | canal | ID | tema | voz (persona) |
|---|---|---|---|---|
| `gta6` | GTAzando_youtube | UCrP6_yBsVO9lMN6dOSbpWVA | GTA VI (lança 19/11/2026, PS5/Xbox Series) | Andrew Multilingual, timbre "trailer" |
| `engenhoso` | Engenhoso (ex-SuperKids) | UCYtkx4t6WOx15FTvzJLN3_A | como as coisas funcionam por dentro | Thalita, timbre "doc" |
Bíblias (regras de cada canal): `canais/<canal>/biblia.md`. Tema visual: `canais/<canal>/tema.json`.
Canal pessoal "Marcos Vinicius Almeida Ferreira": **nunca usar**.

## Ritmo (pedido do dono em 15/10/2026)
Por canal, **todo dia**: 1 vídeo longo (8–12 min) às **19:00** + 1 Short às **20:00**.
**Modo independente**: `config.json → aprovacao_automatica = true` — o vídeo é aprovado sozinho ao subir e entra
no horário. O dono pode vetar pelo app Estúdio até o horário. Ninguém espera o dono.

## A esteira (quem faz o quê)
Rodada diária = tarefa agendada do app Claude **"yt-producao-diaria" (06:30)**, que coordena os subagentes
(`C:\Users\vinic\.claude\agents\yt-*.md`). Arquivos da rodada: `producao/rodadas/AAAA-MM-DD/`.

| etapa | agente (modelo) | entrada → saída |
|---|---|---|
| 1 métricas + nicho | `yt-analista` (haiku) | `coletar.py` → `analise.md` |
| 2 assuntos quentes | `yt-radar` (sonnet) | web + YouTube + oficiais → `pauta.json` |
| 3 cenas oficiais | `yt-acervo` (sonnet, olha imagens) | pauta → `acervo/` + `cenas_<canal>.json` |
| 4 roteiro | `yt-roteirista` (opus) | pauta + cenas + bíblia → `episodios/<canal>/vNNN.json` e `sNNN.json` |
| 5 checagem | `yt-checador` (sonnet) | roteiro → roteiro corrigido + `checagem_<id>.md` |
| 6 título/descrição/tags | `yt-seo` (haiku) | roteiro → campos de SEO no próprio JSON |
| 7 miniatura | `yt-thumb` (sonnet, olha imagens) | roteiro + conferência → campo `miniatura` aprovado |
| 8 edição/conferência | `yt-editor` (sonnet, olha imagens) | `render.py --rapido`, corrige, cria o **pedido de render** |
| 9 render | `render_fila.py` (Windows, a cada 10 min) | pedido → vídeo na `fila/` com `slot` |
| 10 subir + agendar | `publicar.py` (Windows, a cada 15 min) | fila → YouTube (privado + publishAt no slot) |
| 11 conferência da tarde | `yt-publicador` (haiku), tarefa "yt-verificacao-tarde" (16:30) | confere se 19:00/20:00 estão agendados |
| semanal | `yt-horarios` (haiku), segunda | analytics → `dados/horarios.json` (recomendação) |
| de hora em hora | `vigia.py` (Windows `AgentesYouTube\Vigia`) | canal oficial publicou vídeo novo do tema (ex.: trailer) → baixa no acervo + `producao/alertas/<id>.json` |
| 12:00 | tarefa Claude "yt-plantao-noticia" | alerta do gta6 ainda não tratado → refaz o GTA do dia em cima da novidade |

Por que esses modelos: roteiro é o que mais pesa no resultado (gancho, ritmo, loops) → **opus**. Pesquisa,
checagem de fatos, escolher cena olhando imagem, miniatura e edição pedem julgamento + visão → **sonnet**.
Coletar números, SEO com regras fixas, horários e conferência de agenda são tarefas de regra → **haiku**.

## Contratos (arquivos)
- `producao/rodadas/<data>/pauta.json`:
  `{"gta6": [{"tema","angulo","por_que_agora","fontes":[url],"oficiais":[video_id],"nota":0-10}], "engenhoso": [...]}`
- `producao/rodadas/<data>/cenas_<canal>.json`: `[{"video":"<id>","ini":41.2,"o_que":"Lucia na praia"}]`
- Roteiro: formato em `motor_pro/ROTEIRO.md`. Cena oficial: `"visual": {"tipo":"imagem","clipes":[{"video":"VQRLujxTm3c","ini":40}],"rotulo":"...","sub":"..."}`
  (qualquer tipo aceita `clipes` no lugar de `imagens`). Miniatura com quadro oficial: `"miniatura":{"texto":"...","quadro":{"video":"<id>","t":41.2},"selo":"..."}`.
- Pedido de render: `producao/pedidos/<data>_<canal>_<formato>.json`
  `{"roteiro":"episodios/<canal>/<id>.json","slot":"AAAA-MM-DDT19:00:00-03:00","canal":"...","formato":"longo|short","por":"yt-editor"}`
- Estado de cada vídeo: `fila/<canal>/<id>/item.json` (pronto → enviado → aprovado → agendado → publicado).
- Log geral: `dados/agente.log`. Status de render ao vivo: `fila/<canal>/<id>/_trabalho/status.json`.

## Motor (tudo grátis, nada pago, nada com cadastro)
`motor_pro/render.py` = voz (`voz.py`: edge-tts + timbre ffmpeg) → trilha gerada (`trilha.py`) → imagens livres
(`imagens.py`: Wikimedia Commons CC0/PD/CC BY; Openverse bloqueia anônimo) → cenas oficiais (`acervo.py`) →
**EffectCraft** (`cenas.jsx`, render H.264) → miniatura EffectCraft + **PhotoCraft** → descrição com capítulos,
fontes e créditos → `fila/` + `Entregas/<canal>/<id>/` (vídeo, miniatura, publicar.txt, legendas).
Render: ~120–190 ms/quadro (≈ 50 min por longo de 9 min, ≈ 5 min por Short). **Um render por vez.** A conferência
(`--rapido`) roda em prioridade baixa e o render final em alta — mesmo assim evite `bench`/renders manuais durante
um render final (em 15/10 a disputa levou um longo de ~50 min para ~5 h).
Não use Drop Shadow / Fractal Noise / Noise em camada que fica o vídeo todo (custa 100+ ms/quadro).

## Cenas oficiais (regras que não se quebram)
- Só de canal oficial listado em `acervo/fontes_oficiais.json` (Rockstar, PlayStation, Netflix, Netflix Brasil,
  NASA, SpaceX, Boeing, Airbus…). Vídeo com restrição de idade não baixa (precisaria da conta do dono) → pule.
- Trecho ≤ 6 s, **sem áudio original**, sempre com narração nossa por cima (comentário/análise), crédito na tela e
  na descrição (automático). Máx. **45%** do vídeo com cena oficial (o motor recusa acima disso).
- Nunca: vazamento, gameplay de terceiros, trailer inteiro ou sequência longa, música do trailer.
- GTA: violência gráfica fora dos 7 primeiros segundos; só fato oficial (com fonte) ou comparação marcada como tal.

## Limites para todo agente
- Não apagar vídeos do canal, não mexer em configuração de canal, não gastar dinheiro.
- Não inventar fato. Número sempre com fonte; na dúvida "mais de/cerca de".
- Datas: hoje é a data do sistema; GTA VI sai em 19/11/2026.
- O dono lê tudo no app **Estúdio dos Canais** (atalho na Área de Trabalho; `app/`).

## Comandos úteis
```
python motor_pro/acervo.py listar gta6             # vídeos recentes dos canais oficiais
python motor_pro/acervo.py baixar gta6 <id>        # baixa + folha.jpg (quadros a cada 2 s com o tempo)
python motor_pro/render.py episodios/<c>/<id>.json --rapido   # conferência (voz, imagens, miniatura, 3 quadros)
python render_fila.py                              # força o operador de render agora
python publicar.py                                 # força a fila agora
python coletar.py                                  # métricas agora
python ~/.claude/skills/yt-package/title.py --title "..." --thumb "..."
```

## Histórico curto
- 13/10: canais criados, OAuth publicado, auditoria da API enviada. Shorts iniciais.
- 14/10: profissionalização (guia "canal sem rosto"): motor_pro, EffectCraft/PhotoCraft, kids → Engenhoso,
  app Estúdio. GTA v001 "GTA 6 é a Flórida?" foi ao ar sozinho 14/10 19:00 (agendamento pela API funciona).
- 15/10: cenas oficiais (acervo), esteira diária de subagentes, modo independente, 19:00 longo / 20:00 Short.
  Rockstar lançou o "GTA VI Launch Trailer" (rz1B4B2yBZY) às ~10h; o dono avisou → GTA do dia refeito em cima dele
  (v003 + s003); o "Trailer 1 x Trailer 2" (v002/s002) ficou de reserva em `producao/reserva/`. Daí nasceram vigia + plantão.
