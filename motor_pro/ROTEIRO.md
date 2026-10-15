# Sistema de roteiro (motor_pro)

Baseado no guia de 14/10/2026 ("canal sem rosto com Claude"): o que fazia os canais de exemplo crescerem não era
a ferramenta, era o **sistema de roteiro** + nicho que paga + constância. Aqui tudo é grátis:

| no guia (pago)             | aqui (grátis)                                                        |
|----------------------------|----------------------------------------------------------------------|
| Claude escreve o roteiro   | o agente semanal (AGENTE.md), seguindo as regras abaixo              |
| ElevenLabs (voz)           | `motor_pro/voz.py`: voz neural edge-tts + timbre próprio do canal    |
| CapCut / Canva (edição)    | **EffectCraft** (`effectcraft-cli`, roteiro → cenas animadas → MP4)  |
| Nano Banana (miniatura)    | **EffectCraft** desenha + **PhotoCraft** finaliza em JPG             |
| Pexels (imagens)           | Openverse (CC0 / domínio público / CC BY) com crédito automático     |
| TubeBuddy / VidIQ          | `pesquisa.py` + skills /yt-viral, /yt-package, /yt-seo               |
| música de banco            | `motor_pro/trilha.py` (trilha gerada, sem Content ID)                |

## As 7 regras do roteiro (todo vídeo longo)
1. **Gancho com quebra de padrão nos primeiros 30 s.** Primeira frase = uma imagem mental surpreendente ou um
   número absurdo. Nada de "neste vídeo eu vou". Ex.: "Se você pegar um avião pra Miami, você pousa dentro do
   mapa do GTA 6."
2. **Loop aberto cedo** (até 30 s): prometer algo que só aparece perto do fim ("uma das regiões não existe —
   fica até o fim"). Abrir um **segundo loop** no meio do vídeo. Fechar os dois.
3. **Entregar cedo**: o primeiro fato bom vem antes de 45 s. Quem promete e enrola perde o público.
4. **Escrever como a gente fala**, não como redação: frase curta, "você", pergunta retórica, "repara",
   "agora vem a parte boa". Número por extenso na fala ("trinta e seis"), em algarismo na tela.
5. **Marcadores de pausa**: `[pausa]` antes de revelação, `[pausa longa]` antes da maior revelação.
6. **Tag visual em toda cena** (`visual.tipo`) — trocar o que se vê a cada 4–8 s. Uma cena = uma ideia.
7. **CTA suave no fim**: uma pergunta pros comentários + "se quiser acompanhar...". Nunca "deixa o like".

Duração: longo **8 a 12 min** (anúncio no meio só a partir de 8 min ≈ 60–70 cenas). Short: 25–50 s, 6–10 cenas.

## Formato do arquivo `episodios/<canal>/<id>.json`
```json
{
  "id": "v002-...", "canal": "gta6|engenhoso", "formato": "longo|short", "nicho": "...",
  "titulo": "...", "titulos_alternativos": ["3 opções, a 1ª é a escolhida"],
  "miniatura": {"texto": "ATÉ 3|PALAVRAS", "imagem": "busca em inglês", "selo": "opcional", "tam": 150},
  "descricao": "2-3 parágrafos SEO (o motor junta capítulos, fontes e créditos das imagens)",
  "fontes": ["órgão/site oficial — o que foi usado"], "hashtags": ["#a", "#b"], "tags": ["..."],
  "cenas": [
    {"capitulo": "opcional: abre capítulo", "fala": "texto falado [pausa] ...",
     "destaques": ["palavras pra pintar na legenda do Short"],
     "visual": {"tipo": "...", "...": "..."}}
  ]
}
```
### Tipos de visual (`motor_pro/cenas.jsx`)
| tipo | campos | uso |
|---|---|---|
| `gancho` | `texto` (linhas separadas por `|`), `imagens` | primeira cena |
| `imagem` | `imagens` [buscas], `rotulo`, `sub` | o padrão: foto em movimento + legenda inferior |
| `numero` | `valor`, `prefixo`, `sufixo`, `decimais`, `rotulo`, `imagens`? | número que conta até o valor |
| `lista` | `n`, `texto`, `sub`, `imagens` | "#3 ..." em vídeos de lista |
| `fato` | `texto`, `fonte`, `imagens`? | citação/fato oficial com fonte na tela |
| `comparar` | `a` e `b`: {`rotulo`, `valor`, `sub`} | X vs Y |
| `barras` | `titulo`, `itens` [[rótulo, valor, texto]], `destaque` (índice), `fonte` | gráfico |
| `titulo` | `antes` (sobretítulo), `texto`, `imagens` | abertura de capítulo |
| `cta` | `texto`, `sub`, `imagens` | final |

Buscas de imagem: **em inglês**, 2–3 palavras concretas ("everglades airboat", não "pântano bonito").
Imagem própria: `"arquivo:C:/caminho/print.png"` (ex.: gameplay do PS5 depois de 19/11).

## Rodar e conferir (obrigatório antes da fila)
```
python motor_pro/render.py episodios/<canal>/<id>.json --rapido   # voz + imagens + miniatura + 3 quadros
```
Olhar `fila/<canal>/<id>/_trabalho/imagens.jpg` (folha de contato de TODAS as fotos), os 3 `confere_*.png` e
`thumb.jpg`. Foto fora de contexto ou imprópria → trocar a busca da cena e rodar de novo. Depois:
```
python motor_pro/render.py episodios/<canal>/<id>.json --fila      # render final (~1 min de render por min de vídeo)
```
Título passa no `python ~/.claude/skills/yt-package/title.py --title "..." --thumb "..."`.

## Detalhes do motor
- Longos ganham **12 s de tela final** automática ("Assista também" + 2 molduras vazias): no Studio, coloque ali
  o elemento "vídeo/playlist" (moldura da esquerda) e "inscrever-se" (direita). Conta na duração (meta ≥ 8:00).
- Custo de render ≈ 120–150 ms por quadro (≈ 30–40 min por vídeo de 8 min). Não use `Drop Shadow`, `Fractal
  Noise` ou `Noise` em camadas que ficam no vídeo inteiro — custam 100+ ms por quadro cada. A sombra do texto é
  uma cópia deslocada; a cor das fotos é aplicada uma vez no Python (`tratar()` em render.py).
- `effectcraft-cli bench <projeto> --comp Main --time <s>` mostra o custo de cada camada/efeito.
