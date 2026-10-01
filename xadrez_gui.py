#!/usr/bin/env python3
"""
XADREZ COM MOUSE (interface gráfica, estilo chess.com)

Use junto com o xadrez.py (os dois arquivos na MESMA pasta):
    pip install chess
    python xadrez_gui.py
    python xadrez_gui.py --stockfish "C:/caminho/stockfish.exe"

Como jogar:
  - Clique numa peça sua: os lances possíveis aparecem (pontos e anéis).
  - Clique na casa de destino  OU  arraste a peça até lá.
  - Promoção do peão: abre uma janelinha para escolher a peça.
  - Roque: mova o rei duas casas em direção à torre.

Níveis: Fácil, Médio, Difícil, Impossível (Stockfish; veja xadrez.py).
Modo treinamento: o treinador comenta cada lance, e há Dica, Desfazer
e barra de avaliação.
"""

import argparse
import math
import os
import queue
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import chess
    import chess.pgn
except ImportError:
    sys.exit("Falta a biblioteca python-chess. Instale com:  pip install chess")
try:
    import xadrez as X
except ImportError:
    sys.exit("Coloque o xadrez_gui.py na mesma pasta do xadrez.py.")

TAM = 80  # tamanho de cada casa em pixels
CLARO, ESCURO = "#f0d9b5", "#b58863"
ULT_CLARO, ULT_ESCURO = "#f7ec74", "#dac331"
SELECIONADA, XEQUE_COR = "#f6f669", "#e85d5d"
DICA_COR = "#5aa9e6"
GLIFOS = {chess.KING: "\u265a", chess.QUEEN: "\u265b", chess.ROOK: "\u265c",
          chess.BISHOP: "\u265d", chess.KNIGHT: "\u265e", chess.PAWN: "\u265f"}
NIVEIS = {"Fácil": "facil", "Médio": "medio", "Difícil": "dificil", "Impossível": "impossivel"}


def escolher_fonte():
    disponiveis = set(tkfont.families())
    for f in ("Segoe UI Symbol", "Apple Symbols", "DejaVu Sans", "Noto Sans Symbols2",
              "Arial Unicode MS", "FreeSerif", "Symbola"):
        if f in disponiveis:
            return f
    return "TkDefaultFont"


