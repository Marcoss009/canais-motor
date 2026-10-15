# Checagem s003-trailer-de-lancamento-3-coisas (gta6, 15/10/2026)

Método: quadros do video.mp4 do Launch Trailer (rz1B4B2yBZY) nos tempos dos clipes; Trailers 1 (QdBZY2fkU-0) e 2 (VQRLujxTm3c) varridos a 1 quadro/s em folhas de contato.

| # | Afirmação | Veredito | Fonte |
|---|---|---|---|
| 1 | Trailer de lançamento saiu hoje (15/10/2026) | OK | info.json (upload 20261015, Rockstar) |
| 2 | Cofre aos 0:34: duas mulheres, porta redonda, notas voando | OK (quadros 34-35 s) | Launch Trailer |
| 3 | Cofre inédito | OK: nada parecido nos T1/T2 | folhas T1/T2 |
| 4 | Moto sobre trilho elevado do trem, 0:48 | OK (48-50 s, salto entre prédios) | Launch Trailer |
| 5 | Moto/trilho inédito | OK: T1 tem motos de trilha em rua, T2 tem motos na rua/chopper; nenhuma em trilho de trem. A fala é específica ("no trilho do trem"), não "moto" | folhas |
| 6 | Biplano com alguém em pé na asa sobre a praia, 0:55 | OK (55-57 s, fumaça rosa) | Launch Trailer |
| 7 | Biplano inédito | OK: T2 só tem hidroavião no cais; T1 tem aérea da praia sem avião | folhas |
| 8 | Tornozeleira, ducha, luz vermelha, 0:51 | OK (luz vermelha nítida a 51,2 s; visível ~1,2 s) | Launch Trailer |
| 9 | Tornozeleira inédita | OK: T1/T2 têm cela/prisão/visita, sem tornozeleira | folhas |
| 10 | "De quem é? O trailer não mostra" | OK (só pernas) | Launch Trailer |
| 11 | Letreiro final 19 de novembro, pré-venda já | OK (80,7-86 s) | Launch Trailer |
| 12 | Faltam 35 dias | OK (15/10 a 19/11) | cálculo |
| 13 | "o mais estranho" | Opinião -> marcada "na minha opinião" | - |

Regras: clipe oficial em 3 de 8 cenas (37,5%, <=40%); gancho (0:40, casal no esportivo) não violento nos 7 s iniciais; fala ~110 palavras (~40 s, <=50 s); sem rumor/vazamento; título e miniatura (quadro 26,3 s, Lucia/Jason, já na curadoria) entregam o que prometem.

## Mudou
- Cena 5: "o mais estranho" -> "o mais estranho, na minha opinião".
- Cena 6: "Um segundo só" -> "Pouco mais de um segundo".
- `fontes`: acrescentada a conferência quadro a quadro.

## Riscos para o editor
- Tornozeleira: clipe em 51,0 s; o melhor quadro (luz vermelha) está em ~51,2; abaixo de 50,8 s só entra a moto. Ajustar `ini` para 50,9 se quiser mostrar só a tornozeleira (a cena 4 usa 48,0 e o clipe pode invadir 51 s se passar de 3 s; clipe do 55 s fica ok).
- Clipe de 48 s acaba na tornozeleira se >3 s; manter curto.
- Varredura de T1/T2 foi a 1 quadro/s: plano <1 s poderia escapar; risco baixo.
