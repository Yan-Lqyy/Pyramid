#!/usr/bin/env python3
import sys
import copy
from typing import List, Dict, Tuple, Optional
import questionary
from rich.console import Console
from rich.text import Text
from rich import print

console = Console(force_terminal=True)

# ----------------------
# Board & Puzzle Definitions
# ----------------------
ORDER = 10  # Right-triangle board: valid positions are those with 0 <= x <= y < ORDER
NUM_BOARD_CELLS = ORDER * (ORDER + 1) // 2  # For order=10, 55 valid cells.
NUM_PIECES = 12
TOTAL_COLUMNS = NUM_BOARD_CELLS + NUM_PIECES  # First part: board cells; second part: piece usage.

# Build a mapping for board cells:
# For each valid coordinate (x, y) with x <= y, assign a unique column index 0 .. (NUM_BOARD_CELLS-1)
board_map: Dict[Tuple[int, int], int] = {}
cell_index = 0
for y in range(ORDER):
    for x in range(y + 1):
        board_map[(x, y)] = cell_index
        cell_index += 1

# Pieces (same as before)
PIECE_DATA = [
    [0b1000, 0b1000, 0b1100, 0b0000],  # A
    [0b1000, 0b1100, 0b1100, 0b0000],  # B
    [0b1000, 0b1000, 0b1000, 0b1100],  # C
    [0b1000, 0b1000, 0b1100, 0b1000],  # D
    [0b1000, 0b1000, 0b1100, 0b0100],  # E
    [0b1000, 0b1100, 0b0000, 0b0000],  # F
    [0b1000, 0b1000, 0b1110, 0b0000],  # G
    [0b1000, 0b1100, 0b0110, 0b0000],  # H
    [0b1100, 0b1000, 0b1100, 0b0000],  # I
    [0b1000, 0b1000, 0b1000, 0b1000],  # J
    [0b1100, 0b1100, 0b0000, 0b0000],  # K
    [0b0100, 0b1110, 0b0100, 0b0000]   # L
]
ROTATES = [8, 8, 8, 8, 8, 4, 4, 4, 4, 2, 1, 1]
PIECE_MAP = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
RICH_COLORS = [
    "gray50", "light_sky_blue1", "light_pink1", "light_green",
    "purple", "magenta2", "blue1", "orange1",
    "gainsboro", "green4", "yellow1", "red1"
]

# ----------------------
# Geometry Classes & Piece Orientations
# ----------------------

class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
    def __repr__(self):
        return f"({self.x},{self.y})"

