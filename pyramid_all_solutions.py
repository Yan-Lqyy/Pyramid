#!/usr/bin/env python3
import sys
import copy
from typing import List, Dict, Tuple, Optional, Set
import questionary
from rich.console import Console
from rich.text import Text
from rich import print
import json
import os

console = Console(force_terminal=True)

# ----------------------
# Piece Definitions (same as before)
# ----------------------
NUM_PIECES = 12
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
# Geometry Classes & Piece Orientations (same as before)
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
# Dancing Links (DLX) Implementation (same as before, progress bar removed)
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
                # link into column
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
            return solutions  # Stop if max solutions reached

        if self.header.R == self.header:
            solutions.append([node.row_id for node in self.solution])
            print(f"[green]Found solution #{len(solutions)}[/green]", end='\r') # inline print
            return solutions

        # Choose column with minimum size.
        col = None
        s = sys.maxsize
        j = self.header.R
        while j != self.header:
            if j.size < s:
                s = j.size
                col = j
            j = j.R

        if col is None or col.size == 0:
            return solutions

        self.cover(col)
        r = col.D
        while r != col:
            if len(solutions) >= max_solutions:
                break
            self.solution.append(r)
            j = r.R
            while j != r:
                self.cover(j.C)
                j = j.R
            solutions = self.search(k+1, solutions, max_solutions)
            if len(solutions) >= max_solutions:
                break
            self.solution.pop()
            j = r.L
            while j != r:
                self.uncover(j.C)
                j = j.L
            r = r.D
        self.uncover(col)
        return solutions

# ----------------------
# Pyramid Pattern and Step Definitions (same as before)
# ----------------------
class PyramidPattern:
    def __init__(self, order: int):
        self.ORDER = order  # number of floors (e.g., 5)
        self.floors: List[List[int]] = [[] for _ in range(self.ORDER)]
        index = 0
        for floor in range(self.ORDER):
            for y in range(floor + 1):
                for x in range(floor + 1):
                    self.floors[floor].append(index + 1)
                    index += 1
        self.diagonals_left: List[List[int]] = [[] for _ in range(2 * self.ORDER - 1)]
        self.diagonals_right: List[List[int]] = [[] for _ in range(2 * self.ORDER - 1)]
        for plane in range(2 * self.ORDER - 1):
            size = self.ORDER - abs(self.ORDER - 1 - plane)
            for y in range(size):
                for x in range(size):
                    if x <= y:
                        floor = self.ORDER - 1 - (y - x)
                        offset = plane - self.ORDER + 1
                        if offset < 0:
                            idx = x * (floor + 1) + (floor + offset - x)
                            self.diagonals_left[plane].append(self.floors[floor][idx])
                            idx = (floor + offset - x) * (floor + 1) + (floor - x)
                            self.diagonals_right[plane].append(self.floors[floor][idx])
                        else:
                            idx = (x + offset) * (floor + 1) + (floor - x)
                            self.diagonals_left[plane].append(self.floors[floor][idx])
                            idx = (floor - x) * (floor + 1) + (floor - offset - x)
                            self.diagonals_right[plane].append(self.floors[floor][idx])
                    else:
                        self.diagonals_left[plane].append(0)
                        self.diagonals_right[plane].append(0)

    def size(self) -> int:
        return sum(len(floor) for floor in self.floors)

class Step:
    def __init__(self, block_index: int, orient_code: int, x: int, y: int):
        self.block_index = block_index
        self.orient_code = orient_code
        self.x = x
        self.y = y
        self.indices: List[int] = []
    def __repr__(self):
        return f"Step(Piece {PIECE_MAP[self.block_index]}, orient {self.orient_code}, pos=({self.x},{self.y}), cells={self.indices})"

