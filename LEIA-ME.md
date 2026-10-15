# Agentes YouTube — Engenhoso + GTAzando

Piloto automático dos dois canais. Custo zero. **Nada vai ao ar sem o seu ✅.**

**Desde 14/10/2026 ("profissionalização")**: os dois canais fazem vídeo longo de 8–12 min sem rosto (carro-chefe)
e Shorts de funil, seguindo o sistema de roteiro do guia (`motor_pro/ROTEIRO.md`). Tudo grátis:
voz própria de cada canal (`motor_pro/voz.py`), cenas animadas e render no **EffectCraft**, miniatura no
**EffectCraft + PhotoCraft**, imagens livres do Wikimedia Commons/Openverse com crédito automático, trilha gerada.
O canal infantil (SuperKids) virou **Engenhoso** — "como as coisas funcionam por dentro" (pesquisa em
`canais/engenhoso/biblia.md`). O material infantil antigo está em `_arquivo_kids/`.

## Modo independente (desde 15/10/2026)
Todo dia, sem você: **06:30** a tarefa "YouTube — produção diária" do app Claude coordena 10 agentes
(radar de assuntos, curador de cenas oficiais, roteirista, checador, SEO, miniatura, editor…; lista e modelos na aba
**Agentes** do Estúdio e em `CLAUDE.md`). O Windows renderiza um vídeo por vez (`AgentesYouTube\Render`, a cada 10 min),
sobe e **agenda sozinho**: longo **19:00** e Short **20:00** em cada canal. **16:30** uma conferência confere os 4 horários.
Para barrar um vídeo: Estúdio → vídeo → **Vetar** (fica privado, nada é apagado).
Precisa: PC ligado (as rotinas acordam o PC e rodam na bateria) e o app Claude aberto às 06:30 (se estiver fechado,
a produção roda quando você abrir).
Cenas reais: trechos curtos de vídeos oficiais (Rockstar, Netflix, NASA…, lista em `acervo/fontes_oficiais.json`),
sem o áudio original, com narração por cima e crédito — nunca vazamento nem trailer inteiro.

## O app: Estúdio dos Canais
Atalho **"Estúdio dos Canais"** na Área de Trabalho e no Menu Iniciar (código em `app/`). Janela própria com:
visão geral (render ao vivo com % e previsão de término, o que espera sua aprovação, canais, agenda),
produção (cada vídeo do roteiro até o ar: roteiro cena a cena, imagens, quadros, descrição, histórico e botões
de conferir/renderizar/aprovar/refazer), métricas (views por dia e por vídeo) e atividade (log e rotinas).
Roda no Python + Edge já instalados (o Windows bloqueia .exe não assinado). Fechar a janela encerra o app.
Vídeos prontos ficam também em `Entregas/<canal>/<id>/` (vídeo, miniatura, `publicar.txt` com título/descrição/tags, legendas).

## O dia a dia (o que é com você)
1. **Aprovar vídeos** — dois cliques em `Abrir painel.cmd` (abre http://localhost:8787) ou pelo Telegram, se configurado.
   ✅ Publicar = o agente agenda no próximo horário bom. ❌ Refazer = o agente refaz na próxima rodada.
2. **GTA, a partir de 19/11** — gravar a lista da semana (`canais/gta6/lista_gravacao.md`) e jogar os clipes em
   `canais/gta6/entrada/`.

## O que roda sozinho
| Quando | O quê | Como |
|---|---|---|
| a cada 15 min | sobe vídeos prontos (privado), lê aprovações, agenda | Agendador do Windows → `AgentesYouTube\Fila` |
| todo dia 09:00 | puxa views/analytics e recalcula o nicho | Agendador do Windows → `AgentesYouTube\Metricas` |
| segunda 08:00 | **o cérebro**: mede, pesquisa o que viraliza, decide nicho, cria os vídeos da semana | Claude → tarefa agendada "Agente YouTube — rodada semanal" (precisa do app Claude aberto) |

## Como o nicho muda sozinho
`config.json → regras_nicho`: cada vídeo é medido contra a mediana do próprio canal. Um nicho de teste que fizer
**2x a mediana em 3 vídeos seguidos** vira o principal. Nada é julgado antes de 6 vídeos com 7+ dias.
Histórico das trocas em `dados/<canal>/nicho.json` e no painel.

## Pastas
- `episodios/<canal>/` — roteiros (JSON) de cada vídeo · `fila/<canal>/<id>/` — vídeo, miniatura e estado
- `motor_pro/` — **motor principal** dos dois canais (roteiro → voz → EffectCraft → MP4 + miniatura + descrição)
- `motor_gta/` — quadros/montagem dos clipes do PS5 · `motor_kids/` — antigo (Bubi), fora de uso
- `canais/<canal>/biblia.md` — regras de cada canal · `canais/<canal>/tema.json` — cores/fontes/trilha · `AGENTE.md` — rotina do cérebro
- `dados/` — métricas, pesquisas, log (`agente.log`) · `credenciais/` — acesso ao YouTube (não compartilhar)

## Pendências que só você resolve
- [x] **App OAuth publicado** (13/10) e canais reautorizados — o acesso não vence mais.
      Se um dia precisar refazer: `python autorizar.py engenhoso --novo` (idem `gta6`).
- [x] **Canais verificados por telefone** (13/10) — miniaturas personalizadas aplicadas.
- [x] **Auditoria da API pedida** (13/10/2026) — formulário enviado; resposta do Google por e-mail em dias/semanas.
      Respostas e provas usadas em `docs/auditoria/`. Até aprovar, vídeo que continuar privado depois do horário
      vai para "subir pelo Studio" no painel.
- [ ] **Telegram (opcional)**: @BotFather → /newbot → cole `TELEGRAM_TOKEN=...` no arquivo `.env` desta pasta →
      mande "oi" pro bot.

## Comandos úteis
```
python painel.py                     # painel de controle
python coletar.py                    # métricas agora
python publicar.py                   # roda a fila agora
python motor_pro/render.py episodios/<canal>/<id>.json --rapido   # confere imagens/miniatura
python motor_pro/render.py episodios/<canal>/<id>.json --fila     # render final + fila
python motor_gta/montar.py episodios/gta6/<id>.json --fila
python autorizar.py engenhoso|gta6        # reautorizar um canal
```
