# ♟ Xadrez contra o Computador

Jogo de xadrez em Python para jogar contra o computador, com quatro níveis de dificuldade (Fácil, Médio, Difícil e Impossível), modo treinamento e problemas táticos. Funciona de duas formas: **com o mouse** (janela gráfica) ou **pelo terminal**.

## Arquivos

| Arquivo | O que é |
|---|---|
| `xadrez_gui.py` | Versão com interface gráfica (mouse) |
| `xadrez.py` | Versão de terminal, e também o motor usado pela versão gráfica |

> Mantenha os dois arquivos **na mesma pasta**. A versão gráfica depende do `xadrez.py`.

## Requisitos

- Python 3.8 ou superior
- Biblioteca [python-chess](https://pypi.org/project/chess/)
- Tkinter (para a versão com mouse)
- *(Opcional, mas necessário para o nível Impossível)* [Stockfish](https://stockfishchess.org/)

## Instalação

```bash
pip install chess
```

O Tkinter já vem com o Python no Windows e no macOS. No Linux, instale com:

```bash
sudo apt install python3-tk
```

## Como executar

**Com o mouse:**

```bash
python xadrez_gui.py
```

**No terminal:**

```bash
python xadrez.py
```

Opções disponíveis:

| Opção | Efeito |
|---|---|
| `--stockfish "caminho"` | Indica onde está o executável do Stockfish |
| `--ascii` | (só no terminal) Mostra as peças como letras em vez de símbolos |

## Níveis de dificuldade

| Nível | Como o computador joga |
|---|---|
| **Fácil** | Joga aleatoriamente quase metade das vezes. Erra bastante. |
| **Médio** | Enxerga poucos lances à frente e às vezes erra. |
| **Difícil** | Busca profunda (até 6 segundos por lance). Um desafio para a maioria dos jogadores. |
| **Impossível** | Usa o **Stockfish**, o motor de xadrez mais forte do mundo, muito acima de qualquer humano. |

### Sobre o nível Impossível

O nível Impossível só é realmente impossível com o Stockfish instalado. Sem ele, o jogo continua funcionando, mas esse nível usa o motor interno no máximo de força (forte, porém derrotável), e o programa avisa disso na tela. Em Python puro não dá para criar um bot invencível sem um motor como o Stockfish.

#### Instalando o Stockfish

- **Windows:** baixe em <https://stockfishchess.org/download/>, extraia e coloque a pasta (ou o `.exe`) ao lado dos arquivos do jogo. Ele é encontrado automaticamente. Também funciona com `--stockfish "C:/caminho/stockfish.exe"`.
- **Linux:** `sudo apt install stockfish`
- **macOS:** `brew install stockfish`

O programa procura o Stockfish, nesta ordem: no argumento `--stockfish`, na variável de ambiente `STOCKFISH_PATH`, no PATH do sistema, em pastas comuns de instalação e na pasta do jogo.

## Versão com mouse (`xadrez_gui.py`)

- **Mover uma peça:** clique nela e depois na casa de destino, ou arraste-a até lá.
- Os lances possíveis aparecem como **pontos** (casas vazias) e **anéis** (capturas).
- **Roque:** mova o rei duas casas em direção à torre.
- **Promoção do peão:** abre uma janelinha para escolher dama, torre, bispo ou cavalo.
- O último lance fica destacado em amarelo e o rei em xeque fica vermelho.

Painel lateral:

- **Nível** e **Sua cor** (brancas, pretas ou sorteio), válidos a partir do próximo *Novo jogo*.
- **Modo treinamento** e **Peças em letras** (útil se os símbolos das peças não aparecerem direito).
- **Novo jogo**, **Desfazer**, **Dica**, **Virar** (inverte o tabuleiro), **Desistir** e **Salvar PGN**.
- Barra de avaliação e registro de lances e comentários.

## Versão de terminal (`xadrez.py`)

O menu principal oferece: jogar contra o computador, treinamento, problemas táticos e sair.

### Como digitar os lances

Há duas formas, e as duas funcionam no mesmo jogo.

**Coordenadas** (a mais fácil): casa de origem + casa de destino.

```
e2e4     peão de e2 para e4
g1f3     cavalo de g1 para f3
e7e8q    peão chega à última fileira e vira dama
```

**Notação algébrica**: letra da peça (em inglês) + casa de destino.

| Peça | Letra | Exemplo |
|---|---|---|
| Cavalo | N | `Nf3` |
| Bispo | B | `Bc4` |
| Torre | R | `Ra4` |
| Dama | Q | `Qh5` |
| Rei | K | `Ke2` |
| Peão | (nenhuma) | `e4` |

- **Captura:** `Nxe5`, `exd5`
- **Roque pequeno:** `O-O` (ou `e1g1` / `e8g8`)
- **Roque grande:** `O-O-O` (ou `e1c1` / `e8c8`)
- **Promoção:** `e8=Q` ou `e7e8q` (sem a letra, vira dama)
- **Duas peças iguais para a mesma casa:** indique a de origem, como em `Rae1`, `Nbd2` ou `a1e1`.

### Comandos

| Comando | O que faz |
|---|---|
| `ajuda` | Mostra a ajuda |
| `lances` | Lista todos os seus lances legais |
| `lances e2` | Lista os lances legais da peça em e2 |
| `salvar` | Salva a partida em PGN |
| `desistir` | Abandona a partida |

Disponíveis só no **modo treinamento**:

| Comando | O que faz |
|---|---|
| `dica` | Diz qual peça mover |
| `solucao` | Mostra o melhor lance |
| `avaliar` | Mostra quem está melhor (em peões) |
| `desfazer` | Desfaz seu último lance e a resposta do computador |

## Modo treinamento

Depois de cada lance seu, o treinador compara com o melhor lance possível e classifica:

- ✔ **Excelente / Bom lance**
- **Imprecisão**
- **Erro**
- **Erro grave**

Quando você erra, ele mostra qual seria o melhor lance. Além disso, há dica, desfazer e avaliação da posição.

## Problemas táticos (só no terminal)

No menu do `xadrez.py`, a opção 3 traz problemas de **mate em 1** e **mate em 2** (corredor, mate do pastor, mate sufocado e escada de torres). Os comandos `dica`, `pular` e `sair` funcionam durante os problemas.

## Regras implementadas

Todas as regras do xadrez, graças ao python-chess: roque, en passant, promoção, xeque, xeque-mate, afogamento, material insuficiente, repetição de posição e regra dos 75 lances.

## Salvando partidas

As partidas são salvas no formato **PGN**, que pode ser aberto em qualquer programa de xadrez (Lichess, Chess.com, Arena, etc.). No terminal, o arquivo é salvo na pasta atual ao final da partida. Na versão gráfica, use o botão **Salvar PGN**.

## Problemas comuns

| Problema | Solução |
|---|---|
| `Falta a biblioteca python-chess` | Rode `pip install chess` |
| `No module named tkinter` | No Linux: `sudo apt install python3-tk` |
| `Coloque o xadrez_gui.py na mesma pasta do xadrez.py` | Mova os dois arquivos para a mesma pasta |
| Peças aparecem como quadrados ou emojis | Marque **Peças em letras** (gráfica) ou use `--ascii` (terminal) |
| O nível Impossível está fácil demais de vencer | O Stockfish não foi encontrado. Instale-o ou use `--stockfish "caminho"` |
| `Lance inválido` ao digitar `Re1` | Há duas peças que podem ir à mesma casa. Use `Rae1`, `Rfe1` ou coordenadas |

## Créditos

- [python-chess](https://python-chess.readthedocs.io/): regras, lances legais e comunicação com o Stockfish
- [Stockfish](https://stockfishchess.org/): motor do nível Impossível e do treinador (quando instalado)
- As tabelas de valor das peças do motor interno seguem a *Simplified Evaluation Function*