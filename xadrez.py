#!/usr/bin/env python3
"""
XADREZ CONTRA O COMPUTADOR  (terminal)

Níveis: Fácil, Médio, Difícil e Impossível
Modos : Jogar  |  Treinamento (com treinador)  |  Problemas táticos (mates)

Requisitos:
    pip install chess

Nível IMPOSSÍVEL:
    Usa o Stockfish (o motor de xadrez mais forte do mundo, muito acima de
    qualquer humano). Instale-o e o programa o encontra sozinho:
      - Windows : baixe em https://stockfishchess.org/download/ e ponha o .exe
                  na mesma pasta deste arquivo (ou use --stockfish "caminho")
      - Linux   : sudo apt install stockfish
      - macOS   : brew install stockfish
    Sem o Stockfish o jogo funciona, mas o "impossível" vira apenas o
    motor interno no máximo de força (forte, porém derrotável).

Uso:
    python xadrez.py
    python xadrez.py --stockfish "C:/caminho/stockfish.exe"
    python xadrez.py --ascii        (peças em letras, se seu terminal não mostrar ♜♞♝)
"""

import argparse
import glob
import os
import random
import shutil
import sys
import time

try:
    import chess
    import chess.engine
    import chess.pgn
except ImportError:
    sys.exit("Falta a biblioteca python-chess. Instale com:  pip install chess")

# ----------------------------------------------------------------------------
# MOTOR INTERNO (minimax com poda alfa-beta, quiescência e tabelas de posição)
# ----------------------------------------------------------------------------

MATE = 100000
VALOR = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
         chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}

# Tabelas na visão das brancas, da 8ª fileira (a8) para a 1ª (h1).
PST = {
    chess.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5, 5, 10, 25, 25, 10, 5, 5,
        0, 0, 0, 20, 20, 0, 0, 0,
        5, -5, -10, 0, 0, -10, -5, 5,
        5, 10, 10, -20, -20, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0],
    chess.KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50],
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20],
    chess.ROOK: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, 10, 10, 10, 10, 5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        0, 0, 0, 5, 5, 0, 0, 0],
    chess.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20],
    chess.KING: [
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        20, 20, 0, 0, 0, 0, 20, 20,
        20, 30, 10, 0, 0, 10, 30, 20],
}
PST_REI_FINAL = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50]


class TempoEsgotado(Exception):
    pass


def avaliar(board):
    """Avaliação estática em centipeões, do ponto de vista de quem joga."""
    material_pesado = sum(
        VALOR[p.piece_type] for p in board.piece_map().values()
        if p.piece_type not in (chess.PAWN, chess.KING))
    final = material_pesado <= 2600
    total = 0
    for casa, peca in board.piece_map().items():
        idx = casa ^ 56 if peca.color == chess.WHITE else casa
        if peca.piece_type == chess.KING:
            tab = PST_REI_FINAL if final else PST[chess.KING]
        else:
            tab = PST[peca.piece_type]
        v = VALOR[peca.piece_type] + tab[idx]
        total += v if peca.color == chess.WHITE else -v
    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        total += 30
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        total -= 30
    return total if board.turn == chess.WHITE else -total


