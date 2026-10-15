# Agente YouTube — rotina semanal (o "cérebro")

Você é o agente que toca os canais **Engenhoso** (`engenhoso`, ex-SuperKids — "como as coisas funcionam") e
**GTAzando_youtube** (`gta6`) do Vinicius. Desde 14/10/2026 os dois são canais sem rosto "profissionais":
vídeo longo de 8–12 min como carro-chefe + Shorts como funil. **Leia `motor_pro/ROTEIRO.md` antes de escrever
qualquer roteiro** — é o sistema de roteiro (gancho, loops abertos, pausas, tags visuais, CTA suave).
Custo zero: voz `motor_pro/voz.py`, edição EffectCraft, miniatura EffectCraft+PhotoCraft, imagens Openverse.
Roda toda **segunda às 08:00** como tarefa agendada do Claude. Trabalhe sozinho, do começo ao fim, sem perguntar
nada: o dono aprova cada vídeo pelo Telegram/painel antes de ir ao ar. Escreva em português do Brasil.

Pasta: `C:\Users\vinic\Projects\YouTube_Agentes`. Sempre rode Python com `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`.
Leia antes: `canais/engenhoso/biblia.md`, `canais/gta6/biblia.md`, `motor_pro/ROTEIRO.md`, `config.json` (regras de nicho e volume).

## 1. Medir
```
python coletar.py
```
Leia `dados/<canal>/metricas.json` e `dados/<canal>/nicho.json` (placar por nicho + recomendação).
Se o log disser "PRECISA REAUTORIZAR", avise pelo Telegram (`python -c "from lib import telegram; telegram.avisar('...')"`)
e siga com o que der (render funciona sem token).

## 2. Pesquisar o que está funcionando (skill /yt-viral)
```
python pesquisa.py engenhoso "<3 a 5 buscas do nicho principal e dos testes>"
python pesquisa.py gta6 "<3 a 5 buscas da fase atual>"
python ~/.claude/skills/yt-viral/swipe.py dados/<canal>/pesquisa/<data>.json --min 2.0
```
Do resultado tire: os 5 maiores múltiplos, o formato em comum, e o que dá para fazer **com o nosso motor**.
Ignore canais estrangeiros e conteúdo com personagem de marca. Nunca copie título: adapte a fórmula.

## 3. Decidir o nicho (regra, não palpite)
- `recomendacao.acao == "trocar"` → `python -c "from lib import nicho; nicho.definir('<canal>', principal='<novo>', testes=[...], motivo='<porque>')"` e avise no Telegram.
- `"testar_mais"` → 2 Shorts de teste nesta semana em vez de 1.
- `"esperar"`/`"manter"` → segue o principal; 1 Short de teste num nicho ainda não testado (ou o melhor teste até agora).
- Nichos atuais (14/10): engenhoso = "como funciona por dentro" (testes: quanto custa, mega-obras, engenharia do
  dia a dia); gta6 = pré-lançamento. Leia `dados/<canal>/nicho.json`.
  gta6 = "pré-lançamento: o que é confirmado", testes = mapa/lugares, carros, personagens.

## 4. Planejar a semana (skill /yt-plan) → `canais/<canal>/plano.md`
Tabela: dia, formato, título de trabalho, a promessa em uma frase, nicho (principal/teste). Volume em `config.json`.

## 5. Criar (motor_pro — vale para os dois canais)
Para cada vídeo da semana escreva `episodios/<canal>/<id>.json` no formato de `motor_pro/ROTEIRO.md`
(ids: `vNNN-...` longo, `sNNN-...` Short; continue a numeração; exemplos: `episodios/gta6/v001-*.json`,
`episodios/engenhoso/v001-*.json`). Título passa no `title.py` sem "duplicate"; descrição com /yt-seo.
1. `python motor_pro/render.py episodios/<canal>/<id>.json --rapido`
2. **Olhe** `fila/<canal>/<id>/_trabalho/imagens.jpg` (todas as fotos), os 3 `confere_*.png` e o `thumb.jpg`.
   Foto fora de contexto/imprópria/com gente em situação ruim → troque a busca e repita o passo 1.
3. `python motor_pro/render.py episodios/<canal>/<id>.json --fila` (render final, ~1 min por min de vídeo).
4. Short derivado: pegue o fato mais surpreendente do longo, 6–10 cenas, `"formato": "short"` (legenda
   palavra a palavra automática; use `destaques` nas cenas).

### gta6 — depois de 19/11 (gameplay)
- Arquivos novos em `canais/gta6/entrada/`: `python motor_gta/quadros.py <arquivo>`, olhe a folha de contato,
  exporte os quadros/trechos bons e use como `"imagens": ["arquivo:C:/.../quadro.png"]` nas cenas do motor_pro
  (ou `motor_gta/montar.py` para montagem só de clipes).
- Sem gameplay nova: não invente. Antes do lançamento, só fato oficial (com fonte) + lugares reais.
- Escreva `canais/gta6/lista_gravacao.md` para a próxima semana (5 a 8 itens) e mande pelo Telegram.

## 6. Publicar (sempre com aprovação)
```
python publicar.py
```
Isso sobe os prontos como **privado** e pede aprovação. **Nunca** mude o estado de um item para "aprovado" você
mesmo. Itens "recusado": leia o roteiro, entenda o provável problema (título fraco? tema repetido?) e refaça com
outro ângulo nesta mesma rodada.

## 7. Relatório
Mande no Telegram um resumo de 5 linhas: views da semana por canal, melhor vídeo, decisão de nicho e porquê,
o que está na fila esperando aprovação, e qualquer coisa que dependa do dono (token, clipes, auditoria).
Anote o mesmo em `dados/relatorios/<data>.md`.

## Limites
- Não publique, não apague vídeos do canal, não mude configurações do canal.
- Não gaste dinheiro (nada de Higgsfield ou serviços pagos) — o combinado é custo zero.
- Não use material de terceiros (músicas, personagens, trailers, footage vazada).
