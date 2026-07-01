#!/usr/bin/env pypy3
from __future__ import print_function

import time, math
from itertools import count, takewhile
from collections import namedtuple, defaultdict

# Unbuffered output: use pypy3 -u, or uncomment the two lines below:
#from functools import partial; print = partial(print, flush=True)

version = "Tetrafish"

###############################################################################
# Piece-Square tables. Tune these to change sunfish's behaviour
###############################################################################

# With xz compression this whole section takes 652 bytes.
# That's pretty good given we have 64*6 = 384 values.
# Though probably we could do better...
# For one thing, they could easily all fit into int8.
piece = {"P": 100, "N": 305, "B": 333, "R": 563, "Q": 950, "K": 60000}
pst = {
    'P': (   0,   0,   0,   0,   0,   0,   0,   0,
             5,  10,  15,  20,  20,  15,  10,   5,
             4,   8,  12,  16,  16,  12,   8,   4,
             3,   6,   9,  12,  12,   9,   6,   3,
             2,   4,   6,  10,  10,   6,   4,   2,
             1,   2,   3,  -5,  -5,   3,   2,   1,
             0,   0,   0, -10, -10,   0,   0,   0,
             0,   0,   0,   0,   0,   0,   0,   0),
    'N': ( -50, -40, -30, -30, -30, -30, -40, -50,
           -40, -20,   0,   5,   5,   0, -20, -40,
           -30,   5,  10,  15,  15,  10,   5, -30,
           -30,   0,  15,  20,  20,  15,   0, -30,
           -30,   5,  15,  20,  20,  15,   5, -30,
           -30,   0,  10,  15,  15,  10,   0, -30,
           -40, -20,   0,   0,   0,   0, -20, -40,
           -50, -40, -30, -30, -30, -30, -40, -50),
    'B': ( -20, -10, -10, -10, -10, -10, -10, -20,
           -10,   5,   0,   0,   0,   0,   5, -10,
           -10,  10,  10,  10,  10,  10,  10, -10,
           -10,   0,  10,  10,  10,  10,   0, -10,
           -10,   5,   5,  10,  10,   5,   5, -10,
           -10,   0,   5,  10,  10,   5,   0, -10,
           -10,   0,   0,   0,   0,   0,   0, -10,
           -20, -10, -10, -10, -10, -10, -10, -20),
    'R': (   0,   0,   0,   5,   5,   0,   0,   0,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
            -5,   0,   0,   0,   0,   0,   0,  -5,
             5,  10,  10,  10,  10,  10,  10,   5,
             0,   0,   0,   0,   0,   0,   0,   0),
    'Q': ( -20, -10, -10,  -5,  -5, -10, -10, -20,
           -10,   0,   5,   0,   0,   0,   0, -10,
           -10,   5,   5,   5,   5,   5,   0, -10,
             0,   0,   5,   5,   5,   5,   0,  -5,
            -5,   0,   5,   5,   5,   5,   0,  -5,
           -10,   0,   5,   5,   5,   5,   0, -10,
           -10,   0,   0,   0,   0,   0,   0, -10,
           -20, -10, -10,  -5,  -5, -10, -10, -20),
    'K': (  20,  30,  10,   0,   0,  10,  30,  20,
            20,  20,   0,   0,   0,   0,  20,  20,
           -10, -20, -20, -20, -20, -20, -20, -10,
           -20, -30, -30, -40, -40, -30, -30, -20,
           -30, -40, -40, -50, -50, -40, -40, -30,
           -30, -40, -40, -50, -50, -40, -40, -30,
           -30, -40, -40, -50, -50, -40, -40, -30,
           -30, -40, -40, -50, -50, -40, -40, -30),
}
# Pad tables and join piece and pst dictionaries
for k, table in pst.items():
    padrow = lambda row: (0,) + tuple(x + piece[k] for x in row) + (0,)
    pst[k] = sum((padrow(table[i * 8 : i * 8 + 8]) for i in range(8)), ())
    pst[k] = (0,) * 20 + pst[k] + (0,) * 20

###############################################################################
# Global constants
###############################################################################

