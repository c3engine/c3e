"""minnow_engine.py -- golfed core (movegen + eval + search), no FEN/CLI/perft.
Moves are plain tuples (frm, to, promo, flag) so no Move class is needed.
See minnow_tools.py for FEN parsing, perft, and a text CLI built on top."""
import random, time

P, N, B, R, Q, K = range(1, 7)
PVAL = {P: 100, N: 320, B: 330, R: 500, Q: 900, K: 0}
PHW = {P: 0, N: 1, B: 1, R: 2, Q: 4, K: 0}
MAXP = 24

def sq(r, c): return r * 8 + c
def on(r, c): return 0 <= r < 8 and 0 <= c < 8
def rays(dirs):
    out = [[] for _ in range(64)]
    for r in range(8):
        for c in range(8):
            for dr, dc in dirs:
                ray, rr, cc = [], r + dr, c + dc
                while on(rr, cc):
                    ray.append(sq(rr, cc)); rr += dr; cc += dc
                if ray: out[sq(r, c)].append(ray)
    return out

NDIR = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
KDIR = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
BDIR = [(-1,-1),(-1,1),(1,-1),(1,1)]
RDIR = [(-1,0),(1,0),(0,-1),(0,1)]
NMOV = [[sq(r+dr,c+dc) for dr,dc in NDIR if on(r+dr,c+dc)] for r in range(8) for c in range(8)]
KMOV = [[sq(r+dr,c+dc) for dr,dc in KDIR if on(r+dr,c+dc)] for r in range(8) for c in range(8)]
BRAY, RRAY = rays(BDIR), rays(RDIR)
QRAY = [BRAY[s] + RRAY[s] for s in range(64)]
SRAY = {B: BRAY, R: RRAY, Q: QRAY}
PPUSH = [sq(r-1,c) if on(r-1,c) else None for r in range(8) for c in range(8)]
PDBL = [sq(r-2,c) if r==6 and on(r-2,c) else None for r in range(8) for c in range(8)]
PCAP = [[sq(r-1,c+dc) for dc in (-1,1) if on(r-1,c+dc)] for r in range(8) for c in range(8)]
A1,H1,A8,H8 = sq(7,0),sq(7,7),sq(0,0),sq(0,7)
BACK = [R,N,B,Q,K,B,N,R]
START = [0]*64
for c in range(8):
    START[sq(0,c)], START[sq(1,c)], START[sq(6,c)], START[sq(7,c)] = -BACK[c], -P, P, BACK[c]

def attacked(bd, s, by):
    """Is square s attacked by a piece of sign `by` (+1 'mine', -1 'theirs')?"""
    r, c = divmod(s, 8)
    pr = r + 1 if by > 0 else r - 1
    for dc in (-1, 1):
        if on(pr, c+dc) and bd[sq(pr,c+dc)] == by*P: return True
    if any(bd[f] == by*N for f in NMOV[s]): return True
    if any(bd[f] == by*K for f in KMOV[s]): return True
    for piece, rs in ((B,BRAY),(R,RRAY)):
        for ray in rs[s]:
            for f in ray:
                v = bd[f]
                if v == 0: continue
                if v == by*piece or v == by*Q: return True
                break
    return False