# ----------------------
# Generate valid steps (same as before)
# ----------------------
def get_valid_steps(pyramid: PyramidPattern, piece: Piece) -> List[Step]:
    steps: List[Step] = []
    for floor in range(pyramid.ORDER):
        grid_size = floor + 1
        for y in range(grid_size):
            for x in range(grid_size):
                valid = True
                cell_list = []
                for p in piece.get_points():
                    new_x = x + p.x
                    new_y = y + p.y
                    if new_x >= grid_size or new_y >= grid_size:
                        valid = False
                        break
                    cell_index = (new_y) * grid_size + (new_x)
                    cell_num = pyramid.floors[floor][cell_index]
                    if cell_num == 0:
                        valid = False
                        break
                    cell_list.append(cell_num)
                if valid:
                    orient_code = (floor << 3) | piece.shape_index
                    step = Step(piece.block_index, orient_code, x, y)
                    step.indices.extend(cell_list)
                    steps.append(step)
    for plane in range(2 * pyramid.ORDER - 1):
        size = pyramid.ORDER - abs(pyramid.ORDER - 1 - plane)
        for y in range(size):
            for x in range(size):
                valid = True
                cell_list = []
                for p in piece.get_points():
                    new_x = x + p.x
                    new_y = y + p.y
                    if new_x >= size or new_y >= size:
                        valid = False
                        break
                    idx = new_y * size + new_x
                    cell_num = pyramid.diagonals_left[plane][idx]
                    if cell_num == 0:
                        valid = False
                        break
                    cell_list.append(cell_num)
                if valid:
                    orient_code = (1 << 6) | (plane << 3) | piece.shape_index
                    step = Step(piece.block_index, orient_code, x, y)
                    step.indices.extend(cell_list)
                    steps.append(step)
    for plane in range(2 * pyramid.ORDER - 1):
        size = pyramid.ORDER - abs(pyramid.ORDER - 1 - plane)
        for y in range(size):
            for x in range(size):
                valid = True
                cell_list = []
                for p in piece.get_points():
                    new_x = x + p.x
                    new_y = y + p.y
                    if new_x >= size or new_y >= size:
                        valid = False
                        break
                    idx = new_y * size + new_x
                    cell_num = pyramid.diagonals_right[plane][idx]
                    if cell_num == 0:
                        valid = False
                        break
                    cell_list.append(cell_num)
                if valid:
                    orient_code = (1 << 7) | (plane << 3) | piece.shape_index
                    step = Step(piece.block_index, orient_code, x, y)
                    step.indices.extend(cell_list)
                    steps.append(step)
    return steps

# ----------------------
# Symmetry and Canonicalization Functions (same as before)
# ----------------------
def solution_grid_to_string(solution_grid: List[List[str]], pyramid: PyramidPattern) -> str:
    s = ""
    for floor_cells in pyramid.floors:
        for cell_index in floor_cells:
            s += solution_grid[cell_index - 1]
    return s

def rotate_solution_grid(solution_cells: List[str], pyramid: PyramidPattern) -> List[str]:
    rotated_cells: List[str] = ['.'] * len(solution_cells)
    for floor_idx in range(pyramid.ORDER):
        floor = pyramid.floors[floor_idx]
        grid_size = floor_idx + 1
        floor_grid = [['.' for _ in range(grid_size)] for _ in range(grid_size)]
        for j, cell_num in enumerate(floor):
            r = j // grid_size
            c = j % grid_size
            floor_grid[r][c] = solution_cells[cell_num - 1]

        rotated_floor_grid = [['.' for _ in range(grid_size)] for _ in range(grid_size)]
        for r in range(grid_size):
            for c in range(grid_size):
                rotated_floor_grid[c][grid_size - 1 - r] = floor_grid[r][c]

        for j, cell_num in enumerate(floor):
            r = j // grid_size
            c = j % grid_size
            rotated_cells[cell_num - 1] = rotated_floor_grid[r][c]
    return rotated_cells

def reflect_solution_grid(solution_cells: List[str], pyramid: PyramidPattern) -> List[str]:
    reflected_cells: List[str] = ['.'] * len(solution_cells)
    for floor_idx in range(pyramid.ORDER):
        floor = pyramid.floors[floor_idx]
        grid_size = floor_idx + 1
        floor_grid = [['.' for _ in range(grid_size)] for _ in range(grid_size)]
        for j, cell_num in enumerate(floor):
            r = j // grid_size
            c = j % grid_size
            floor_grid[r][c] = solution_cells[cell_num - 1]

        reflected_floor_grid = [['.' for _ in range(grid_size)] for _ in range(grid_size)]
        for r in range(grid_size):
            for c in range(grid_size):
                reflected_floor_grid[r][grid_size - 1 - c] = floor_grid[r][c]

        for j, cell_num in enumerate(floor):
            r = j // grid_size
            c = j % grid_size
            reflected_cells[cell_num - 1] = reflected_floor_grid[r][c]
    return reflected_cells

def get_canonical_solution(solution_cells: List[str], pyramid: PyramidPattern) -> List[str]:
    canonical_grid = solution_cells
    canonical_str = solution_grid_to_string(canonical_grid, pyramid)

    grids = [solution_cells]
    for _ in range(3):
        grids.append(rotate_solution_grid(grids[-1], pyramid))

    reflected_grid = reflect_solution_grid(solution_cells, pyramid)
    grids.append(reflected_grid)
    for _ in range(3):
        grids.append(rotate_solution_grid(grids[-1], pyramid))

    for grid in grids:
        grid_str = solution_grid_to_string(grid, pyramid)
        if grid_str < canonical_str:
            canonical_str = grid_str
            canonical_grid = grid
    return canonical_grid