# Our board is represented as a 120 character string. The padding allows for
# fast detection of moves that don't stay within the board.
A1, H1, A8, H8 = 91, 98, 21, 28
initial = (
    "         \n"  #   0 -  9
    "         \n"  #  10 - 19
    " rnbqkbnr\n"  #  20 - 29
    " pppppppp\n"  #  30 - 39
    " ........\n"  #  40 - 49
    " ........\n"  #  50 - 59
    " ........\n"  #  60 - 69
    " ........\n"  #  70 - 79
    " PPPPPPPP\n"  #  80 - 89
    " RNBQKBNR\n"  #  90 - 99
    "         \n"  # 100 -109
    "         \n"  # 110 -119
)

# Lists of possible moves for each piece type.
N, E, S, W = -10, 1, 10, -1
directions = {
    "P": (N, N+N, N+W, N+E),
    "N": (N+N+E, E+N+E, E+S+E, S+S+E, S+S+W, W+S+W, W+N+W, N+N+W),
    "B": (N+E, S+E, S+W, N+W),
    "R": (N, E, S, W),
    "Q": (N, E, S, W, N+E, S+E, S+W, N+W),
    "K": (N, E, S, W, N+E, S+E, S+W, N+W)
}

# Mate bounds: king value set so king capture always beats material. Mate in N = MATE_UPPER - 2N.
MATE_LOWER = piece["K"] - 10 * piece["Q"]
MATE_UPPER = piece["K"] + 10 * piece["Q"]

# Constants for tuning search
QS = 35
QS_A = 150
EVAL_ROUGHNESS = 13

# minifier-hide start
opt_ranges = dict(
    QS = (0, 300),
    QS_A = (0, 300),
    EVAL_ROUGHNESS = (0, 50),
)
# minifier-hide end


###############################################################################
# Chess logic
###############################################################################



Move = namedtuple("Move", "i j prom")