class MotorInterno:
    def __init__(self):
        self.nos = 0
        self.limite = None

    def _ordenar(self, board, lances, preferido=None):
        def chave(m):
            if m == preferido:
                return 10**6
            s = 0
            if board.is_capture(m):
                vit = board.piece_type_at(m.to_square) or chess.PAWN  # en passant
                ag = board.piece_type_at(m.from_square)
                s += 10 * VALOR[vit] - VALOR[ag] + 1000
            if m.promotion:
                s += VALOR[m.promotion] + 900
            if board.gives_check(m):
                s += 50
            return -s
        return sorted(lances, key=chave)

    def _tempo(self):
        self.nos += 1
        if self.limite and (self.nos & 1023) == 0 and time.time() > self.limite:
            raise TempoEsgotado

    def _quiescencia(self, board, alfa, beta, ply):
        self._tempo()
        parado = avaliar(board)
        if parado >= beta:
            return beta
        alfa = max(alfa, parado)
        caps = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]
        for m in self._ordenar(board, caps):
            board.push(m)
            nota = -self._quiescencia(board, -beta, -alfa, ply + 1)
            board.pop()
            if nota >= beta:
                return beta
            alfa = max(alfa, nota)
        return alfa

    def _busca(self, board, prof, alfa, beta, ply):
        self._tempo()
        if board.is_checkmate():
            return -MATE + ply
        if (board.is_stalemate() or board.is_insufficient_material()
                or board.halfmove_clock >= 100 or board.is_repetition(2)):
            return 0
        if prof <= 0:
            return self._quiescencia(board, alfa, beta, ply)
        if board.is_check():
            prof += 1  # extensão de xeque
        melhor = -MATE
        for m in self._ordenar(board, list(board.legal_moves)):
            board.push(m)
            nota = -self._busca(board, prof - 1, -beta, -alfa, ply + 1)
            board.pop()
            if nota > melhor:
                melhor = nota
            alfa = max(alfa, nota)
            if alfa >= beta:
                break
        return melhor

    def melhor(self, board, prof_max, tempo=None, todos=False):
        """Busca com aprofundamento iterativo.
        Retorna (lance, nota) ou, com todos=True, lista [(nota, lance)] ordenada."""
        self.nos = 0
        self.limite = time.time() + tempo if tempo else None
        board = board.copy()
        lances = list(board.legal_moves)
        resultado = None
        melhor_lance = None
        for prof in range(1, prof_max + 1):
            try:
                notas = []
                alfa = -MATE - 1
                for m in self._ordenar(board, lances, melhor_lance):
                    board.push(m)
                    # com todos=True precisamos da nota exata de cada lance
                    a = -MATE - 1 if todos else alfa
                    nota = -self._busca(board, prof - 1, -MATE - 1, -a, 1)
                    board.pop()
                    notas.append((nota, m))
                    alfa = max(alfa, nota)
                notas.sort(key=lambda x: -x[0])
                resultado = notas
                melhor_lance = notas[0][1]
                if abs(notas[0][0]) > MATE - 100:
                    break  # mate encontrado
            except TempoEsgotado:
                break  # usa o resultado da profundidade anterior
        if todos:
            return resultado
        return resultado[0][1], resultado[0][0]


# ----------------------------------------------------------------------------
# NÍVEIS E ANALISADOR
# ----------------------------------------------------------------------------

NIVEIS = {
    "1": ("Fácil", "facil"),
    "2": ("Médio", "medio"),
    "3": ("Difícil", "dificil"),
    "4": ("Impossível", "impossivel"),
}


def achar_stockfish(caminho=None):
    candidatos = []
    if caminho:
        candidatos.append(caminho)
    if os.environ.get("STOCKFISH_PATH"):
        candidatos.append(os.environ["STOCKFISH_PATH"])
    w = shutil.which("stockfish")
    if w:
        candidatos.append(w)
    candidatos += ["/usr/games/stockfish", "/usr/bin/stockfish",
                   "/usr/local/bin/stockfish", "/opt/homebrew/bin/stockfish"]
    aqui = os.path.dirname(os.path.abspath(__file__))
    for pasta in (aqui, os.getcwd()):
        candidatos += glob.glob(os.path.join(pasta, "stockfish*"))
        candidatos += glob.glob(os.path.join(pasta, "stockfish*", "stockfish*"))
    for c in candidatos:
        if c and os.path.isfile(c) and os.access(c, os.X_OK) and not c.endswith((".txt", ".md")):
            try:
                eng = chess.engine.SimpleEngine.popen_uci(c)
                return eng
            except Exception:
                continue
    return None


