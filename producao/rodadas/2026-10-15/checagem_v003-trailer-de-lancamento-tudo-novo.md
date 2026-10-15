# Checagem v003-trailer-de-lancamento-tudo-novo (2026-10-15)

Fontes: descrição oficial e vídeo do Launch Trailer (acervo `rz1B4B2yBZY`, quadros extraídos com ffmpeg), descrições do T1/T2 e da capa no acervo, fatos já checados em `checagem_v002-trailer-1-x-trailer-2.md`, imprensa para a pré-venda (Consequence, GamesRadar, Vice).

| # | Afirmação | Veredito | Fonte / nota |
|---|---|---|---|
| 1 | Letreiro "Brian's Marina" | OK | Quadros aos 4,5 s e 5,5 s: "BRIAN'S MARINA" no telhado do galpão + "RENT A RACK 786-555-0109". Leitura completa, não só "...N'S MARINA" |
| 2 | Ligar Brian's Marina a Brian Heder = leitura | OK | Já dito como leitura |
| 3 | 04/12/2023 a 15/10/2026 = 1.046 dias | OK | Calculado: 1.046. Faltam 35 até 19/11/2026 |
| 4 | Descrição repete a sinopse do T2 palavra por palavra | OK | Comparado texto a texto: "Vice City, USA. Jason and Lucia have always known... forced to rely on each other more than ever if they want to make it out alive" idêntico nos dois |
| 5 | Justice compôs a trilha original | AJUSTADO | Descrição: "electronic duo Justice, composers of the original score from GTA VI". Fala agora diz "segundo a descrição" |
| 6 | Single "Flower in a Hurricane" feat. Tame Impala, SZA, King Gizzard; The Album em pré-save e vinil/CD | OK | Descrição oficial |
| 7 | Pré-venda desde 25/06/2026, "uma semana depois da capa" | OK | Rockstar (capa, 18/06: "pre-orders will officially begin on June 25") + imprensa confirma que abriu em 25/06. 18 a 25/06 = 7 dias |
| 8 | Trailer de 90 s; T1 90 s; T2 167 s | OK | `info.json` duration 90; T1 90; T2 167. "Exatamente o mesmo" suavizado para "o mesmo tempo" (algumas fontes dão 1:31 ao T1) |
| 9 | Tornozeleira aos 0:51, luz vermelha, pés descalços na ducha | AJUSTADO | Quadro 51,2 s confirma pés e luz vermelha. Que seja tornozeleira é interpretação: "É uma" virou "Parece uma" (cena e rótulo). Leitura "da Lucia" já estava dita como leitura, com "pode ser o Jason, pode ser outro". Mantido |
| 10 | Letreiros: "Plays best on PS5" (0:00-0:02); "November 19, 2026 / Pre-order now", ESRB M, "Captured on PS5" | OK | Quadros 0,5/1,5 s e 81/84 s |
| 11 | "Captured entirely in-game from a PlayStation 5"; sem proporção (T2 dizia partes iguais) | OK | Descrições |
| 12 | "O último trailer antes do jogo chegar" | CORRIGIDO | Previsão sem fonte. Trocado por "fechando com a data de lançamento" |
| 13 | Jason trabalhando na marina / polindo o casco | AJUSTADO | Quadro 6,5 s só mostra mão; 9,5 s mostra duas pessoas polindo um iate. Rockstar não identifica ninguém. Gancho: "parece fazer"; descrição: "parece trabalhar"; "o que parece ser o Jason" no celular (11,5 s); trecho do site oficial marcado como leitura |
| 14 | "Três caras de óculos" no lowrider | CORRIGIDO | Quadro 18,5 s mostra dois bem visíveis. Virou "caras de óculos" |
| 15 | Cofre com "dinheiro voando" | CORRIGIDO | Quadro 34,5 s mostra papel/estilhaços voando; não dá pra afirmar dinheiro. Virou "papel voando" |
| 16 | "Até hoje nenhum trailer tinha mostrado golpe nenhum" | CORTADO | Sem fonte e há o Extended Look (27/08/2026). Mantida só a leitura "o cofre pode ser o golpe fácil" |
| 17 | Equipe tática no mangue com visão noturna e fuzil | OK | Quadros 27,2 e 28,2 s |
| 18 | Camiseta "U.S. Army" | OK (leitura) | Quadro 40,5 s. Ligação com a bio marcada como "leitura minha" |
| 19 | Casal na ducha "tudo indica que são os dois" | AJUSTADO | Virou "pra mim, são os dois, mas a Rockstar não diz" |
| 20 | Heliponto, helicóptero no prédio, mulher de boné com carro em chamas, picape no aeroporto, biplano etc. | OK (visual) | Quadros 38,5, 52,5, 68,5, 72,8 conferidos; biplano, moto, atirador e viatura não reconferidos quadro a quadro (vêm da curadoria do acervo) |
| 21 | "30 de 36 cenas inéditas" | OK (leitura) | Contagem do canal, dita como "pelas minhas contas" |
| 22 | Comparações T1/T2 (rosa/teia, flamingos/iguana, helicóptero, Lucia presa/portão) | OK com ressalva | Já dadas como comparação/leitura; vêm de quadros dos trailers do acervo e da v002 |
| 23 | Datas T1 "2025" e T2 "26/05/2026" caíram; letreiro final 19/11/2026 | OK | v002 + quadro 81 s |
| 24 | Tom Petty / Pointer Sisters | OK | Descrições do T1 e T2 |

Afirmações checadas: 24 (itens agrupados; cerca de 60 fatos individuais). Corrigidas/cortadas/ajustadas: 11 (corrigidas 3, cortada 1, ajustes de precisão 7). 14 edições no JSON, nenhuma cena removida.

## Regras
- Cenas com clipe oficial: 27 de 72 = 37,5% (limite 40%). OK.
- Clipe violento nos 7 primeiros segundos: nenhum (cena 1 é o trecho aos 6,0 s com mão polindo casco, sem `violento`).
- Fala: cerca de 1.640 palavras (cerca de 10 a 11 min). OK.
- Miniatura: quadro oficial (0:40,5) do Launch Trailer, "TUDO|NOVO" + selo "LAUNCH TRAILER"; sem marca de terceiros. Atenção: "TUDO NOVO" exagera um pouco (30 de 36 momentos não aparecem nos trailers anteriores, mas 6 aparecem e o porto é "cartão-postal repetido"). O vídeo entrega o que promete, então segue, mas o título "analisei cena por cena" é o que protege.

## Riscos para o editor
- Cena de 0:51 (tornozeleira) e a da ducha: sempre com "parece"/"leitura", nunca como fato nem como identificação de personagem.
- Clipes de Jason (0:06, 0:09, 0:11) não têm identificação oficial; não pôr legenda "Jason" sem "parece".
- Não cortar a parte "segundo a descrição" da cena do Justice.
- Clipe da capa (`EiQEBYDox_k` aos 15 s) tem só 33 s de vídeo; confira que o trecho existe.
