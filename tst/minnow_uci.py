"""minnow_uci.py -- UCI protocol wrapper around minnow_engine.py.

Lets minnow plug into any UCI-speaking GUI or match runner (cutechess-cli,
Arena, python-chess's engine interface, etc.) instead of only the toy CLI
in minnow_tools.py. Kept as a separate file from the engine on purpose,
same reasoning as minnow_tools.py: it's tooling, not core search/eval
logic, so it doesn't count against the engine's line-count comparison to
Sunfish.

Supported commands: uci, isready, ucinewgame, position [startpos|fen ...]
[moves ...], go [depth N | movetime MS | wtime W btime B [winc I binc I]
| infinite], stop, quit.

"go" runs in a background thread so "stop" can interrupt it -- the engine
already polls a wall-clock deadline internally (see Engine.search), so
stopping just means setting that deadline to "now".
"""
import sys
import threading
import time

from minnow_engine import Pos, Engine
from minnow_tools import from_fen, algebraic

ENGINE_NAME = "minnow"
ENGINE_AUTHOR = "minnow project"


def parse_uci_move(pos, ply, move_str):
    """Convert a UCI move string (e.g. 'e2e4', 'e7e8q') into one of pos's
    internal move tuples. UCI squares are always absolute (a1..h8); the
    engine's internal squares are from the mover's own perspective, so on
    odd plies (Black to move) the squares are flipped with ^56 before
    matching, the same flip make_move() itself uses."""
    files = "abcdefgh"
    f_file, f_rank, t_file, t_rank = move_str[0], move_str[1], move_str[2], move_str[3]
    promo_ch = move_str[4] if len(move_str) > 4 else None
    f_abs = (8 - int(f_rank)) * 8 + files.index(f_file)
    t_abs = (8 - int(t_rank)) * 8 + files.index(t_file)
    if ply % 2 == 1:
        f_abs, t_abs = f_abs ^ 56, t_abs ^ 56
    promo_map = {"q": 5, "r": 4, "b": 3, "n": 2}  # matches Q,R,B,N = 5,4,3,2 in minnow_engine
    promo = promo_map.get(promo_ch, 0)
    for mv in pos.legal():
        f, t, p, _flag = mv
        if f == f_abs and t == t_abs and p == promo:
            return mv
    return None


class UCIEngine:
    def __init__(self):
        self.pos = Pos.start()
        self.ply = 0
        self.engine = Engine()
        self.search_thread = None
        self.lock = threading.Lock()

    def set_position(self, tokens):
        if tokens[0] == "startpos":
            self.pos = Pos.start()
            self.ply = 0
            rest = tokens[1:]
        elif tokens[0] == "fen":
            fen = " ".join(tokens[1:7])
            self.pos = from_fen(fen)
            # ply parity must match the FEN's side-to-move so move parsing
            # flips squares correctly; FEN field 2 ('w'/'b') tells us that.
            self.ply = 0 if tokens[2] == "w" else 1
            rest = tokens[7:]
        else:
            return
        if rest and rest[0] == "moves":
            for mv_str in rest[1:]:
                mv = parse_uci_move(self.pos, self.ply, mv_str)
                if mv is None:
                    break  # malformed input from the GUI; stop applying
                self.pos = self.pos.move(mv)
                self.ply += 1

    def go(self, tokens):
        depth_limit = 99
        time_limit = 3.0  # sensible default if the GUI gives us nothing
        i = 0
        wtime = btime = winc = binc = None
        while i < len(tokens):
            tok = tokens[i]
            if tok == "depth":
                depth_limit = int(tokens[i + 1]); i += 2
            elif tok == "movetime":
                time_limit = int(tokens[i + 1]) / 1000.0; i += 2
            elif tok == "wtime":
                wtime = int(tokens[i + 1]); i += 2
            elif tok == "btime":
                btime = int(tokens[i + 1]); i += 2
            elif tok == "winc":
                winc = int(tokens[i + 1]); i += 2
            elif tok == "binc":
                binc = int(tokens[i + 1]); i += 2
            elif tok == "infinite":
                time_limit = 1e9; i += 1
            else:
                i += 1
        if wtime is not None or btime is not None:
            my_time = wtime if self.ply % 2 == 0 else btime
            my_inc = (winc or 0) if self.ply % 2 == 0 else (binc or 0)
            if my_time is not None:
                # simple fixed-fraction allocation: 1/30 of remaining clock
                # plus increment, simpler than Sunfish's own clock budgeting
                # but adequate for a non-tournament-grade time control.
                time_limit = max(0.05, my_time / 1000.0 / 30 + my_inc / 1000.0)

        def run():
            best = None
            for d, score, move, nodes, elapsed in self.engine.search(self.pos, depth_limit, time_limit):
                best = move
                with self.lock:
                    nps = int(nodes / max(elapsed, 1e-6))
                    pv = algebraic(move, self.ply % 2 == 1) if move else ""
                    print(f"info depth {d} score cp {score} nodes {nodes} nps {nps} "
                          f"time {int(elapsed*1000)} pv {pv}", flush=True)
            with self.lock:
                mv_str = algebraic(best, self.ply % 2 == 1) if best else "0000"
                print(f"bestmove {mv_str}", flush=True)

        self.search_thread = threading.Thread(target=run, daemon=True)
        self.search_thread.start()

    def stop(self):
        self.engine.stop = True
        if self.search_thread is not None:
            self.search_thread.join(timeout=2.0)


def main():
    uci = UCIEngine()
    for line in sys.stdin:
        tokens = line.split()
        if not tokens:
            continue
        cmd = tokens[0]
        if cmd == "uci":
            print(f"id name {ENGINE_NAME}")
            print(f"id author {ENGINE_AUTHOR}")
            print("uciok", flush=True)
        elif cmd == "isready":
            print("readyok", flush=True)
        elif cmd == "ucinewgame":
            uci.engine = Engine()
            uci.pos = Pos.start()
            uci.ply = 0
        elif cmd == "position":
            uci.set_position(tokens[1:])
        elif cmd == "go":
            uci.go(tokens[1:])
        elif cmd == "stop":
            uci.stop()
        elif cmd in ("quit", "exit"):
            uci.stop()
            return
        # unrecognized commands (e.g. "setoption", "debug") are ignored,
        # since minnow has no tunable options to expose
    # stdin closed (e.g. piped input ended) without an explicit "quit":
    # still wait for any in-flight search so "bestmove" gets printed.
    if uci.search_thread is not None:
        uci.search_thread.join()


if __name__ == "__main__":
    main()