class Pos:
    """Always from the mover's perspective: 'mine' pieces are positive and
    push toward row 0. castle = (myK, myQ, theirK, theirQ)."""
    __slots__ = ("bd", "mine", "theirs", "castle", "ep")
    def __init__(self, bd, mine, theirs, castle, ep):
        self.bd, self.mine, self.theirs, self.castle, self.ep = bd, mine, theirs, castle, ep

    @staticmethod
    def start():
        m = [s for s in range(64) if START[s] > 0]
        t = [s for s in range(64) if START[s] < 0]
        return Pos(START[:], m, t, (1,1,1,1), None)

    def king(self, mine=True):
        tgt, lst = (K, self.mine) if mine else (-K, self.theirs)
        return next((s for s in lst if self.bd[s] == tgt), None)

    def in_check(self):
        ks = self.king()
        return ks is not None and attacked(self.bd, ks, -1)

    def gen(self, chk=None):
        bd, mv = self.bd, []
        for f in self.mine:
            p = bd[f]
            if p == P:
                t = PPUSH[f]
                if t is not None and bd[t] == 0:
                    self._padd(mv, f, t)
                    t2 = PDBL[f]
                    if t2 is not None and bd[t2] == 0: mv.append((f, t2, 0, 0))
                for t in PCAP[f]:
                    if bd[t] < 0 or t == self.ep:
                        self._padd(mv, f, t, t == self.ep and bd[t] == 0)
            elif p == N:
                mv += [(f, t, 0, 0) for t in NMOV[f] if bd[t] <= 0]
            elif p == K:
                mv += [(f, t, 0, 0) for t in KMOV[f] if bd[t] <= 0]
                if chk is None: chk = self.in_check()
                if not chk: self._castles(mv, f)
            else:
                for ray in SRAY[p][f]:
                    for t in ray:
                        q = bd[t]
                        if q > 0: break
                        mv.append((f, t, 0, 0))
                        if q < 0: break
        return mv

    def _padd(self, mv, f, t, ep=False):
        if t < 8: mv += [(f, t, pr, 0) for pr in (Q, R, B, N)]
        else: mv.append((f, t, 0, 1 if ep else 0))

    def _castles(self, mv, k):
        mk, mq, _, _ = self.castle
        bd = self.bd
        if mk and bd[k+1]==0 and bd[k+2]==0 and bd[k+3]==R:
            if not attacked(bd,k+1,-1) and not attacked(bd,k+2,-1): mv.append((k, k+2, 0, 2))
        if mq and bd[k-1]==0 and bd[k-2]==0 and bd[k-3]==0 and bd[k-4]==R:
            if not attacked(bd,k-1,-1) and not attacked(bd,k-2,-1): mv.append((k, k-2, 0, 2))

    def _mirror(self, bd, mine, theirs, castle, ep):
        flip = [0]*64
        for s in mine: flip[s^56] = -bd[s]
        for s in theirs: flip[s^56] = -bd[s]
        return Pos(flip, [s^56 for s in theirs], [s^56 for s in mine], castle, ep^56 if ep is not None else None)

    def null(self):
        mk,mq,tk,tq = self.castle
        return self._mirror(self.bd, self.mine, self.theirs, (tk,tq,mk,mq), None)

    def move(self, mv):
        f, t, promo, flag = mv
        bd = self.bd[:]
        mine, theirs = list(self.mine), list(self.theirs)
        p = bd[f]
        mine.remove(f)
        if bd[t] < 0 and t in theirs: theirs.remove(t)
        bd[f] = 0
        bd[t] = promo if promo else p
        mine.append(t)
        if flag == 1:  # en passant
            cap = t + 8
            bd[cap] = 0
            if cap in theirs: theirs.remove(cap)
        mk,mq,tk,tq = self.castle
        if flag == 2:  # castle
            rf, rt = (f+3, f+1) if t == f+2 else (f-4, f-1)
            bd[rf], bd[rt] = 0, R
            mine.remove(rf); mine.append(rt)
        if p == K: mk = mq = 0
        if f == A1: mq = 0
        if f == H1: mk = 0
        if t == A8: tq = 0
        if t == H8: tk = 0
        new_ep = f - 8 if p == P and t == f - 16 else None
        return self._mirror(bd, mine, theirs, (tk,tq,mk,mq), new_ep)

    def legal(self):
        out = []
        for mv in self.gen():
            nxt = self.move(mv)
            if not illegal(nxt): out.append(mv)
        return out

def illegal(pos):
    for s in pos.theirs:
        if pos.bd[s] == -K: return attacked(pos.bd, s, 1)
    return True

def big_piece(pos):
    return any(pos.bd[s] in (N,B,R,Q) for s in pos.mine)

# ---------------- eval: material + tapered PST, generated from formulas ----------------
def cent(r, c): return (3.5-abs(r-3.5)) + (3.5-abs(c-3.5))
def tbl(fn): return [round(fn(*divmod(s,8))) for s in range(64)]
MG = {P: tbl(lambda r,c:(7-r)*6+(3.5-abs(c-3.5))*3), N: tbl(lambda r,c:cent(r,c)*8-16),
      B: tbl(lambda r,c:cent(r,c)*5-8), R: tbl(lambda r,c:(3.5-abs(c-3.5))*3+(12 if r==1 else 0)),
      Q: tbl(lambda r,c:cent(r,c)*2), K: tbl(lambda r,c:r*8-cent(r,c)*6)}
EG = {P: tbl(lambda r,c:(7-r)*12), N: tbl(lambda r,c:cent(r,c)*6-12), B: tbl(lambda r,c:cent(r,c)*5-8),
      R: tbl(lambda r,c:(3.5-abs(c-3.5))*2), Q: tbl(lambda r,c:cent(r,c)*4), K: tbl(lambda r,c:cent(r,c)*12)}

def evaluate(pos):
    bd = pos.bd
    mat = mg = eg = ph = 0
    for s in pos.mine:
        p = bd[s]; ph += PHW[p]; mat += PVAL[p]; mg += MG[p][s]; eg += EG[p][s]
    for s in pos.theirs:
        p = -bd[s]; fs = s^56; ph += PHW[p]; mat -= PVAL[p]; mg -= MG[p][fs]; eg -= EG[p][fs]
    ph = min(ph, MAXP)
    return mat + (mg*ph + eg*(MAXP-ph)) // MAXP