class Position(namedtuple("Position", "board score wc bc ep kp")):
    """A state of a chess game
    board -- a 120 char representation of the board
    score -- the board evaluation
    wc -- the castling rights, [west/queen side, east/king side]
    bc -- the opponent castling rights, [west/king side, east/queen side]
    ep - the en passant square
    kp - the king passant square
    """

    def gen_moves(self):
        # Iterate rays per piece; rays break on capture or board edge.
        for i, p in enumerate(self.board):
            if not p.isupper():
                continue
            for d in directions[p]:
                for j in count(i + d, d):
                    q = self.board[j]
                    # Stay inside the board, and off friendly pieces
                    if q.isspace() or q.isupper():
                        break
                    # Pawn move, double move and capture
                    if p == "P":
                        if d in (N, N + N) and q != ".": break
                        if d == N + N and (i < A1 + N or self.board[i + N] != "."): break
                        if (
                            d in (N + W, N + E)
                            and q == "."
                            and j not in (self.ep, self.kp, self.kp - 1, self.kp + 1)
                            #and j != self.ep and abs(j - self.kp) >= 2
                        ):
                            break
                        # If we move to the last row, we can be anything
                        if A8 <= j <= H8:
                            for prom in "NBRQ":
                                yield Move(i, j, prom)
                            break
                    # Move it
                    yield Move(i, j, "")
                    # Stop crawlers from sliding, and sliding after captures
                    if p in "PNK" or q.islower():
                        break
                    # Castling, by sliding the rook next to the king
                    if i == A1 and self.board[j + E] == "K" and self.wc[0]:
                        yield Move(j + E, j + W, "")
                    if i == H1 and self.board[j + W] == "K" and self.wc[1]:
                        yield Move(j + W, j + E, "")

    def rotate(self, nullmove=False):
        """Rotates the board, preserving enpassant, unless nullmove"""
        return Position(
            self.board[::-1].swapcase(), -self.score, self.bc, self.wc,
            119 - self.ep if self.ep and not nullmove else 0,
            119 - self.kp if self.kp and not nullmove else 0,
        )

    def move(self, move):
        i, j, prom = move
        p, q = self.board[i], self.board[j]
        put = lambda board, i, p: board[:i] + p + board[i + 1 :]
        # Copy variables and reset ep and kp
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        score = self.score + self.value(move)
        # Actual move
        board = put(board, j, board[i])
        board = put(board, i, ".")
        # Castling rights, we move the rook or capture the opponent's
        if i == A1: wc = (False, wc[1])
        if i == H1: wc = (wc[0], False)
        if j == A8: bc = (bc[0], False)
        if j == H8: bc = (False, bc[1])
        # Castling
        if p == "K":
            wc = (False, False)
            if abs(j - i) == 2:
                kp = (i + j) // 2
                board = put(board, A1 if j < i else H1, ".")
                board = put(board, kp, "R")
        # Pawn promotion, double move and en passant capture
        if p == "P":
            if A8 <= j <= H8:
                board = put(board, j, prom)
            if j - i == 2 * N:
                ep = i + N
            if j == self.ep:
                board = put(board, j + S, ".")
        # We rotate the returned position, so it's ready for the next player
        return Position(board, score, wc, bc, ep, kp).rotate()

    def value(self, move):
        i, j, prom = move
        p, q = self.board[i], self.board[j]
        # Actual move
        score = pst[p][j] - pst[p][i]
        # Capture
        if q.islower():
            score += pst[q.upper()][119 - j]
        # Castling check detection
        if abs(j - self.kp) < 2:
            score += pst["K"][119 - j]
        # Castling
        if p == "K" and abs(i - j) == 2:
            score += pst["R"][(i + j) // 2]
            score -= pst["R"][A1 if j < i else H1]
        # Special pawn stuff
        if p == "P":
            if A8 <= j <= H8:
                score += pst[prom or "Q"][j] - pst["P"][j]
            if j == self.ep:
                score += pst["P"][119 - (j + S)]
            # Passed pawn bonus: no enemy pawns on same or adjacent files ahead
            fil = (j - A1) % 10
            if not any(self.board[s] == 'p' for f in (fil-1, fil, fil+1)
                       for s in range(j + N, A8 - 1, N) if 1 <= f <= 8):
                score += 20 + (A1 - j) // 10 * 8  # bonus grows as pawn advances
        # Bishop pair bonus: reward keeping both bishops
        if p == "B" and self.board.count("B") >= 2:
            score += 30
        # Rook on open / half-open file bonus
        if p == "R":
            fil = (j - A1) % 10
            file_squares = [self.board[A1 - r * 10 + fil] for r in range(0, 8)]
            has_own_pawn = 'P' in file_squares
            has_opp_pawn = 'p' in file_squares
            if not has_own_pawn and not has_opp_pawn:
                score += 20   # fully open file
            elif not has_own_pawn:
                score += 10   # half-open file
        # Mobility: count reachable squares from destination (sliders only).
        # Rewards active pieces on open diagonals/files without expensive search.
        if p in 'BRQ':
            mobility = sum(1 for d in directions[p] for sq in
                takewhile(lambda s: not self.board[s].isspace() and
                          not self.board[s].isupper(), count(j + d, d)))
            score += mobility  # ~1-14 squares; gentle nudge toward active posts
        # King safety / endgame centralisation
        if p == "K":
            major = sum(1 for c in self.board if c in "RBNQ")
            if major < 4:  # endgame: king marches to center
                rank, fil = divmod(j - A1, 10) if j >= A1 else (0, 0)
                score += (3 - abs(3 - fil)) + (3 - abs(3 + rank))
            else:  # middlegame: reward pawn shield (pawns on rank ahead of king)
                score += 15 * sum(1 for d in (N+W, N, N+E) if self.board[j + d] == 'P')
        return score


    def see(self, move):
        """Static Exchange Evaluation: estimate net material gain of a capture.
        Returns gain - cheapest_defender; negative means we lose the exchange."""
        i, j, _ = move
        p, q = self.board[i], self.board[j]
        if not q.islower(): return 0  # not a capture
        gain = piece.get(q.upper(), 0)  # what we capture
        # Find cheapest attacker the opponent has on square j after our move
        min_def = min((piece.get(c, 0) for c in self.rotate().board if c.isupper()), default=0)
        return gain - min_def  # net gain; negative = losing exchange


###############################################################################
# Search logic
###############################################################################

# lower <= s(pos) <= upper
Entry = namedtuple("Entry", "lower upper")


class Searcher:
    def __init__(self):
        self.tp_score = {}
        self.tp_move = {}
        self.counter_move = {}  # refutation table: prev_move -> best response
        self.hist_score = {}    # history heuristic: (piece, to_sq) -> cutoff count
        # hist_score uses depth^2 weighting so deep cutoffs outweigh shallow ones
        self.history = set()
        self.nodes = 0

    def bound(self, pos, gamma, depth, can_null=True):
        """Return r where r<gamma if s*<gamma (upper bound) else r>=gamma (lower bound)."""
        self.nodes += 1

        # Depth <= 0: quiescent search (captures only); clamp so TT keys stay consistent.
        depth = max(depth, 0)

        # King-capture engine: if our king is gone, we've already lost.
        if pos.score <= -MATE_LOWER:
            return -MATE_UPPER

        # Transposition table: if we've searched this node before at sufficient depth, reuse.
        # Entry stores (lower, upper) bounds; skip search if they already bracket gamma.
        entry = self.tp_score.get((pos, depth, can_null), Entry(-MATE_UPPER, MATE_UPPER))
        if entry.lower >= gamma: return entry.lower
        if entry.upper < gamma: return entry.upper

        # Avoid repetitions (skip at root and QSearch to preserve futility pruning).
        # A repeated position is scored 0 (draw) to discourage loops.
        if can_null and depth > 0 and pos in self.history:
            return 0

        # Move generator (lazy): define order here, compute only as needed.
        def moves():
            # Null move: pass the turn to the opponent at reduced depth.
            # Skip if position is unbalanced (zugzwang risk) or we're in endgame.
            if depth > 2 and can_null and abs(pos.score) < 500:
                R = 3 + depth // 4  # staged reduction: deeper search = more aggressive null
                yield None, -self.bound(pos.rotate(nullmove=True), 1 - gamma, depth - R)

            # QSearch stand-pat: we can always choose not to capture.
            if depth == 0:
                yield None, pos.score
            # Razoring: at depth 1, if static eval is far below gamma, go straight to QSearch
            if depth == 1 and pos.score + piece["R"] < gamma:
                yield None, self.bound(pos, gamma, 0)

            # Look for the strongest ove from last time, the hash-move.
            killer = self.tp_move.get(pos)

            # IID: no hash move? Run a shallower search to populate tp_move first.
            # Without a hash move, move ordering is random — IID fixes that cheaply.
            # Trigger only at depth > 3 so IID itself gets a useful result.
            if not killer and depth > 3:
                self.bound(pos, gamma, depth - 2, can_null=False)
                killer = self.tp_move.get(pos)

            # Quiescent search threshold: only consider captures/promotions at depth 0.
            val_lower = QS - depth * QS_A

            # Play killer only if it's still legal in this position (piece must still be there).
            if killer and pos.board[killer.i].isupper() and pos.value(killer) >= val_lower:
                yield killer, -self.bound(pos.move(killer), 1 - gamma, depth - 1)
            # Counter-move heuristic: move that refuted opponent's last move.
            # Only apply at depth >= 2 to avoid noise in leaf/QSearch nodes.
            counter = self.counter_move.get(self.tp_move.get(pos.rotate()))
            if depth >= 2 and counter and counter != killer \
                    and pos.board[counter.i].isupper() \
                    and pos.value(counter) >= val_lower:
                yield counter, -self.bound(pos.move(counter), 1 - gamma, depth - 1)

            # Main move loop: value() + history score, best first
            def move_key(m): return pos.value(m) + (
                self.hist_score.get((pos.board[m.i], m.j), 0)
                if pos.board[m.i].isupper() else 0)
            for move_num, (val, move) in enumerate(sorted(((move_key(m), m) for m in pos.gen_moves()), reverse=True)):
                val = pos.value(move)  # use raw value for pruning thresholds
                # Quiescent search: skip quiet moves below threshold; delta pruning for QS
                if val < val_lower:
                    break

                # Delta pruning: skip if even best gain can't reach gamma
                if depth == 0 and pos.score + val + piece["Q"] < gamma:
                    break
                # SEE: skip captures that lose material in QSearch
                if depth == 0 and pos.board[move.j].islower() and pos.see(move) < 0:
                    continue

                # Futility pruning: scale margin by depth so shallow nodes prune more.
                futility_margin = piece["R"] * depth  # depth 1=563, depth 2=1126
                if depth <= 2 and pos.score + futility_margin < gamma and val < MATE_LOWER:
                    yield move, pos.score + val
                    break

                # Search extensions: +1 ply for promotions and moves into check.
                ext = 1 if move.prom or abs(val) > piece["R"] else 0
                # LMR: reduce depth for quiet late moves (val<0); engine re-searches if needed.
                lmr = 1 if depth >= 3 and move_num >= 3 and val < 0 and not ext else 0
                yield move, -self.bound(pos.move(move), 1 - gamma, depth - 1 + ext - lmr)

        # Run moves; 'best' starts at -MATE_UPPER so any legal move beats it.
        best = -MATE_UPPER
        for move, score in moves():
            best = max(best, score)
            if best >= gamma:
                # Save the move for pv construction and killer heuristic
                if move is not None:
                    self.tp_move[pos] = move
                    self.counter_move[self.tp_move.get(pos.rotate())] = move
                    if pos.board[move.j] == '.' and pos.board[move.i].isupper():  # quiet cutoff
                        key = (pos.board[move.i], move.j)
                        self.hist_score[key] = self.hist_score.get(key, 0) + depth * depth
                break

        # Stalemate fix: bound() returns MATE_UPPER when king is capturable,
        # so we can detect mate vs stalemate by checking for check below.
        # At low depths, pruning may cause false mate reports; deeper search corrects them.

        # Distinguish mate from stalemate when no moves were found.
        # Skip at depth==0 (too expensive) and shallow (pruning causes false positives).
        # The null-move TT entry usually covers this call for free.
        if depth > 2 and best == -MATE_UPPER:
            flipped = pos.rotate(nullmove=True)
            in_check = self.bound(flipped, MATE_UPPER, 0) == MATE_UPPER
            best = -MATE_LOWER if in_check else 0

        # Update transposition table bounds
        if best >= gamma: self.tp_score[pos, depth, can_null] = Entry(best, entry.upper)
        if best < gamma:  self.tp_score[pos, depth, can_null] = Entry(entry.lower, best)

        return best

    def search(self, history):
        """Iterative deepening with aspiration windows. Bound ply to avoid recursion limit."""
        self.nodes = 0; self.history = set(history); self.tp_score.clear()
        score = 0
        for depth in range(1, 1000):
            # Aspiration window: search ±delta around last depth's score.
            # On a miss (score outside window), widen that side and retry.
            delta = EVAL_ROUGHNESS + depth * 3
            lower, upper = score - delta, score + delta
            while True:
                gamma = (lower + upper + 1) // 2
                score = self.bound(history[-1], gamma, depth, can_null=False)
                yield depth, gamma, score, self.tp_move.get(history[-1])
                if score >= gamma: lower = score  # fail-high: raise floor
                if score < gamma:  upper = score  # fail-low: drop ceiling
                if lower >= upper - EVAL_ROUGHNESS: break  # window closed
                # Widen exponentially on miss; clamp to full window near mate
                delta = min(delta * 2, MATE_LOWER)
                lower = max(lower, -MATE_LOWER)
                upper = min(upper,  MATE_LOWER)


# UCI interface
# parse/render convert between algebraic notation (e4) and 120-board index (91).
def parse(c):
    fil, rank = ord(c[0]) - ord("a"), int(c[1]) - 1
    return A1 + fil - 10 * rank


def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord("a")) + str(-rank + 1)

