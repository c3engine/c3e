"""minnow_tools.py -- FEN parsing, perft, and a text CLI for minnow_engine.py.
Kept separate from the engine on purpose: Sunfish's own "111 lines" figure
also excludes its UCI/CLI wrapper, so this is the fair comparison point."""
import sys, time
from minnow_engine import Pos, Engine, P, N, B, R, Q, K, illegal

LETTER = {"p": P, "n": N, "b": B, "r": R, "q": Q, "k": K}
PIECE_CH = {0: ".", P: "P", N: "N", B: "B", R: "R", Q: "Q", K: "K"}


def from_fen(fen):
    board_f, turn, castling, ep_f = fen.split()[:4]
    bd = [0] * 64
    for r, row in enumerate(board_f.split("/")):
        c = 0
        for ch in row:
            if ch.isdigit():
                c += int(ch)
            else:
                bd[r * 8 + c] = (1 if ch.isupper() else -1) * LETTER[ch.lower()]
                c += 1
    wk, wq, bk, bq = "K" in castling, "Q" in castling, "k" in castling, "q" in castling
    ep = None
    if ep_f != "-":
        ep = (8 - int(ep_f[1])) * 8 + (ord(ep_f[0]) - ord("a"))
    if turn == "w":
        mine = [s for s in range(64) if bd[s] > 0]
        theirs = [s for s in range(64) if bd[s] < 0]
        return Pos(bd, mine, theirs, (wk, wq, bk, bq), ep)
    flip = [0] * 64
    for s in range(64):
        if bd[s]:
            flip[s ^ 56] = -bd[s]
    mine = [s for s in range(64) if flip[s] > 0]
    theirs = [s for s in range(64) if flip[s] < 0]
    return Pos(flip, mine, theirs, (bk, bq, wk, wq), (ep ^ 56) if ep is not None else None)


def algebraic(mv, flip=False):
    f, t, promo, _ = mv
    if flip:
        f, t = f ^ 56, t ^ 56
    s1 = "abcdefgh"[f % 8] + str(8 - f // 8)
    s2 = "abcdefgh"[t % 8] + str(8 - t // 8)
    return s1 + s2 + (PIECE_CH[promo].lower() if promo else "")


def perft(pos, depth):
    if depth == 0:
        return 1
    return sum(perft(pos.move(mv), depth - 1) for mv in pos.legal())


def run_perft_suite():
    cases = [
        ("startpos", Pos.start(), {1: 20, 2: 400, 3: 8902, 4: 197281}),
        ("kiwipete", from_fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
         {1: 48, 2: 2039, 3: 97862}),
        ("en passant edge case", from_fen("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"),
         {1: 14, 2: 191, 3: 2812, 4: 43238}),
        ("castling/promotion", from_fen("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"),
         {1: 6, 2: 264, 3: 9467}),
    ]
    ok = True
    for name, pos, known in cases:
        print(f"-- {name} --")
        for d, expected in known.items():
            t0 = time.time()
            n = perft(pos, d)
            status = "OK" if n == expected else "MISMATCH"
            ok &= n == expected
            print(f"  perft({d}) = {n:>8} (expected {expected:>8})  {status}  {time.time()-t0:.2f}s")
    print("ALL OK" if ok else "FAILURES PRESENT")


def play():
    pos = Pos.start()
    eng = Engine()
    ply = 0
    print("minnow -- type a move like e2e4, or 'quit'.")
    while True:
        legal = pos.legal()
        if not legal:
            print("Checkmate!" if pos.in_check() else "Stalemate.")
            return
        flip = ply % 2 == 1
        if ply % 2 == 0:
            user = input("your move: ").strip()
            if user in ("quit", "exit"):
                return
            mv = next((m for m in legal if algebraic(m, flip) == user), None)
            if mv is None:
                print("not a legal move, try again")
                continue
        else:
            best, score, nodes, elapsed = None, 0, 0, 0
            for d, score, move, nodes, elapsed in eng.search(pos, max_depth=6, time_limit=2.0):
                best = move
            mv = best
            print(f"minnow plays {algebraic(mv, flip)}  (score {score}, {nodes} nodes, {elapsed:.1f}s)")
        pos = pos.move(mv)
        ply += 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "perft":
        run_perft_suite()
    elif len(sys.argv) > 1 and sys.argv[1] == "play":
        play()
    else:
        print(__doc__)
