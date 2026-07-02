"""
NiceDragon — Spectral Lab
Graph Laplacian builder from a chess position (FEN string).

Graph model:
  - Nodes: 64 squares (0..63, a1=0, h8=63)
  - Edges: one edge per (piece, reachable_square) pair
  - Edge weight: 1.0 baseline, scaled by piece value
  - White pieces contribute positive weight; Black pieces contribute negative
    weight (signed Laplacian variant used for Spectral Margin)

Author: Gokul Chandar / NiceDragon project
"""

import numpy as np
import chess

# Piece values for edge weighting (centipawn scale, normalised)
PIECE_WEIGHT = {
    chess.PAWN:   1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.0,
    chess.ROOK:   5.0,
    chess.QUEEN:  9.0,
    chess.KING:   0.0,   # King mobility not weighted — avoid skewing by king flight squares
}


def _mobility_edges(board: chess.Board) -> list[tuple[int, int, float]]:
    """
    Return list of (from_sq, to_sq, signed_weight) triples.

    signed_weight > 0  → White piece can reach to_sq
    signed_weight < 0  → Black piece can reach to_sq
    """
    edges = []

    # We generate pseudo-legal moves (faster; enough for graph structure)
    for move in board.pseudo_legal_moves:
        piece = board.piece_at(move.from_square)
        if piece is None:
            continue
        w = PIECE_WEIGHT.get(piece.piece_type, 0.0)
        if w == 0.0:
            continue
        sign = +1.0 if piece.color == chess.WHITE else -1.0
        edges.append((move.from_square, move.to_square, sign * w))

    return edges


def build_unsigned_laplacian(board: chess.Board) -> np.ndarray:
    """
    Build the standard (unsigned) Graph Laplacian L = D - A.
    Uses absolute edge weights so L is positive semi-definite.
    Returns a 64×64 float64 matrix.
    """
    A = np.zeros((64, 64), dtype=np.float64)
    for fr, to, w in _mobility_edges(board):
        abs_w = abs(w)
        A[fr, to] += abs_w
        A[to, fr] += abs_w   # undirected

    D = np.diag(A.sum(axis=1))
    return D - A


def build_signed_laplacian(board: chess.Board) -> np.ndarray:
    """
    Build a signed Graph Laplacian that encodes colour.
    White mobility → positive entries; Black mobility → negative.
    This is the matrix used to compute the Spectral Margin.
    Returns a 64×64 float64 matrix (not guaranteed PSD).
    """
    A = np.zeros((64, 64), dtype=np.float64)
    for fr, to, w in _mobility_edges(board):
        A[fr, to] += w
        A[to, fr] += w

    # Degree matrix uses absolute row sums to keep diagonal non-negative
    D = np.diag(np.abs(A).sum(axis=1))
    return D - A


def fiedler_value(board: chess.Board) -> float:
    """
    Return the Fiedler value (second-smallest eigenvalue of unsigned L).
    A higher Fiedler value means the graph is more strongly connected —
    proxy for piece coordination / activity.
    """
    L = build_unsigned_laplacian(board)
    # eigvalsh returns eigenvalues in ascending order; L is symmetric
    eigenvalues = np.linalg.eigvalsh(L)
    # eigenvalues[0] ≈ 0 (always); eigenvalues[1] is Fiedler value
    return float(eigenvalues[1])


def spectral_margin(board: chess.Board) -> float:
    """
    Spectral Margin = λ₂(L_white) - λ₂(L_black).

    Computed by building two unsigned Laplacians — one per side —
    and returning the difference of their Fiedler values.

    Positive value → White has better piece coordination.
    Negative value → Black has better piece coordination.
    """
    # Build a board with only White pieces for λ₂_white
    white_board = chess.Board(fen=None)
    white_board.clear()
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == chess.WHITE:
            white_board.set_piece_at(sq, piece)
    white_board.turn = chess.WHITE

    # Build a board with only Black pieces for λ₂_black
    black_board = chess.Board(fen=None)
    black_board.clear()
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == chess.BLACK:
            # Mirror to White so pseudo_legal_moves work
            mirrored_sq = chess.square_mirror(sq)
            mirrored_piece = chess.Piece(piece.piece_type, chess.WHITE)
            black_board.set_piece_at(mirrored_sq, mirrored_piece)
    black_board.turn = chess.WHITE

    lw = fiedler_value(white_board)
    lb = fiedler_value(black_board)
    return lw - lb


if __name__ == "__main__":
    # Quick smoke test
    board = chess.Board()  # starting position
    print(f"Starting position FEN: {board.fen()}")
    print(f"Fiedler value (unsigned): {fiedler_value(board):.6f}")
    print(f"Spectral Margin:          {spectral_margin(board):.6f}  (expect ≈ 0.0)")

    board2 = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    print(f"\nAfter 1.e4 e5 2.Nf3 Nc6:")
    print(f"Fiedler value (unsigned): {fiedler_value(board2):.6f}")
    print(f"Spectral Margin:          {spectral_margin(board2):.6f}")