class Piece:
    WIDTH = 4
    HEIGHT = 4
    def __init__(self, data: List[int], block_index: int, points: Optional[List[Point]] = None, shape_index: int = 0):
        self.points: List[Point] = []
        self.block_index = block_index
        self.shape_index = shape_index
        self.data_template = list(data)
        for i in range(self.HEIGHT):
            for j in range(self.WIDTH):
                if (data[i] & (1 << (self.WIDTH - 1 - j))) != 0:
                    self.points.append(Point(j, i))
        self._normalize()
        if points is not None:
            self.points = points
            self.shape_index = shape_index
    def _normalize(self):
        if not self.points:
            return
        min_x = min(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        for p in self.points:
            p.x -= min_x
            p.y -= min_y
    def rotate(self):
        new_points = [Point(self.HEIGHT - 1 - p.y, p.x) for p in self.points]
        self.points = new_points
        self._normalize()
        self.shape_index += 1
    def flip(self):
        for p in self.points:
            p.x = self.WIDTH - 1 - p.x
        self._normalize()
        self.shape_index += 1
    def get_points(self) -> List[Point]:
        return self.points
    def __repr__(self):
        return f"Piece {PIECE_MAP[self.block_index]}, shape {self.shape_index}, points: {self.points}"

def get_piece_shapes(block_index: int) -> List[Piece]:
    piece = Piece(PIECE_DATA[block_index], block_index)
    shapes = [Piece(PIECE_DATA[block_index], block_index)]
    rotations = ROTATES[block_index]
    if rotations == 8:
        for _ in range(3):
            piece.rotate()
            shapes.append(Piece(PIECE_DATA[block_index], block_index,
                                  points=[Point(p.x, p.y) for p in piece.get_points()],
                                  shape_index=piece.shape_index))
        piece.flip()
        shapes.append(Piece(PIECE_DATA[block_index], block_index,
                              points=[Point(p.x, p.y) for p in piece.get_points()],
                              shape_index=piece.shape_index))
        for _ in range(3):
            piece.rotate()
            shapes.append(Piece(PIECE_DATA[block_index], block_index,
                                  points=[Point(p.x, p.y) for p in piece.get_points()],
                                  shape_index=piece.shape_index))
    elif rotations == 4:
        for _ in range(3):
            piece.rotate()
            shapes.append(Piece(PIECE_DATA[block_index], block_index,
                                  points=[Point(p.x, p.y) for p in piece.get_points()],
                                  shape_index=piece.shape_index))
    elif rotations == 2:
        piece.rotate()
        shapes.append(Piece(PIECE_DATA[block_index], block_index,
                              points=[Point(p.x, p.y) for p in piece.get_points()],
                              shape_index=piece.shape_index))
    return shapes

# ----------------------
# Interactive Manual Placement Process
# ----------------------
pre_solution: List[Tuple[int,int,int,int,List[Tuple[int,int]]]] = []
used_piece_indices = set()

def display_board(pre_solution: List[Tuple[int,int,int,int,List[Tuple[int,int]]]]):
    board_disp = ['.' for _ in range(NUM_BOARD_CELLS)]
    for (piece_index, _, _, _, covered) in pre_solution:
        letter = PIECE_MAP[piece_index]
        for (cx, cy) in covered:
            board_disp[board_map[(cx, cy)]] = letter
    print("\n[bold]Current Manual Placement:[/bold]")
    cell = 0
    for y in range(ORDER):
        row = []
        for x in range(y + 1):
            letter = board_disp[cell]
            style = RICH_COLORS[PIECE_MAP.index(letter)] if letter != '.' else "white"
            row.append(Text(f"{letter} ", style=style))
            cell += 1
        console.print(*row)

def manual_placement():
    global used_piece_indices
    while True:
        display_board(pre_solution)
        action = questionary.select(
            "Choose an action:",
            choices=["Place a piece", "SOLVE", "Exit"]
        ).ask()
        if action is None:
            continue
        if action == "Exit":
            print("[bold yellow]Exiting manual placement.[/bold yellow]")
            sys.exit(0)
        if action == "SOLVE":
            break
        # List available pieces.
        available = [name for idx, name in enumerate(PIECE_MAP) if idx not in used_piece_indices]
        if not available:
            print("[bold yellow]No more pieces to place manually.[/bold yellow]")
            break
        selected_piece = questionary.autocomplete(
            "Choose a piece to place:",
            choices=available
        ).ask()
        if not selected_piece:
            continue
        selected_piece = selected_piece.strip().upper()
        if selected_piece not in PIECE_MAP:
            print(f"[red]Invalid piece '{selected_piece}'.[/red]")
            continue
        piece_index = PIECE_MAP.index(selected_piece)
        piece_shapes = get_piece_shapes(piece_index)
        print(f"\nAvailable shapes for Piece {selected_piece}:")
        for i, shape in enumerate(piece_shapes):
            cell_width = 2
            lines = []
            for row in range(Piece.HEIGHT):
                line = ""
                for col in range(Piece.WIDTH):
                    if any(p.x==col and p.y==row for p in shape.get_points()):
                        line += f"[{RICH_COLORS[piece_index]}]{selected_piece:<{cell_width}}[/]"
                    else:
                        line += " " * cell_width
                lines.append(line)
            print(f"Shape {i+1}:\n" + "\n".join(lines))
        shape_choice = questionary.text(f"Enter shape number for piece {selected_piece}:").ask()
        try:
            shape_index = int(shape_choice.strip()) - 1
            if not (0 <= shape_index < len(piece_shapes)):
                print("[red]Invalid shape number.[/red]")
                continue
        except Exception as e:
            print("[red]Invalid input.[/red]")
            continue
        selected_shape = piece_shapes[shape_index]
        coords = questionary.text("Enter X and Y coordinates separated by a comma (e.g., 0,0):").ask()
        try:
            x_str, y_str = coords.split(",")
            x_coord = int(x_str.strip())
            y_coord = int(y_str.strip())
        except:
            print("[red]Invalid coordinates.[/red]")
            continue
        valid = True
        covered_cells = []
        for p in selected_shape.get_points():
            new_x = x_coord + p.x
            new_y = y_coord + p.y
            if (new_x, new_y) not in board_map:
                valid = False
                break
            covered_cells.append((new_x, new_y))
        if not valid:
            print("[red]Placement out of board bounds.[/red]")
            continue
        pre_solution.append((piece_index, selected_shape.shape_index, x_coord, y_coord, covered_cells))
        used_piece_indices.add(piece_index)
        print(f"[green]Placed piece {selected_piece} at ({x_coord},{y_coord}).[/green]")

# ----------------------
# Dancing Links (DLX) Implementation
# ----------------------
class DLXNode:
    def __init__(self):
        self.L: 'DLXNode' = self
        self.R: 'DLXNode' = self
        self.U: 'DLXNode' = self
        self.D: 'DLXNode' = self
        self.C: 'ColumnNode' = None
        self.row_id: Optional[int] = None

class ColumnNode(DLXNode):
    def __init__(self, name):
        super().__init__()
        self.size = 0
        self.name = name

class DLX:
    def __init__(self, matrix: List[List[int]], col_names: List[str]):
        self.header = ColumnNode("header")
        self.columns: List[ColumnNode] = []
        num_cols = len(col_names)
        prev = self.header
        for i in range(num_cols):
            col = ColumnNode(col_names[i])
            self.columns.append(col)
            col.L = prev
            col.R = self.header
            prev.R = col
            self.header.L = col
            prev = col
        self.nodes: List[DLXNode] = []
        for r, row in enumerate(matrix):
            first = None
            for j in row:
                col = self.columns[j]
                node = DLXNode()
                node.C = col
                node.row_id = r
                node.U = col.U
                node.D = col
                col.U.D = node
                col.U = node
                col.size += 1
                if first is None:
                    first = node
                    node.L = node
                    node.R = node
                else:
                    node.L = first.L
                    node.R = first
                    first.L.R = node
                    first.L = node
                self.nodes.append(node)
        self.solution: List[DLXNode] = []

    def cover(self, col: ColumnNode):
        col.R.L = col.L
        col.L.R = col.R
        i = col.D
        while i != col:
            j = i.R
            while j != i:
                j.D.U = j.U
                j.U.D = j.D
                j.C.size -= 1
                j = j.R
            i = i.D

    def uncover(self, col: ColumnNode):
        i = col.U
        while i != col:
            j = i.L
            while j != i:
                j.C.size += 1
                j.D.U = j
                j.U.D = j
                j = j.L
            i = i.U
        col.R.L = col
        col.L.R = col

    def search(self, k: int = 0, solutions: Optional[List[List[int]]] = None, max_solutions: int = 1) -> List[List[int]]:
        if solutions is None:
            solutions = []
        if len(solutions) >= max_solutions:
            return solutions # Stop if max solutions reached

        if self.header.R == self.header:
            solutions.append([node.row_id for node in self.solution])
            return solutions # Found a solution, but continue searching for more

        col = None
        s = sys.maxsize
        j = self.header.R
        while j != self.header:
            if j.size < s:
                s = j.size
                col = j
            j = j.R

        if col is None or col.size == 0:
            return solutions # No solution from this branch

        self.cover(col)
        r = col.D
        while r != col:
            if len(solutions) >= max_solutions:
                break # Stop if max solutions reached
            self.solution.append(r)
            j = r.R
            while j != r:
                self.cover(j.C)
                j = j.R
            solutions = self.search(k+1, solutions, max_solutions) # Pass solutions list
            if len(solutions) >= max_solutions:
                break # Stop if max solutions reached
            self.solution.pop()
            j = r.L
            while j != r:
                self.uncover(j.C)
                j = j.L
            r = r.D
        self.uncover(col)
        return solutions


if __name__ == "__main__":
    print("[bold blue]Welcome to the Triangular Puzzle Solver![/bold blue]")
    manual_placement()

    # ----------------------
    # Build Exact Cover Matrix for DLX
    # ----------------------
    placements: List[List[int]] = []
    placements_meta: Dict[int, Tuple[int,int,int,int,List[Tuple[int,int]]]] = {}
    row_id = 0
    for piece_index in range(NUM_PIECES):
        shapes = get_piece_shapes(piece_index)
        seen = set()
        for shape in shapes:
            pts_id = tuple(sorted((p.x, p.y) for p in shape.get_points()))
            if pts_id in seen:
                continue
            seen.add(pts_id)
            for y in range(ORDER):
                for x in range(ORDER):
                    valid = True
                    covered = []
                    for p in shape.get_points():
                        new_x = x + p.x
                        new_y = y + p.y
                        if (new_x, new_y) not in board_map:
                            valid = False
                            break
                        covered.append((new_x, new_y))
                    if not valid:
                        continue
                    # Check if this placement overlaps with any pre-placed cells
                    overlap = False
                    for (cx, cy) in covered:
                        for (_, _, _, _, pre_covered) in pre_solution:
                            if (cx, cy) in pre_covered:
                                overlap = True
                                break
                        if overlap:
                            break
                    if overlap:
                        continue
                    board_cols = [board_map[(cx, cy)] for (cx, cy) in covered]
                    piece_col = NUM_BOARD_CELLS + piece_index
                    row = sorted(board_cols + [piece_col])
                    placements.append(row)
                    placements_meta[row_id] = (piece_index, shape.shape_index, x, y, covered)
                    row_id += 1

    # Build column names.
    col_names = []
    board_cells = [None] * NUM_BOARD_CELLS
    for (coord, idx) in board_map.items():
        board_cells[idx] = f"{coord}"
    col_names.extend(board_cells)
    for i in range(NUM_PIECES):
        col_names.append(f"Piece {PIECE_MAP[i]}")

    # Create DLX structure.
    dlx = DLX(placements, col_names)

    # Incorporate Pre-Placement Constraints into DLX
    for (piece_index, shape_index, x, y, covered_cells) in pre_solution:
        # Cover the cells occupied by this pre-placement
        for (cx, cy) in covered_cells:
            col_idx = board_map[(cx, cy)]
            dlx.cover(dlx.columns[col_idx])
        # Cover the piece column to prevent re-use
        piece_col_idx = NUM_BOARD_CELLS + piece_index
        dlx.cover(dlx.columns[piece_col_idx])

    # ----------------------
    # Solve with DLX (Find up to 8 solutions)
    # ----------------------
    max_num_solutions = 8
    all_solution_row_ids_list = dlx.search(max_solutions=max_num_solutions)

    if not all_solution_row_ids_list:
        print("[red]No full board solution found given the pre-placement constraints.[/red]")
        sys.exit(0)

    print(f"\n[bold green]Found {len(all_solution_row_ids_list)} solutions (displaying up to {max_num_solutions}):[/bold green]")

    for sol_idx, solution_row_ids in enumerate(all_solution_row_ids_list):
        if sol_idx >= max_num_solutions:
            break # Display max_num_solutions only
        print(f"\n[bold magenta]Solution #{sol_idx + 1}:[/bold magenta]")

        # Reconstruct placements from placements_meta.
        solution_steps: List[Tuple[int,int,int,int,List[Tuple[int,int]]]] = []
        for rid in solution_row_ids:
            meta = placements_meta[rid]
            solution_steps.append(meta)

        # Combine DLX solution with pre-placement moves.
        full_solution = pre_solution + solution_steps

        # ----------------------
        # Visualize Final Full Board
        # ----------------------
        board_display = ['.' for _ in range(NUM_BOARD_CELLS)]
        for (piece_index, shape_index, x, y, covered) in full_solution:
            letter = PIECE_MAP[piece_index]
            for (cx, cy) in covered:
                board_display[board_map[(cx, cy)]] = letter

        print(f"\n[bold green]Full Board Solution (including your placements):[/bold green]")
        cell = 0
        for y in range(ORDER):
            row_cells = []
            for x in range(y+1):
                letter = board_display[cell]
                color = RICH_COLORS[PIECE_MAP.index(letter)] if letter != '.' else "white"
                row_cells.append(Text(f"{letter} ", style=color))
                cell += 1
            console.print(*row_cells)