class Cerebro:
    """Escolhe o lance do bot e analisa posições (para dicas e treinamento)."""

    def __init__(self, nivel, stockfish):
        self.nivel = nivel
        self.sf = stockfish
        self.interno = MotorInterno()
        if self.sf:
            try:
                self.sf.configure({"Threads": min(4, os.cpu_count() or 1), "Hash": 256})
            except Exception:
                pass

    @property
    def impossivel_real(self):
        return self.nivel == "impossivel" and self.sf is not None

    def lance_do_bot(self, board):
        n = self.nivel
        if n == "facil":
            lances = list(board.legal_moves)
            if random.random() < 0.45:          # joga "no chute" boa parte das vezes
                return random.choice(lances)
            res = self.interno.melhor(board, 1, todos=True)
            escolha = random.choice(res[:max(2, len(res) // 3)])  # um dos melhores 1/3
            return escolha[1]
        if n == "medio":
            res = self.interno.melhor(board, 2, tempo=3, todos=True)
            if random.random() < 0.15 and len(res) > 1:
                return res[1][1]                 # às vezes erra um pouco
            return res[0][1]
        if n == "dificil":
            return self.interno.melhor(board, 5, tempo=6)[0]
        # impossível
        if self.sf:
            r = self.sf.play(board, chess.engine.Limit(time=2.0))
            return r.move
        return self.interno.melhor(board, 12, tempo=20)[0]

    def analisar(self, board, tempo=1.5):
        """(melhor lance, nota em centipeões do ponto de vista de quem joga)."""
        if self.sf:
            info = self.sf.analyse(board, chess.engine.Limit(time=tempo))
            nota = info["score"].pov(board.turn).score(mate_score=MATE)
            return info["pv"][0], nota
        return self.interno.melhor(board, 6, tempo=tempo * 2)

    def fechar(self):
        if self.sf:
            try:
                self.sf.quit()
            except Exception:
                pass


# ----------------------------------------------------------------------------
# INTERFACE
# ----------------------------------------------------------------------------

UNI = {"P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
       "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"}
USAR_ASCII = False
NOME_PECA = {chess.PAWN: "peão", chess.KNIGHT: "cavalo", chess.BISHOP: "bispo",
             chess.ROOK: "torre", chess.QUEEN: "dama", chess.KING: "rei"}


def desenhar(board, perspectiva, ultimo=None):
    ranks = range(7, -1, -1) if perspectiva == chess.WHITE else range(8)
    files = range(8) if perspectiva == chess.WHITE else range(7, -1, -1)
    letras = "  " + " ".join(chess.FILE_NAMES[f] for f in files)
    print()
    print(letras)
    for r in ranks:
        linha = f"{r + 1} "
        for f in files:
            casa = chess.square(f, r)
            p = board.piece_at(casa)
            if p:
                s = p.symbol() if USAR_ASCII else UNI[p.symbol()]
            else:
                s = "·" if not USAR_ASCII else "."
            linha += s + " "
        linha += f"{r + 1}"
        print(linha)
    print(letras)
    print()


def fmt_nota(nota):
    if abs(nota) > MATE - 200:
        n = (MATE - abs(nota) + 1) // 2
        return ("+" if nota > 0 else "-") + f"M{n}"
    return f"{nota / 100:+.2f}"


def analisar_lance_usuario(cerebro, board_antes, lance, melhor, nota_melhor):
    """Treinador: compara o lance do usuário com o melhor lance."""
    b = board_antes.copy()
    san_usuario = b.san(lance)
    b.push(lance)
    if b.is_game_over():
        nota_user = MATE if b.is_checkmate() else 0
    else:
        _, nota_op = cerebro.analisar(b, tempo=1.0)
        nota_user = -nota_op
    perda = max(0, nota_melhor - nota_user)
    san_melhor = board_antes.san(melhor)
    if lance == melhor or perda <= 25:
        rotulo = "✔ Excelente lance!" if lance == melhor else "✔ Bom lance."
    elif perda <= 80:
        rotulo = f"~ Imprecisão (perdeu ~{perda / 100:.2f} peão). Melhor era {san_melhor}."
    elif perda <= 200:
        rotulo = f"✘ Erro (perdeu ~{perda / 100:.2f} peão). Melhor era {san_melhor}."
    else:
        rotulo = f"✘✘ Erro grave! Melhor era {san_melhor}."
    print(f"   Treinador: {san_usuario} → {rotulo}  [avaliação: {fmt_nota(nota_user)}]")


AJUDA = """
Como jogar:
  Digite o lance em notação de coordenadas (e2e4, g1f3, e7e8q para promover)
  ou em notação algébrica inglesa (e4, Nf3, O-O, exd5, e8=Q).
  Letras das peças na algébrica: N=cavalo, B=bispo, R=torre, Q=dama, K=rei.

Comandos:
  ajuda        mostra esta ajuda
  lances       lista todos os seus lances legais
  lances e2    lista os lances legais da peça em e2
  salvar       salva a partida em PGN
  desistir     abandona a partida
Somente no modo TREINAMENTO:
  dica         mostra qual peça mover
  solucao      mostra o melhor lance
  avaliar      mostra quem está melhor (em peões)
  desfazer     desfaz seu último lance (e a resposta do bot)
"""


def ler_lance(board, texto):
    texto = texto.strip()
    try:
        return board.parse_san(texto)
    except ValueError:
        pass
    try:
        m = chess.Move.from_uci(texto.lower())
        # promoção automática para dama se o usuário esquecer a letra
        p = board.piece_at(m.from_square)
        if (p and p.piece_type == chess.PAWN and not m.promotion
                and chess.square_rank(m.to_square) in (0, 7)):
            m = chess.Move(m.from_square, m.to_square, chess.QUEEN)
        if m in board.legal_moves:
            return m
    except ValueError:
        pass
    return None


def salvar_pgn(board, brancas, pretas, resultado="*"):
    jogo = chess.pgn.Game.from_board(board)
    jogo.headers["White"] = brancas
    jogo.headers["Black"] = pretas
    jogo.headers["Result"] = resultado
    nome = time.strftime("partida_%Y%m%d_%H%M%S.pgn")
    with open(nome, "w", encoding="utf-8") as f:
        print(jogo, file=f)
    print(f"Partida salva em {nome}")


def resultado_texto(board, cor_usuario):
    if board.is_checkmate():
        venceu = (not board.turn) == cor_usuario
        return ("XEQUE-MATE! Você venceu! 🎉" if venceu
                else "XEQUE-MATE! O computador venceu."), ("1-0" if not board.turn else "0-1")
    if board.is_stalemate():
        return "Empate por afogamento.", "1/2-1/2"
    if board.is_insufficient_material():
        return "Empate por material insuficiente.", "1/2-1/2"
    if board.is_seventyfive_moves():
        return "Empate pela regra dos 75 lances.", "1/2-1/2"
    if board.is_fivefold_repetition():
        return "Empate por repetição.", "1/2-1/2"
    return "Fim de jogo.", "*"


def partida(cerebro, treino, cor_usuario, nome_nivel):
    board = chess.Board()
    ultimo = None
    cache = {}  # fen -> (melhor, nota)

    def analise(b):
        k = b.fen()
        if k not in cache:
            cache[k] = cerebro.analisar(b)
        return cache[k]

    print(AJUDA if treino else "\n(Digite 'ajuda' para ver os comandos.)")
    rotulo_bot = f"Computador ({nome_nivel})"
    nomes = ("Você", rotulo_bot) if cor_usuario == chess.WHITE else (rotulo_bot, "Você")

    while not board.is_game_over(claim_draw=False):
        desenhar(board, cor_usuario, ultimo)
        if board.turn == cor_usuario:
            if board.is_check():
                print("Você está em XEQUE!")
            while True:
                try:
                    entrada = input("Seu lance > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    entrada = "desistir"
                cmd = entrada.lower()
                if not cmd:
                    continue
                if cmd == "ajuda":
                    print(AJUDA)
                elif cmd.startswith("lances"):
                    partes = cmd.split()
                    lista = list(board.legal_moves)
                    if len(partes) > 1:
                        try:
                            casa = chess.parse_square(partes[1])
                            lista = [m for m in lista if m.from_square == casa]
                        except ValueError:
                            print("Casa inválida. Exemplo: lances e2")
                            continue
                    print("Lances:", ", ".join(board.san(m) for m in lista) or "nenhum")
                elif cmd == "salvar":
                    salvar_pgn(board, *nomes)
                elif cmd == "desistir":
                    print("Você desistiu. O computador venceu.")
                    salvar_pgn(board, *nomes, "0-1" if cor_usuario == chess.WHITE else "1-0")
                    return
                elif treino and cmd == "dica":
                    m, _ = analise(board)
                    p = board.piece_at(m.from_square)
                    print(f"Dica: mova o {NOME_PECA[p.piece_type]} em "
                          f"{chess.square_name(m.from_square)}.")
                elif treino and cmd in ("solucao", "solução"):
                    m, n = analise(board)
                    print(f"Melhor lance: {board.san(m)} ({m.uci()})  [avaliação {fmt_nota(n)}]")
                elif treino and cmd in ("avaliar", "avaliacao", "avaliação"):
                    _, n = analise(board)
                    print(f"Avaliação: {fmt_nota(n)}  (positivo = vantagem sua, negativo = do computador)")
                elif treino and cmd == "desfazer":
                    minimo = 2 if cor_usuario == chess.WHITE else 3
                    if len(board.move_stack) >= minimo:
                        board.pop()
                        board.pop()
                        ultimo = board.peek() if board.move_stack else None
                        desenhar(board, cor_usuario, ultimo)
                    else:
                        print("Nada para desfazer.")
                else:
                    lance = ler_lance(board, entrada)
                    if lance is None:
                        print("Lance inválido. Digite 'lances' para ver os legais.")
                        continue
                    if treino:
                        print("   (treinador analisando...)")
                        melhor, nota = analise(board)
                        analisar_lance_usuario(cerebro, board, lance, melhor, nota)
                    san = board.san(lance)
                    board.push(lance)
                    ultimo = lance
                    print(f"Você jogou: {san}")
                    break
        else:
            print("Computador pensando...")
            t = time.time()
            lance = cerebro.lance_do_bot(board)
            san = board.san(lance)
            board.push(lance)
            ultimo = lance
            print(f"Computador jogou: {san}  ({time.time() - t:.1f}s)")

    desenhar(board, cor_usuario, ultimo)
    msg, res = resultado_texto(board, cor_usuario)
    print(msg)
    salvar_pgn(board, *nomes, res)


# ----------------------------------------------------------------------------
# PROBLEMAS TÁTICOS (mate em 1 e mate em 2)
# ----------------------------------------------------------------------------

PROBLEMAS = [
    ("Mate em 1 (corredor)", "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", 1),
    ("Mate em 1 (mate do pastor)",
     "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", 1),
    ("Mate em 1 (mate sufocado)", "6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1", 1),
    ("Mate em 2 (escada de torres)", "7k/8/8/8/8/8/1R6/R5K1 w - - 0 1", 2),
    ("Mate em 2 (escada de torres, pretas)", "r5k1/1r6/8/8/8/8/8/7K b - - 0 1", 2),
]


def mate_forcado(board, n):
    """O lado que joga consegue dar mate em até n lances seus?"""
    if n <= 0:
        return False
    for m in board.legal_moves:
        board.push(m)
        if board.is_checkmate():
            board.pop()
            return True
        ok = False
        if n > 1 and not board.is_game_over():
            ok = all(_resposta_ok(board, r, n - 1) for r in list(board.legal_moves))
        board.pop()
        if ok:
            return True
    return False


def _resposta_ok(board, resposta, n):
    board.push(resposta)
    try:
        return mate_forcado(board, n)
    finally:
        board.pop()


def lance_mantem_mate(board, lance, n):
    board.push(lance)
    try:
        if board.is_checkmate():
            return True
        if n <= 1 or board.is_game_over():
            return False
        return all(_resposta_ok(board, r, n - 1) for r in list(board.legal_moves))
    finally:
        board.pop()


def modo_problemas():
    print("\n=== PROBLEMAS TÁTICOS ===")
    print("Dê xeque-mate no número de lances indicado. ('dica', 'pular' ou 'sair' funcionam.)")
    for titulo, fen, n in PROBLEMAS:
        board = chess.Board(fen)
        cor = board.turn
        restante = n
        print(f"\n--- {titulo} --- Você joga de {'brancas' if cor else 'pretas'}.")
        resolvido = False
        while True:
            desenhar(board, cor)
            entrada = input(f"Lance (mate em {restante}) > ").strip()
            cmd = entrada.lower()
            if cmd == "sair":
                return
            if cmd == "pular":
                break
            if cmd == "dica":
                for m in board.legal_moves:
                    if lance_mantem_mate(board, m, restante):
                        p = board.piece_at(m.from_square)
                        print(f"Dica: mova o {NOME_PECA[p.piece_type]} em "
                              f"{chess.square_name(m.from_square)}.")
                        break
                continue
            lance = ler_lance(board, entrada)
            if lance is None:
                print("Lance inválido.")
                continue
            if not lance_mantem_mate(board, lance, restante):
                print("Esse lance não leva ao mate forçado. Tente de novo.")
                continue
            board.push(lance)
            if board.is_checkmate():
                desenhar(board, cor)
                print("✔ XEQUE-MATE! Muito bem!")
                resolvido = True
                break
            # o adversário responde (a defesa que mais demora ao mate)
            restante -= 1
            resp = max(board.legal_moves,
                       key=lambda r: (not _resposta_ok(board, r, restante), random.random()))
            print(f"Adversário joga: {board.san(resp)}")
            board.push(resp)
        if not resolvido:
            print("Problema pulado.")
    print("\nFim dos problemas. Parabéns!")


# ----------------------------------------------------------------------------
# MENU
# ----------------------------------------------------------------------------

def escolher(prompt, opcoes):
    while True:
        r = input(prompt).strip().lower()
        if r in opcoes:
            return r
        print("Opção inválida.")


def main():
    global USAR_ASCII
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", help="caminho do executável do Stockfish")
    ap.add_argument("--ascii", action="store_true", help="peças em letras")
    args = ap.parse_args()
    USAR_ASCII = args.ascii

    sf = achar_stockfish(args.stockfish)

    print("=" * 46)
    print("        XADREZ CONTRA O COMPUTADOR")
    print("=" * 46)
    if sf:
        print("Stockfish encontrado: nível IMPOSSÍVEL de verdade.")
    else:
        print("Stockfish NÃO encontrado: o nível 'Impossível' usará o motor")
        print("interno no máximo (forte, mas não invencível). Veja como instalar")
        print("o Stockfish no início deste arquivo.")

    try:
        while True:
            print("\n1) Jogar contra o computador")
            print("2) Treinamento (treinador analisa cada lance, dicas, desfazer)")
            print("3) Problemas táticos (mates)")
            print("4) Sair")
            op = escolher("Escolha > ", {"1", "2", "3", "4"})
            if op == "4":
                break
            if op == "3":
                modo_problemas()
                continue

            print("\nNível do computador:")
            for k, (nome, _) in NIVEIS.items():
                print(f"  {k}) {nome}")
            nome_nivel, nivel = NIVEIS[escolher("Nível > ", set(NIVEIS))]
            if nivel == "impossivel" and not sf:
                print("Aviso: sem Stockfish, este nível não é realmente impossível.")

            print("\nSua cor: 1) Brancas  2) Pretas  3) Sorteio")
            c = escolher("Cor > ", {"1", "2", "3"})
            cor = {"1": chess.WHITE, "2": chess.BLACK,
                   "3": random.choice([chess.WHITE, chess.BLACK])}[c]
            print("Você joga de", "BRANCAS" if cor else "PRETAS")

            cerebro = Cerebro(nivel, sf)
            partida(cerebro, treino=(op == "2"), cor_usuario=cor, nome_nivel=nome_nivel)
    except (KeyboardInterrupt, EOFError):
        print("\nAté logo!")
    finally:
        if sf:
            try:
                sf.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