import sys

def parse_fen(fen):
    """Parse a FEN string into a Position. Supports full FEN or 'startpos'."""
    rows, turn, castling, ep_sq = fen.split()[:4]
    # Build the 120-char board
    board = "         \n" * 2
    for row in rows.split("/"):
        line = " "
        for c in row:
            line += "." * int(c) if c.isdigit() else c
        board += line.ljust(9) + "\n"
    board += "         \n" * 2
    # Castling rights: wc=(queenside, kingside), bc=(queenside, kingside)
    wc = ("Q" in castling, "K" in castling)
    bc = ("q" in castling, "k" in castling)
    ep = parse(ep_sq) if ep_sq != "-" else 0
    pos = Position(board, 0, wc, bc, ep, 0)
    # Rotate if it's black's turn (sunfish always thinks from white's POV)
    return pos if turn == "w" else pos.rotate()

def parse_moves(pos, moves_list, start_turn):
    """Apply a list of UCI move strings to a position, tracking history."""
    hist = [pos]
    for ply, mv in enumerate(moves_list):
        i, j = parse(mv[:2]), parse(mv[2:4])
        prom = mv[4:].upper() if len(mv) > 4 else ""
        # Rotate coordinates for black's moves
        if (start_turn == "w" and ply % 2 == 1) or (start_turn == "b" and ply % 2 == 0):
            i, j = 119 - i, 119 - j
        hist.append(hist[-1].move(Move(i, j, prom)))
    return hist