# ----------------------
# Complexity Calculation
# ----------------------
def calculate_complexity(solution_row_ids: List[int], placements_meta: Dict[int, Tuple[int, int, int, int, List[int]]]) -> int:
    complexity = 0
    for rid in solution_row_ids:
        meta = placements_meta[rid]
        orient_code = meta[1]
        if (orient_code >> 6) & 1: # Diagonal left or right placement
            complexity += 1
    return complexity

# ----------------------
# Display Solution (with complexity)
# ----------------------
def display_solution(solution_cells, pyramid: PyramidPattern, complexity: int, sol_index: int, pyramid_order: int): # Added pyramid_order
    console.print(f"[bold green]Solution #{sol_index} (Complexity: {complexity}):[/bold green]")
    console.print("[bold green]Pyramid Solution:[/bold green]")
    for floor in range(pyramid_order): # Use pyramid_order here
        grid_size = floor + 1
        print(f"\nFloor {floor + 1} ({grid_size}x{grid_size}):")
        cell_nums = [num - 1 for num in pyramid.floors[floor]]
        for r in range(grid_size):
            row_cells = []
            for c in range(grid_size):
                cell_idx = cell_nums[r * grid_size + c]
                letter = solution_cells[cell_idx]
                color = RICH_COLORS[PIECE_MAP.index(letter)] if letter != '.' else "white"
                row_cells.append(Text(f"{letter} ", style=color))
            console.print(*row_cells)

# ----------------------
# Save and Load Solutions
# ----------------------
SOLUTION_FILENAME = "pyramid_solutions.json"