class App:
    def __init__(self, root, sf):
        self.root = root
        self.sf = sf
        root.title("Xadrez")
        root.resizable(False, False)
        self.fonte = escolher_fonte()

        self.board = chess.Board()
        self.cor = chess.WHITE
        self.persp = chess.WHITE
        self.treino = False
        self.cerebro = None
        self.sel = None
        self.destinos = set()
        self.ultimo = None
        self.dica = None          # (estágio, lance)
        self.busy = False
        self.fim = False
        self.drag = None
        self.gid = 0
        self.cache = {}
        self.fila = queue.Queue()
        self.nome_nivel = "Fácil"

        self.var_nivel = tk.StringVar(value="Fácil")
        self.var_cor = tk.StringVar(value="Brancas")
        self.var_treino = tk.BooleanVar(value=False)
        self.var_letras = tk.BooleanVar(value=False)
        self.status = tk.StringVar()

        self._montar_interface()
        self.novo_jogo()
        self.root.after(50, self.poll)

    # ------------------------------------------------------------------ UI
    def _montar_interface(self):
        self.canvas = tk.Canvas(self.root, width=8 * TAM, height=8 * TAM,
                                highlightthickness=0, cursor="hand2")
        self.canvas.grid(row=0, column=0, padx=10, pady=10)
        self.canvas.bind("<ButtonPress-1>", self.ao_pressionar)
        self.canvas.bind("<B1-Motion>", self.ao_mover)
        self.canvas.bind("<ButtonRelease-1>", self.ao_soltar)

        p = ttk.Frame(self.root, padding=(0, 10, 10, 10))
        p.grid(row=0, column=1, sticky="ns")

        ttk.Label(p, text="Nível do computador").pack(anchor="w")
        ttk.Combobox(p, textvariable=self.var_nivel, values=list(NIVEIS),
                     state="readonly", width=22).pack(anchor="w", pady=(0, 6))
        ttk.Label(p, text="Sua cor").pack(anchor="w")
        ttk.Combobox(p, textvariable=self.var_cor, values=["Brancas", "Pretas", "Sorteio"],
                     state="readonly", width=22).pack(anchor="w", pady=(0, 6))
        ttk.Checkbutton(p, text="Modo treinamento", variable=self.var_treino).pack(anchor="w")
        ttk.Checkbutton(p, text="Peças em letras", variable=self.var_letras,
                        command=self.redesenhar).pack(anchor="w", pady=(0, 6))
        self.btn_novo = ttk.Button(p, text="Novo jogo", command=self.novo_jogo)
        self.btn_novo.pack(fill="x")

        linha = ttk.Frame(p)
        linha.pack(fill="x", pady=4)
        self.btn_desf = ttk.Button(linha, text="Desfazer", command=self.desfazer)
        self.btn_desf.pack(side="left", expand=True, fill="x")
        self.btn_dica = ttk.Button(linha, text="Dica", command=self.pedir_dica)
        self.btn_dica.pack(side="left", expand=True, fill="x")
        linha2 = ttk.Frame(p)
        linha2.pack(fill="x")
        ttk.Button(linha2, text="Virar", command=self.virar).pack(side="left", expand=True, fill="x")
        self.btn_desist = ttk.Button(linha2, text="Desistir", command=self.desistir)
        self.btn_desist.pack(side="left", expand=True, fill="x")
        ttk.Button(p, text="Salvar PGN", command=self.salvar_pgn).pack(fill="x", pady=4)

        ttk.Label(p, textvariable=self.status, wraplength=230,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(8, 4))

        ttk.Label(p, text="Avaliação (treinamento)").pack(anchor="w")
        self.barra = tk.Canvas(p, width=230, height=18, highlightthickness=1,
                               highlightbackground="#888")
        self.barra.pack(anchor="w", pady=(0, 6))

        ttk.Label(p, text="Lances e comentários").pack(anchor="w")
        cx = ttk.Frame(p)
        cx.pack(fill="both", expand=True)
        self.log_txt = tk.Text(cx, width=30, height=13, state="disabled", wrap="word")
        sb = ttk.Scrollbar(cx, command=self.log_txt.yview)
        self.log_txt.config(yscrollcommand=sb.set)
        self.log_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.log_txt.tag_config("bom", foreground="#2e7d32")
        self.log_txt.tag_config("erro", foreground="#c62828")
        self.log_txt.tag_config("aviso", foreground="#ef6c00")
        self.log_txt.tag_config("info", foreground="#555555")

        stock = "Stockfish: encontrado" if self.sf else "Stockfish: não encontrado"
        ttk.Label(p, text=stock, foreground="#666").pack(anchor="w", pady=(6, 0))

    def log(self, texto, tag=None):
        self.log_txt.config(state="normal")
        self.log_txt.insert("end", texto + "\n", tag)
        self.log_txt.see("end")
        self.log_txt.config(state="disabled")

    def limpar_log(self):
        self.log_txt.config(state="normal")
        self.log_txt.delete("1.0", "end")
        self.log_txt.config(state="disabled")

    def atualizar_barra(self, nota_brancas=None):
        c = self.barra
        c.delete("all")
        w, h = 230, 18
        if nota_brancas is None:
            c.create_rectangle(0, 0, w, h, fill="#ddd", outline="")
            c.create_text(w / 2, h / 2, text="—", fill="#666")
            return
        n = max(-3000, min(3000, nota_brancas))
        frac = 1 / (1 + math.exp(-n / 400))
        c.create_rectangle(0, 0, w, h, fill="#222", outline="")
        c.create_rectangle(0, 0, w * frac, h, fill="#eee", outline="")
        c.create_text(w / 2, h / 2, text=X.fmt_nota(nota_brancas), fill="#c62828")

    def atualizar_status(self):
        if self.fim:
            return
        if self.busy:
            self.status.set("Computador pensando...")
        else:
            txt = "Sua vez (%s)" % ("brancas" if self.cor else "pretas")
            if self.board.is_check():
                txt += " — XEQUE!"
            self.status.set(txt)

    def set_busy(self, b):
        self.busy = b
        est = "disabled" if b else "normal"
        self.btn_novo.config(state=est)
        self.btn_desist.config(state=est)
        est2 = "normal" if (self.treino and not b) else "disabled"
        self.btn_desf.config(state=est2)
        self.btn_dica.config(state=est2)
        self.atualizar_status()

    # ------------------------------------------------------------ desenho
    def origem(self, sq):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        if self.persp == chess.WHITE:
            return f * TAM, (7 - r) * TAM
        return (7 - f) * TAM, r * TAM

    def casa_em(self, x, y):
        c, l = int(x // TAM), int(y // TAM)
        if not (0 <= c < 8 and 0 <= l < 8) or x < 0 or y < 0:
            return None
        if self.persp == chess.WHITE:
            return chess.square(c, 7 - l)
        return chess.square(7 - c, l)

    def desenhar_peca(self, cx, cy, peca, tag):
        c = self.canvas
        branca = peca.color == chess.WHITE
        if self.var_letras.get():
            r = TAM * 0.36
            c.create_oval(cx - r, cy - r, cx + r, cy + r, tags=tag, width=3,
                          fill="#ffffff" if branca else "#222222",
                          outline="#222222" if branca else "#eeeeee")
            c.create_text(cx, cy, text=peca.symbol().upper(), tags=tag,
                          fill="#222222" if branca else "#ffffff",
                          font=("Helvetica", int(TAM * 0.38), "bold"))
            return
        g = GLIFOS[peca.piece_type]
        fonte = (self.fonte, -int(TAM * 0.74))
        if branca:
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                           (-1.5, -1.5), (1.5, 1.5), (-1.5, 1.5), (1.5, -1.5)):
                c.create_text(cx + dx, cy + dy, text=g, font=fonte, fill="#111111", tags=tag)
            c.create_text(cx, cy, text=g, font=fonte, fill="#ffffff", tags=tag)
        else:
            c.create_text(cx, cy, text=g, font=fonte, fill="#111111", tags=tag)

    def redesenhar(self, ocultar=None):
        c = self.canvas
        c.delete("all")
        rei_xeque = self.board.king(self.board.turn) if self.board.is_check() else None
        dica_casas = set()
        if self.dica:
            m = self.dica[1]
            dica_casas = {m.from_square} if self.dica[0] == 1 else {m.from_square, m.to_square}
        for sq in chess.SQUARES:
            x, y = self.origem(sq)
            f, r = chess.square_file(sq), chess.square_rank(sq)
            claro = (f + r) % 2 == 1
            cor = CLARO if claro else ESCURO
            if self.ultimo and sq in (self.ultimo.from_square, self.ultimo.to_square):
                cor = ULT_CLARO if claro else ULT_ESCURO
            if sq in dica_casas:
                cor = DICA_COR
            if sq == self.sel:
                cor = SELECIONADA
            if sq == rei_xeque:
                cor = XEQUE_COR
            c.create_rectangle(x, y, x + TAM, y + TAM, fill=cor, outline=cor)
            tc = ESCURO if claro else CLARO
            if x == 0:
                c.create_text(x + 4, y + 8, text=str(r + 1), fill=tc, anchor="w",
                              font=("Helvetica", 9, "bold"))
            if y == 7 * TAM:
                c.create_text(x + TAM - 4, y + TAM - 8, text=chess.FILE_NAMES[f], fill=tc,
                              anchor="e", font=("Helvetica", 9, "bold"))
        for sq, peca in self.board.piece_map().items():
            if sq == ocultar:
                continue
            x, y = self.origem(sq)
            self.desenhar_peca(x + TAM / 2, y + TAM / 2, peca, "peca")
        for sq in self.destinos:
            x, y = self.origem(sq)
            cx, cy = x + TAM / 2, y + TAM / 2
            if self.board.piece_at(sq) or sq == self.board.ep_square:
                c.create_oval(x + 4, y + 4, x + TAM - 4, y + TAM - 4, outline="#6f8f4f", width=6)
            else:
                c.create_oval(cx - 11, cy - 11, cx + 11, cy + 11, fill="#6f8f4f", outline="")
        if self.dica and self.dica[0] == 2:
            m = self.dica[1]
            x1, y1 = self.origem(m.from_square)
            x2, y2 = self.origem(m.to_square)
            c.create_line(x1 + TAM / 2, y1 + TAM / 2, x2 + TAM / 2, y2 + TAM / 2,
                          fill=DICA_COR, width=10, arrow=tk.LAST, arrowshape=(22, 26, 12))

    # -------------------------------------------------------------- mouse
    def ao_pressionar(self, ev):
        if self.busy or self.fim or self.board.turn != self.cor:
            return
        sq = self.casa_em(ev.x, ev.y)
        if sq is None:
            return
        if self.sel is not None and sq in self.destinos:
            if self.tentar_lance(self.sel, sq):
                return
        p = self.board.piece_at(sq)
        if p and p.color == self.cor:
            ja_sel = self.sel == sq
            self.sel = sq
            self.destinos = {m.to_square for m in self.board.legal_moves if m.from_square == sq}
            self.drag = {"sq": sq, "x": ev.x, "y": ev.y, "moveu": False, "ja_sel": ja_sel}
            self.redesenhar(ocultar=sq)
            self.desenhar_peca(ev.x, ev.y, p, "arrasto")
        else:
            self.sel, self.destinos = None, set()
            self.redesenhar()

    def ao_mover(self, ev):
        if not self.drag:
            return
        dx, dy = ev.x - self.drag["x"], ev.y - self.drag["y"]
        self.canvas.move("arrasto", dx, dy)
        self.drag["x"], self.drag["y"] = ev.x, ev.y
        self.drag["moveu"] = True

    def ao_soltar(self, ev):
        if not self.drag:
            return
        d, self.drag = self.drag, None
        self.canvas.delete("arrasto")
        sq = self.casa_em(ev.x, ev.y)
        if sq is not None and sq != d["sq"] and sq in self.destinos:
            if self.tentar_lance(d["sq"], sq):
                return
        elif sq == d["sq"]:
            if d["ja_sel"] and not d["moveu"]:
                self.sel, self.destinos = None, set()
            self.redesenhar()
            return
        self.sel, self.destinos = None, set()
        self.redesenhar()

    # --------------------------------------------------------------- lances
    def escolher_promocao(self):
        top = tk.Toplevel(self.root)
        top.title("Promoção")
        top.transient(self.root)
        top.resizable(False, False)
        escolha = {"p": chess.QUEEN}

        def fechar(pt):
            escolha["p"] = pt
            top.destroy()

        ttk.Label(top, text="Promover o peão para:").pack(padx=14, pady=(12, 6))
        fr = ttk.Frame(top)
        fr.pack(padx=14, pady=(0, 12))
        for nome, pt in (("Dama", chess.QUEEN), ("Torre", chess.ROOK),
                         ("Bispo", chess.BISHOP), ("Cavalo", chess.KNIGHT)):
            ttk.Button(fr, text=nome, command=lambda p=pt: fechar(p)).pack(side="left", padx=3)
        top.grab_set()
        self.root.wait_window(top)
        return escolha["p"]

    def tentar_lance(self, o, d):
        cand = [m for m in self.board.legal_moves if m.from_square == o and m.to_square == d]
        if not cand:
            return False
        m = cand[0]
        if m.promotion:
            m = chess.Move(o, d, self.escolher_promocao())
        self.jogar_usuario(m)
        return True

    def jogar_usuario(self, m):
        antes = self.board.copy()
        san = self.board.san(m)
        self.board.push(m)
        self.ultimo = m
        self.sel, self.destinos, self.dica = None, set(), None
        self.log("Você: " + san)
        self.redesenhar()
        if self.verificar_fim():
            return
        self.iniciar_trabalho(antes if self.treino else None, m)

    def aplicar_bot(self, m):
        san = self.board.san(m)
        self.board.push(m)
        self.ultimo = m
        self.log("Computador: " + san)
        self.set_busy(False)
        self.redesenhar()
        self.verificar_fim()

    def verificar_fim(self):
        if not self.board.is_game_over():
            return False
        self.fim = True
        msg, _ = X.resultado_texto(self.board, self.cor)
        msg = msg.replace(" 🎉", "")
        self.status.set(msg)
        self.log(msg, "info")
        self.redesenhar()
        messagebox.showinfo("Fim de jogo", msg)
        return True

    # ------------------------------------------------- trabalho em segundo plano
    def analise(self, cerebro, b, tempo=1.5):
        k = b.fen()
        if k not in self.cache:
            self.cache[k] = cerebro.analisar(b, tempo=tempo)
        return self.cache[k]

    def comentar(self, cerebro, antes, lance, melhor, nota_melhor):
        b = antes.copy()
        san_u = b.san(lance)
        b.push(lance)
        if b.is_game_over():
            nota_user = X.MATE if b.is_checkmate() else 0
        else:
            _, nota_op = self.analise(cerebro, b, tempo=1.0)
            nota_user = -nota_op
        perda = max(0, nota_melhor - nota_user)
        san_m = antes.san(melhor)
        if lance == melhor:
            return "Treinador: %s — excelente lance!" % san_u, "bom", nota_user
        if perda <= 25:
            return "Treinador: %s — bom lance." % san_u, "bom", nota_user
        if perda <= 80:
            return ("Treinador: %s — imprecisão (-%.2f). Melhor: %s." % (san_u, perda / 100, san_m),
                    "aviso", nota_user)
        if perda <= 200:
            return ("Treinador: %s — erro (-%.2f). Melhor: %s." % (san_u, perda / 100, san_m),
                    "erro", nota_user)
        return "Treinador: %s — erro grave! Melhor: %s." % (san_u, san_m), "erro", nota_user

    def iniciar_trabalho(self, antes=None, lance=None):
        self.set_busy(True)
        gid, pos, cerebro = self.gid, self.board.copy(), self.cerebro

        def job():
            try:
                if antes is not None:
                    melhor, nota = self.analise(cerebro, antes)
                    self.fila.put((gid, "fb", self.comentar(cerebro, antes, lance, melhor, nota)))
                bot = cerebro.lance_do_bot(pos)
                self.fila.put((gid, "bot", bot))
            except Exception as e:  # noqa
                self.fila.put((gid, "erro", repr(e)))

        threading.Thread(target=job, daemon=True).start()

    def poll(self):
        try:
            while True:
                gid, tipo, dado = self.fila.get_nowait()
                if gid != self.gid:
                    continue
                if tipo == "fb":
                    texto, tag, nota_user = dado
                    self.log(texto, tag)
                    self.atualizar_barra(nota_user if self.cor == chess.WHITE else -nota_user)
                elif tipo == "bot":
                    self.aplicar_bot(dado)
                elif tipo == "dica":
                    self.mostrar_dica(*dado)
                elif tipo == "erro":
                    self.set_busy(False)
                    messagebox.showerror("Erro", dado)
        except queue.Empty:
            pass
        self.root.after(50, self.poll)

    # ---------------------------------------------------------- botões
    def pedir_dica(self):
        if self.busy or self.fim or not self.treino or self.board.turn != self.cor:
            return
        if self.dica:
            estagio, m = self.dica
            if estagio == 1:
                self.dica = (2, m)
                self.log("Melhor lance: " + self.board.san(m), "info")
            else:
                self.dica = None
            self.redesenhar()
            return
        self.set_busy(True)
        gid, pos, cerebro = self.gid, self.board.copy(), self.cerebro

        def job():
            try:
                self.fila.put((gid, "dica", self.analise(cerebro, pos)))
            except Exception as e:  # noqa
                self.fila.put((gid, "erro", repr(e)))

        threading.Thread(target=job, daemon=True).start()

    def mostrar_dica(self, m, nota):
        self.dica = (1, m)
        self.set_busy(False)
        self.atualizar_barra(nota if self.cor == chess.WHITE else -nota)
        self.log("Dica: mova a peça destacada em azul. Clique em Dica de novo "
                 "para ver o lance.", "info")
        self.redesenhar()

    def desfazer(self):
        if self.busy or not self.treino:
            return
        k = 1 if self.board.turn != self.cor else 2
        base = 1 if self.cor == chess.BLACK else 0
        if len(self.board.move_stack) - k < base:
            return
        for _ in range(k):
            self.board.pop()
        self.ultimo = self.board.peek() if self.board.move_stack else None
        self.sel, self.destinos, self.dica, self.fim = None, set(), None, False
        self.log("Lance desfeito.", "info")
        self.redesenhar()
        self.atualizar_status()

    def virar(self):
        self.persp = not self.persp
        self.redesenhar()

    def desistir(self):
        if self.busy or self.fim:
            return
        if messagebox.askyesno("Desistir", "Deseja mesmo desistir da partida?"):
            self.fim = True
            self.status.set("Você desistiu. O computador venceu.")
            self.log("Você desistiu.", "info")

    def salvar_pgn(self):
        jogo = chess.pgn.Game.from_board(self.board)
        voce, bot = "Você", "Computador (%s)" % self.nome_nivel
        jogo.headers["White"] = voce if self.cor == chess.WHITE else bot
        jogo.headers["Black"] = bot if self.cor == chess.WHITE else voce
        caminho = filedialog.asksaveasfilename(
            defaultextension=".pgn", filetypes=[("PGN", "*.pgn")],
            initialfile=time.strftime("partida_%Y%m%d_%H%M%S.pgn"))
        if caminho:
            with open(caminho, "w", encoding="utf-8") as f:
                print(jogo, file=f)
            self.log("Partida salva.", "info")

    def novo_jogo(self):
        self.gid += 1
        self.nome_nivel = self.var_nivel.get()
        self.treino = self.var_treino.get()
        escolha = self.var_cor.get()
        self.cor = {"Brancas": chess.WHITE, "Pretas": chess.BLACK}.get(
            escolha, random.choice([chess.WHITE, chess.BLACK]))
        self.persp = self.cor
        self.cerebro = X.Cerebro(NIVEIS[self.nome_nivel], self.sf)
        self.board = chess.Board()
        self.sel, self.destinos, self.ultimo, self.dica = None, set(), None, None
        self.fim, self.drag = False, None
        self.cache = {}
        self.limpar_log()
        self.atualizar_barra(None)
        self.root.title("Xadrez — %s%s" % (self.nome_nivel, " (treinamento)" if self.treino else ""))
        self.log("Você joga de %s. Nível: %s." % ("brancas" if self.cor else "pretas",
                                                  self.nome_nivel), "info")
        if NIVEIS[self.nome_nivel] == "impossivel" and not self.sf:
            self.log("Aviso: sem Stockfish este nível não é realmente impossível "
                     "(veja o topo do xadrez.py).", "aviso")
        self.redesenhar()
        self.set_busy(False)
        if self.board.turn != self.cor:
            self.iniciar_trabalho()

    def fechar(self):
        self.gid += 1
        if self.sf:
            try:
                self.sf.quit()
            except Exception:
                pass
        self.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", help="caminho do executável do Stockfish")
    args = ap.parse_args()
    root = tk.Tk()
    sf = X.achar_stockfish(args.stockfish)
    app = App(root, sf)
    root.protocol("WM_DELETE_WINDOW", app.fechar)
    root.mainloop()


if __name__ == "__main__":
    main()