def go(hist, args, start_turn="w"):
    """Handle the UCI 'go' command. Parse all time control variants robustly."""
    # Build a key->value dict from the go arguments
    params = {}
    it = iter(args[1:])
    for token in it:
        try:
            params[token] = int(next(it))
        except StopIteration:
            params[token] = None  # flags like 'infinite', 'ponder'
        except ValueError:
            pass

    # Determine side to move.
    # If start_turn='w': even hist length after moves = black to move.
    # If start_turn='b': the position was already rotated, so parity is inverted.
    parity = len(hist) % 2  # 0=white's turn in hist, 1=black's turn
    black_to_move = (parity == 0) if start_turn == 'w' else (parity == 1)

    if "movetime" in params and params["movetime"] is not None:
        # Fixed time per move
        think = params["movetime"] / 1000.0
    elif "infinite" in params or ("wtime" not in params and "btime" not in params):
        # Analysis mode: search until 'stop' (we just use a very long time)
        think = 1e9
    else:
        wtime = params.get("wtime", 60000) / 1000.0
        btime = params.get("btime", 60000) / 1000.0
        winc  = params.get("winc",  0)     / 1000.0
        binc  = params.get("binc",  0)     / 1000.0
        if black_to_move:
            wtime, winc = btime, binc
        movestogo = params.get("movestogo", max(2, 50 - len(hist) // 2))
        movestogo = max(2, movestogo)
        think = min(wtime / movestogo + winc * 0.8, wtime / 2 - 1)
        think = max(think, 0.1)  # always think at least 100ms

    start = time.time()
    move_str = None
    for depth, gamma, score, move in Searcher().search(hist):
        if score >= gamma and move:
            i, j = move.i, move.j
            if black_to_move:
                i, j = 119 - i, 119 - j
            move_str = render(i) + render(j) + move.prom.lower()
            print("info depth", depth, "score cp", score, "pv", move_str, flush=True)
        if move_str and time.time() - start > think * 0.9:
            break

    print("bestmove", move_str or "(none)", flush=True)

# ── Main UCI loop ─────────────────────────────────────────────────────────────
hist = [Position(initial, 0, (True, True), (True, True), 0, 0)]
start_turn = "w"

for line in sys.stdin:
    args = line.split()
    if not args:
        continue
    cmd = args[0]

    if cmd == "uci":
        print("id name Tetrafish", flush=True)
        print("id author Gokul Chandar", flush=True)
        print("option name Hash type spin default 16 min 1 max 512", flush=True)
        print("uciok", flush=True)

    elif cmd == "isready":
        print("readyok", flush=True)

    elif cmd == "ucinewgame":
        hist = [Position(initial, 0, (True, True), (True, True), 0, 0)]
        start_turn = "w"

    elif cmd == "position":
        if args[1] == "startpos":
            hist = [Position(initial, 0, (True, True), (True, True), 0, 0)]
            start_turn = "w"
            moves = args[3:] if len(args) > 3 and args[2] == "moves" else []
        elif args[1] == "fen":
            fen_end = args.index("moves") if "moves" in args else len(args)
            fen_str = " ".join(args[2:fen_end])
            start_turn = args[3] if len(args) > 3 else "w"
            base = parse_fen(fen_str)
            hist = [base]
            moves = args[fen_end + 1:] if "moves" in args else []
        else:
            continue
        hist = parse_moves(hist[0], moves, start_turn)

    elif cmd == "go":
        go(hist, args, start_turn)

    elif cmd in ("stop", "quit"):
        break