# ---------------- search: alpha-beta negamax, TT, null-move, MVV-LVA/killers ----------------
MATE, INF = 100000, 10**9
EXACT, LOWER, UPPER = 0, 1, 2
random.seed(2026)
ZM = [[random.getrandbits(64) for _ in range(64)] for _ in range(7)]
ZT = [[random.getrandbits(64) for _ in range(64)] for _ in range(7)]
ZE = [random.getrandbits(64) for _ in range(64)]
ZC = [random.getrandbits(64) for _ in range(16)]

def zkey(pos):
    h, bd = 0, pos.bd
    for s in pos.mine: h ^= ZM[bd[s]][s]
    for s in pos.theirs: h ^= ZT[-bd[s]][s]
    if pos.ep is not None: h ^= ZE[pos.ep]
    mk,mq,tk,tq = pos.castle
    h ^= ZC[mk | mq<<1 | tk<<2 | tq<<3]
    return h

class Engine:
    def __init__(self, tt_size=400_000):
        self.tt, self.tt_size = {}, tt_size
        self.killers = [[None,None] for _ in range(64)]
        self.nodes = self.t0 = self.tlimit = 0
        self.stop = False

    def order(self, pos, moves, ply, ttmv):
        def k(mv):
            if mv == ttmv: return 3, 0
            v = pos.bd[mv[1]]
            if v: return 2, PVAL[abs(v)]*10 - PVAL[abs(pos.bd[mv[0]])]
            if mv in self.killers[ply]: return 1, 0
            return 0, 0
        moves.sort(key=k, reverse=True)
        return moves

    def quiesce(self, pos, alpha, beta):
        self.nodes += 1
        stand = evaluate(pos)
        if stand >= beta: return beta
        alpha = max(alpha, stand)
        for mv in pos.gen():
            if pos.bd[mv[1]] == 0 and mv[2] == 0: continue
            nxt = pos.move(mv)
            if illegal(nxt): continue
            score = -self.quiesce(nxt, -beta, -alpha)
            if score >= beta: return beta
            alpha = max(alpha, score)
        return alpha

    def negamax(self, pos, depth, alpha, beta, ply, can_null=True):
        self.nodes += 1
        if self.nodes % 2048 == 0 and time.time() - self.t0 > self.tlimit: self.stop = True
        if self.stop: return 0
        chk = pos.in_check()
        if chk: depth += 1
        if depth <= 0: return self.quiesce(pos, alpha, beta)
        key = zkey(pos)
        entry = self.tt.get(key)
        ttmv = None
        if entry is not None:
            ed, es, ef, ttmv = entry
            if ed >= depth:
                if ef == EXACT: return es
                if ef == LOWER: alpha = max(alpha, es)
                elif ef == UPPER: beta = min(beta, es)
                if alpha >= beta: return es
        if can_null and depth >= 3 and not chk and big_piece(pos):
            score = -self.negamax(pos.null(), depth-3, -beta, -beta+1, ply+1, False)
            if self.stop: return 0
            if score >= beta: return beta
        moves = self.order(pos, pos.gen(chk), ply, ttmv)
        best, bestmv, flag, legal = -INF, None, UPPER, 0
        for mv in moves:
            nxt = pos.move(mv)
            if illegal(nxt): continue
            legal += 1
            score = -self.negamax(nxt, depth-1, -beta, -alpha, ply+1)
            if self.stop: return 0
            if score > best: best, bestmv = score, mv
            if best > alpha: alpha, flag = best, EXACT
            if alpha >= beta:
                flag = LOWER
                if pos.bd[mv[1]] == 0 and mv[2] == 0:
                    self.killers[ply] = [mv, self.killers[ply][0]]
                break
        if legal == 0: return -MATE+ply if chk else 0
        if len(self.tt) < self.tt_size: self.tt[key] = (depth, best, flag, bestmv)
        return best

    def search(self, pos, max_depth=99, time_limit=2.0):
        self.nodes, self.t0, self.tlimit, self.stop = 0, time.time(), time_limit, False
        best = None
        for depth in range(1, max_depth+1):
            score = self.negamax(pos, depth, -INF, INF, 0)
            if self.stop and depth > 1: break
            e = self.tt.get(zkey(pos))
            if e is not None and e[3] is not None: best = e[3]
            elapsed = time.time() - self.t0
            yield depth, score, best, self.nodes, elapsed
            if elapsed > time_limit: break
