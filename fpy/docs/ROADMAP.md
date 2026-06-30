# FastPy — Roadmap 

Sprint-level tracking. Checked = done. Unchecked = active or upcoming.

---

## Phase 1 — FastPy Transpiler MVP ✅ COMPLETE

### Sprint 1 — Repo Setup & Documentation
- [x] Create `g-c-3/fastpy` repo
- [x] Write `README.md` with vision, Speed Contract, hardware intrinsics table
- [x] Write `CONTRIBUTING.md`
- [x] Write `CODE_OF_CONDUCT.md`
- [x] Create `g-c-3/fastpy-engine` repo
- [x] Write `fastpy-engine/README.md` (vision, 1B NPS target, 4-phase roadmap)
- [x] Write `fastpy-engine/LICENSE` (GPL v3)

### Sprint 2 — Core Modules
- [x] `core/parser.py` — ast visitor → IRModule (all IR nodes, ExpressionVisitor, StatementVisitor, ModuleVisitor)
- [x] `core/type_system.py` — TypeRegistry, TypeChecker, check_module()
- [x] `core/emitter.py` — CppWriter, CppEmitter, emit_module() with auto-intrinsics wiring
- [x] `core/intrinsics.py` — IntrinsicMapper, POPCNT pattern, TZCNT pattern, PATTERN_REGISTRY
- [x] `core/toolchain.py` — find_compiler(), compile_cpp(), CompileResult
- [x] `main.py` — CLI: build / check / emit / intrinsics subcommands

### Sprint 3 — Example & Validation
- [x] `examples/simple_engine.py` — FastPy-dialect chess engine, zero type errors, runs as Python
- [x] Fix `uint64 = int` bug (ground-truth table beats Python base type)
- [x] Fix TZCNT partial-fire bug (full inline pattern match)
- [x] Fix `IRCall.receiver` — preserve `bin(board)` for POPCNT matching

### Sprint 4 — Test Suite
- [x] `tests/conftest.py` — fixtures and `emit_from_source()` helper
- [x] `tests/test_parser.py` — 46 tests
- [x] `tests/test_type_system.py` — 38 tests
- [x] `tests/test_emitter.py` — 43 tests
- [x] `tests/test_intrinsics.py` — 28 tests
- [x] `pytest.ini` — testpaths + pythonpath
- [x] **155/155 tests passing in 1.82s**

### Sprint 5 — CI & Docs
- [x] `.github/workflows/ci.yml` — type check + smoke test + emit check on 3.11 & 3.12
- [x] CI green on first commit
- [x] `docs/` directory with PROJECT_CONTEXT, ARCHITECTURE, ROADMAP, DECISIONS, SESSION_LOG
- [x] **Add `python -m pytest tests/ -v` step to `ci.yml`**

---

## Phase 2 — Package & Engine Foundation

### Sprint 6 — Package Infrastructure
- [x] `core/__init__.py` — makes `core/` a proper Python package
- [x] `pyproject.toml` — `pip install fastpy` + `fastpy` CLI entry point
- [x] Update `ci.yml` to test `pip install -e .` as well

### Sprint 7 — FastPy-Engine Phase 1 Source
- [x] `fastpy-engine/engine.py` — first real engine source:
  - [x] `BoardState` struct (all 17 fields, starting positions)
  - [x] Bitboard utilities: `popcount`, `lsb`, `pop_lsb`, `north/south/east/west`
  - [x] White pawn move generation (single push, double push, captures, en passant)
  - [x] Knight move generation
  - [x] Alpha-beta search skeleton
  - [x] Material evaluation
  - [x] All using `uint64[218]` arrays — zero type errors required
- [x] `fastpy check engine.py` ;→ zero errors
- [x] `fastpy build engine.py --optimize O3` → compiles successfully

### Sprint 7.5 — Make/Unmake & Real Search
- [x] `BIT_ONE: Final[uint64] = 1` constant for correct 64-bit single-square masks
- [x] `make_move(board, move) -> BoardState` — value-copy semantics, handles captures, en passant, double-push EP square, promotions (queen/knight/bishop)
- [x] `alpha_beta()` wired up with real `make_move` recursion — no more static eval placeholder
- [x] Emitter: `_HOISTABLE_TYPES` guard — struct types not hoisted (invalid C++ zero-init)
- [x] Type checker: `param.field` writes exempt from first-use annotation (same as `self.field`)
- [x] `fastpy build engine.py --optimize=O3` → 662 lines C++, compiles clean ✅

### Sprint 8 — UCI Protocol
- [x] UCI loop in `engine.py`: `uci`, `isready`, `position startpos moves ...`, `go depth N`, `quit`
- [x] `bestmove` output
- [x] `fastpy-engine/tests/test_uci.py` — 21 tests, all passing
- [x] Test with Arena or Cutechess (fully compatible — `python engine.py`)

---

## Phase 3 — Complete Move Generation

- [x] Bishop move generation (diagonal rays)
- [x] Rook move generation (horizontal/vertical rays)
- [x] Queen = bishop | rook
- [x] King moves (all 8 directions, one square)
- [x] Castling (rights tracking, legal castling)
- [x] En passant capture
- [x] Check detection
- [x] Legal move filtering (king cannot move into check)
- [x] Perft(1)=20, Perft(2)=400, Perft(3)=8902, Perft(4)=197281
- [x] Perft(5) from starting position = 4,865,609 nodes ← correctness benchmark ✅ (0.25s compiled)

---

## Phase 4 — Search Improvements

- [x] Move ordering (MVV-LVA captures first, selection sort)
- [x] Quiescence search (stand-pat + capture search at leaf nodes)
- [x] Iterative deepening with time management (movetime, wtime/btime, infinite)
- [ ] Piece-Square Tables (PST) evaluation
- [ ] Null move pruning
- [ ] Transposition table (Zobrist hashing)
- [ ] Checkmate vs stalemate detection (return -INF for mate, 0 for stalemate)

---

## Phase 5 — Elite Engine

- [ ] NNUE neural network evaluation
- [ ] Late Move Reductions (LMR)
- [ ] Futility pruning
- [ ] Singular extensions
- [ ] Lazy SMP multi-core search
- [ ] **Target: 1,000,000,000 NPS on modern multi-core hardware**

---

## FastPy Transpiler — Ongoing Improvements

- [ ] BMI2 intrinsics: `PEXT`/`PDEP` patterns for magic bitboards
- [ ] `__builtin_clzll` for most-significant-bit index
- [ ] Windows support (MSVC/MinGW detection in `toolchain.py`)
- [ ] Apple Silicon cross-compilation flags
- [ ] Better parse error messages (highlight offending source line)
- [ ] Multi-file compilation support
- [ ] `match` statement support (Python 3.10+)
