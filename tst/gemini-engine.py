import sys

# 1. Setup: Board padding, Piece Values, and Transposition Cache
B = list("##########" + "".join(f"#{'rnbqkbnr' if r==0 else 'pppppppp' if r==1 else 'PPPPPPPP' if r==6 else 'RNBQKBNR' if r==7 else '........'}#" for r in range(8)) + "##########")
V = {'P':100, 'N':320, 'B':330, 'R':500, 'Q':900, 'K':20000, '.':0}
D = {'N':[-21,-19,-12,-8,8,12,19,21], 'B':[-11,-9,9,11], 'R':[-10,-1,1,10], 'Q':[-11,-10,-9,-1,1,9,10,11], 'K':[-11,-10,-9,-1,1,9,10,11]}
TT = {}

# 2. Move Generator
def gen(b, side, ep, rights, castling=True):
    m = []
    for i, p in enumerate(b):
        if p in '#.' or (side == 1 and p.islower()) or (side == -1 and p.isupper()): continue
        if p.upper() == 'P':
            f = -10 if side == 1 else 10
            if b[i+f] == '.':
                m.append((i, i+f))
                if ((side == 1 and i//10 == 7) or (side == -1 and i//10 == 2)) and b[i+2*f] == '.': m.append((i, i+2*f))
            for c in [f-1, f+1]:
                if i+c == ep or (b[i+c] not in '#.' and ((side==1 and b[i+c].islower()) or (side==-1 and b[i+c].isupper()))): m.append((i, i+c))
        else:
            for d in D[p.upper()]:
                t = i + d
                while b[t] != '#':
                    if b[t] == '.': m.append((i, t))
                    elif (side == 1 and b[t].islower()) or (side == -1 and b[t].isupper()): m.append((i, t)); break
                    else: break
                    if p.upper() in 'NK': break
                    t += d
    if castling:
        atk = set(t for _, t in gen(b, -side, 0, "", False))
        if side == 1:
            if 'K' in rights and b[86]=='.' and b[87]=='.' and not ({85,86,87} & atk): m.append((85, 87))
            if 'Q' in rights and b[82]=='.' and b[83]=='.' and b[84]=='.' and not ({85,83,84} & atk): m.append((85, 83))
        else:
            if 'k' in rights and b[16]=='.' and b[17]=='.' and not ({15,16,17} & atk): m.append((15, 17))
            if 'q' in rights and b[12]=='.' and b[13]=='.' and b[14]=='.' and not ({15,13,14} & atk): m.append((15, 13))
    return m

# 3. Piece-Square Evaluation
def E(b, side):
    s = 0
    for i, p in enumerate(b):
        if p in '#.': continue
        sd = 1 if p.isupper() else -1
        r, f = i // 10, i % 10
        v = V[p.upper()] + (4 - abs(4.5 - r) + 4 - abs(4.5 - f)) * (3 if p.upper() in 'NB' else 0)
        if p.upper() == 'P': v += (8 - r if sd == 1 else r - 1) * 2
        if p.upper() == 'K': v += (abs(4.5 - f)) * 4 if r in [1, 8] else -5
        s += v * sd
    return s * side

# 4. Search with LMR and Null-Move Pruning
def search(b, depth, a, beta, side, ep, rights, null=True, pv=None):
    key = (tuple(b), side, ep, rights)
    if key in TT and TT[key][0] >= depth: return TT[key][1], TT[key][2]
    in_q = depth <= 0
    ev = E(b, side)
    if in_q:
        if ev >= beta: return beta, None
        a = max(a, ev)
        if depth < -3: return ev, None
    if not in_q and null and depth >= 3 and ev >= beta:
        v, _ = search(b, depth - 3, -beta, -beta + 1, -side, 0, rights, False)
        if -v >= beta: return beta, None
    moves = gen(b, side, ep, rights, not in_q)
    if in_q: moves = [m for m in moves if b[m[1]] != '.']
    if not moves: return (ev if in_q else -999999), None
    moves.sort(key=lambda m: (1000000 if m == pv else 0) + V[b[m[1]].upper()] * 10 - V[b[m[0]].upper()], reverse=True)
    best, bm = -999999, None
    for count, (f, t) in enumerate(moves):
        p = b[f]; nb = list(b); nb[t], nb[f] = nb[f], '.'
        if p.upper() == 'P' and t == ep: nb[t + (10 if side == 1 else -10)] = '.'
        if p.upper() == 'K' and abs(f - t) == 2:
            if t == 87: nb[86], nb[88] = nb[88], '.'
            elif t == 83: nb[84], nb[81] = nb[81], '.'
            elif t == 17: nb[16], nb[18] = nb[18], '.'
            elif t == 13: nb[14], nb[11] = nb[11], '.'
        if p.upper() == 'P' and t//10 in [1, 8]: nb[t] = 'Q' if side==1 else 'q'
        nr = "".join(c for c in rights if (c=='K' and f!=85 and t!=85 and f!=88 and t!=88) or (c=='Q' and f!=85 and t!=85 and f!=81 and t!=81) or (c=='k' and f!=15 and t!=15 and f!=18 and t!=18) or (c=='q' and f!=15 and t!=15 and f!=11 and t!=11))
        nep = (f + t) // 2 if p.upper() == 'P' and abs(f - t) == 20 else 0
        if not in_q and count >= 3 and depth >= 3 and b[t] == '.':
            val, _ = search(nb, depth - 2, -beta, -a, -side, nep, nr, null)
            if -val > a: val, _ = search(nb, depth - 1, -beta, -a, -side, nep, nr, null)
            else: val = -val
        else: val = -search(nb, depth - 1, -beta, -a, -side, nep, nr, null)[0]
        if val > best: best, bm = val, (f, t)
        a = max(a, best)
        if a >= beta: break
    TT[key] = (depth, best, bm)
    return best, bm

# 5. UCI Protocol Handler
def uci_handler():
    global B, ep, rights, side
    board = B
    while True:
        line = sys.stdin.readline()
        if not line: break
        cmd = line.strip().split()
        if not cmd: continue

        if cmd[0] == "uci":
            print("id name MyEngine\nid author Me\nuciok")
        elif cmd[0] == "isready":
            print("readyok")
        elif cmd[0] == "ucinewgame":
            B = list("##########" + "".join(f"#{'rnbqkbnr' if r==0 else 'pppppppp' if r==1 else 'PPPPPPPP' if r==6 else 'RNBQKBNR' if r==7 else '........'}#" for r in range(8)) + "##########")
        elif cmd[0] == "position":
            # Simple implementation: reset to startpos (add logic here to parse moves)
            side = 1
        elif cmd[0] == "go":
            move = None
            for d in range(1, 6): 
                _, move = search(B, d, -999999, 999999, side, ep, rights, pv=move)
            if move:
                f, t = move
                # Convert index back to UCI string (e.g., e2e4)
                print(f"bestmove {to_uci(f)}{to_uci(t)}")
        elif cmd[0] == "quit":
            break
        sys.stdout.flush()

def to_uci(idx):
    r, f = idx // 10, idx % 10
    return chr(f + 96) + str(8 - (r - 1))

if __name__ == "__main__":
    uci_handler()