def save_solutions(filename: str, solutions_data: List[Tuple[List[str], int]]):
    """Saves solutions to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump([{'grid': sol[0], 'complexity': sol[1]} for sol in solutions_data], f)
        print(f"[green]Solutions saved to '{filename}'.[/green]")
    except Exception as e:
        print(f"[red]Error saving solutions to '{filename}': {e}[/red]")

def load_solutions(filename: str) -> Optional[List[Tuple[List[str], int]]]:
    """Loads solutions from a JSON file."""
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, 'r') as f:
            loaded_data = json.load(f)
            return [(sol['grid'], sol['complexity']) for sol in loaded_data]
    except Exception as e:
        print(f"[red]Error loading solutions from '{filename}': {e}[/red]")
        return None

# ----------------------
# Main Program: Build Exact Cover Matrix and Solve the Pyramid
# ----------------------
def main():
    PYRAMID_ORDER = 5
    pyramid = PyramidPattern(PYRAMID_ORDER)
    total_cells = pyramid.size()

    loaded_solutions = load_solutions(SOLUTION_FILENAME)
    unique_solutions_with_complexity: List[Tuple[List[str], int]] = []

    if loaded_solutions:
        print(f"[green]Loaded {len(loaded_solutions)} solutions from '{SOLUTION_FILENAME}'.[/green]")
        unique_solutions_with_complexity = loaded_solutions
    else:
        print("[cyan]Searching for solutions...[/cyan]") # Simple message

        placements: List[List[int]] = []
        placements_meta: Dict[int, Tuple[int, int, int, int, List[int]]] = {}
        row_id = 0
        for piece_index in range(NUM_PIECES):
            shapes = get_piece_shapes(piece_index)
            seen = set()
            for shape in shapes:
                pts_id = tuple(sorted((p.x, p.y) for p in shape.get_points()))
                if pts_id in seen:
                    continue
                seen.add(pts_id)
                valid_steps = get_valid_steps(pyramid, shape)
                for step in valid_steps:
                    cell_cols = [num - 1 for num in step.indices]
                    piece_col = total_cells + piece_index
                    row = sorted(cell_cols + [piece_col])
                    placements.append(row)
                    placements_meta[row_id] = (piece_index, step.orient_code, step.x, step.y, [num - 1 for num in step.indices])
                    row_id += 1

        if not placements:
            print("[red]No valid placements found.[/red]")
            sys.exit(1)

        col_names = []
        for i in range(total_cells):
            col_names.append(f"Cell {i}")
        for i in range(NUM_PIECES):
            col_names.append(f"Piece {PIECE_MAP[i]}")

        dlx = DLX(placements, col_names)

        max_num_solutions_dlx = 5000
        canonical_solution_set: Set[str] = set()
        all_solution_row_ids_list = dlx.search(max_solutions=max_num_solutions_dlx)

        if not all_solution_row_ids_list:
            print("[red]No full pyramid solution found.[/red]")
            sys.exit(0)

        print("\nProcessing solutions and removing redundancy...") # Message after search is done

        for solution_row_ids in all_solution_row_ids_list:
            solution_cells = ['.' for _ in range(total_cells)]
            for rid in solution_row_ids:
                meta = placements_meta[rid]
                piece_index, orient_code, x, y, cell_list = meta
                letter = PIECE_MAP[piece_index]
                for cell in cell_list:
                    solution_cells[cell] = letter

            canonical_grid = get_canonical_solution(solution_cells, pyramid)
            canonical_str = solution_grid_to_string(canonical_grid, pyramid)

            if canonical_str not in canonical_solution_set:
                canonical_solution_set.add(canonical_str)
                complexity = calculate_complexity(solution_row_ids, placements_meta)
                unique_solutions_with_complexity.append((canonical_grid, complexity))

        print(f"\n[bold green]Found {len(unique_solutions_with_complexity)} unique solution(s).[/bold green]")
        save_solutions(SOLUTION_FILENAME, unique_solutions_with_complexity) # Save after finding

    if not unique_solutions_with_complexity:
        print("[red]No unique solutions found.[/red]")
        sys.exit(0)

    # Default is original indexing, not sorted by complexity
    solutions_display_list = list(unique_solutions_with_complexity) # copy for display
    complexity_sorted = False # Initial state: not sorted

    print("\n[bold magenta]Example Solution (Solution #1, Original Indexing):[/bold magenta]")
    display_solution(solutions_display_list[0][0], pyramid, solutions_display_list[0][1], 1, PYRAMID_ORDER) # Pass PYRAMID_ORDER

    while True:
        view_prompt = "Enter solution numbers to view (e.g., 1, 3, 5 or 2-4), 'all', 'change', 'load', 'save', or 'exit':"
        answer = questionary.text(view_prompt).ask()

        if answer is None or answer.lower() in ["exit", "quit"]:
            break
        elif answer.lower() in ["change", "sort"]: # Toggle sort mode
            complexity_sorted = not complexity_sorted
            if complexity_sorted:
                solutions_display_list = sorted(unique_solutions_with_complexity, key=lambda item: item[1], reverse=True) # Descending sort
                print("[green]Solutions are now sorted by complexity (most complex first).[/green]")
            else:
                solutions_display_list = list(unique_solutions_with_complexity) # Revert to original order
                print("[green]Reverted to original solution indexing.[/green]")
            continue # Skip solution viewing for this iteration
        elif answer.lower() == "save":
            save_solutions(SOLUTION_FILENAME, unique_solutions_with_complexity)
            continue
        elif answer.lower() == "load":
            loaded_sols = load_solutions(SOLUTION_FILENAME)
            if loaded_sols:
                unique_solutions_with_complexity = loaded_sols
                solutions_display_list = list(unique_solutions_with_complexity) # reset display list
                complexity_sorted = False # reset sort
                print(f"[green]Loaded {len(unique_solutions_with_complexity)} solutions.[/green]")
                print("\n[bold magenta]Example Solution (Solution #1, Original Indexing):[/bold magenta]") # Show example again after load
                display_solution(solutions_display_list[0][0], pyramid, solutions_display_list[0][1], 1, PYRAMID_ORDER)
            else:
                print("[red]No solutions loaded or error loading.[/red]")
            continue


        if answer.lower() == "all":
            sol_indices_to_show = list(range(1, len(solutions_display_list) + 1))
        else:
            sol_indices_to_show = []
            parts = answer.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        sol_indices_to_show.extend(range(start, end + 1))
                    except ValueError:
                        print("[red]Invalid range format.[/red]")
                        continue
                else:
                    try:
                        sol_indices_to_show.append(int(part))
                    except ValueError:
                        print("[red]Invalid number format.[/red]")
                        continue

        valid_indices_to_show = []
        for index in sol_indices_to_show:
            if 1 <= index <= len(solutions_display_list):
                valid_indices_to_show.append(index)
            else:
                print(f"[yellow]Solution #{index} is out of range.[/yellow]")

        for index in valid_indices_to_show:
            sol_list_index = index - 1 # adjust to list index
            display_solution(solutions_display_list[sol_list_index][0], pyramid, solutions_display_list[sol_list_index][1], index, PYRAMID_ORDER) # Pass PYRAMID_ORDER
            print("\n" + "-"*40)


if __name__ == "__main__":
    print("[bold blue]Welcome to the Pyramid Puzzle Solver using DLX![/bold blue]")
    main()