import sys
import os
import json
import copy
from typing import List, Dict, Tuple, Optional, Any, Set
import questionary
from rich.console import Console
from rich.text import Text
from rich import print
import time  # Import time module

console = Console(force_terminal=True)

# ======================================================
# Global definitions: Pieces and their orientation counts.
# ======================================================
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
# For each piece, the value in ROTATES tells us:
#  8: 4 rotations and flip allowed (so up to 8 distinct orientations),
#  4: 4 rotations (no flip), 2: 2 rotations, 1: only one.
ROTATES = [8, 8, 8, 8, 8, 4, 4, 4, 4, 2, 1, 1]
PIECE_MAP = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
RICH_COLORS = [
    "gray50", "light_sky_blue1", "light_pink1", "light_green",
    "purple", "magenta2", "blue1", "orange1",
    "gainsboro", "green4", "yellow1", "red1"
]

# ------------------------------------------------------
# Geometry: Point, Piece, and distinct orientation generation.
# ------------------------------------------------------
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
        self.block_index = block_index
        self.shape_index = shape_index
        self.data_template = list(data)
        if points is None:
            self.points: List[Point] = []
            for i in range(self.HEIGHT):
                for j in range(self.WIDTH):
                    if (data[i] & (1 << (self.WIDTH - 1 - j))) != 0:
                        self.points.append(Point(j, i))
            self._normalize()
        else:
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
        # Rotate 90 degrees clockwise.
        new_points = [Point(self.HEIGHT - 1 - p.y, p.x) for p in self.points]
        self.points = new_points
        self._normalize()
        self.shape_index += 1
    def flip(self):
        # Flip horizontally.
        new_points = [Point(self.WIDTH - 1 - p.x, p.y) for p in self.points]
        self.points = new_points
        self._normalize()
        self.shape_index += 1
    def get_points(self) -> List[Point]:
        return self.points
    def __repr__(self):
        return f"Piece {PIECE_MAP[self.block_index]}, shape {self.shape_index}, points: {self.points}"

def visualize_piece_shape(piece: Piece) -> str:
    """
    Visualize a piece shape as a 4x4 grid string with proper spacing and coloring.
    We use the same cell width as the board (2 characters per cell) and Rich markup.
    """
    cell_width = 2
    piece_color = RICH_COLORS[piece.block_index % len(RICH_COLORS)]
    piece_letter = PIECE_MAP[piece.block_index]
    lines = []
    # Build a 4x4 grid.
    for y in range(Piece.HEIGHT):
        line = ""
        for x in range(Piece.WIDTH):
            # If the piece occupies this cell, print its letter in color.
            if any(p.x == x and p.y == y for p in piece.get_points()):
                padded = f"[{piece_color}]{piece_letter:<{cell_width}}[/]"
            else:
                padded = " ."  # Changed to " ." to align with your example
            line += padded
        lines.append(line)
    return "\n".join(lines)


def get_piece_shapes(block_index: int) -> List[Piece]:
    """Generate all possible shapes (rotations/flips) for a given piece."""
    piece = Piece(PIECE_DATA[block_index], block_index)
    shapes = [Piece(PIECE_DATA[block_index], block_index)]
    rotations = ROTATES[block_index]
    if rotations == 8:
        for _ in range(3):  # Three rotations
            piece.rotate()
            shapes.append(Piece(PIECE_DATA[block_index], block_index,
                                  points=[Point(p.x, p.y) for p in piece.get_points()],
                                  shape_index=piece.shape_index))
        piece.flip()  # Flip the piece.
        shapes.append(Piece(PIECE_DATA[block_index], block_index,
                              points=[Point(p.x, p.y) for p in piece.get_points()],
                              shape_index=piece.shape_index))
        for _ in range(3):  # Rotations of the flipped piece.
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

# ======================================================
# DLX (Dancing Links) implementation for exact cover.
# ======================================================
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

    def search(self, k: int = 0, solutions: Optional[List[List[int]]] = None, max_solutions: int = 3000) -> List[List[int]]:
        if solutions is None:
            solutions = []
        if len(solutions) >= max_solutions:
            return solutions

        if self.header.R == self.header:
            solutions.append([node.row_id for node in self.solution])
            return solutions

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
            self.search(k+1, solutions, max_solutions)
            self.solution.pop()
            j = r.L
            while j != r:
                self.uncover(j.C)
                j = j.L
            r = r.D
        self.uncover(col)
        return solutions

class PyramidPattern: # ... (PyramidPattern class - same as before)
    def __init__(self, order: int):
        self.ORDER = order  # number of floors (e.g., 5)
        # Build horizontal floors.
        self.floors: List[List[int]] = [[] for _ in range(self.ORDER)]
        index = 0
        for floor in range(self.ORDER):
            for y in range(floor + 1):
                for x in range(floor + 1):
                    self.floors[floor].append(index + 1)  # 1-indexed cell numbers
                    index += 1

        # Build diagonal arrays (for vertical placements).
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

class Step: # ... (Step class - same as before)
    def __init__(self, block_index: int, orient_code: int, x: int, y: int):
        self.block_index = block_index
        self.orient_code = orient_code  # Encodes orientation info.
        self.x = x
        self.y = y
        self.indices: List[int] = []  # List of pyramid cell numbers (1-indexed)
    def __repr__(self):
        return f"Step(Piece {PIECE_MAP[self.block_index]}, orient {self.orient_code}, pos=({self.x},{self.y}), cells={self.indices})"

def get_valid_steps(pyramid: PyramidPattern, piece: Piece) -> List[Step]: # ... (get_valid_steps function - same as before)
    steps: List[Step] = []
    # Horizontal placements on floors.
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
                    cell_index = new_y * grid_size + new_x
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
    # Diagonal placements on the left–tilted planes.
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
    # Diagonal placements on the right–tilted planes.
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

def compute_and_store_solutions(solution_file: str) -> List[Dict[str, Any]]: # ... (compute_and_store_solutions function - same as before)
    pyramid = PyramidPattern(5)  # order=5 pyramid (floors 1,2,3,4,5)
    total_cells = pyramid.size()  # 55 cells

    placements: List[List[int]] = []
    placements_meta: Dict[int, Dict[str, Any]] = {}
    row_id = 0
    for piece_index in range(NUM_PIECES):
        shapes = get_piece_shapes(piece_index)
        seen: Set[Tuple[Tuple[int,int],...]] = set() # To avoid duplicate shapes, although get_piece_shapes should already handle this
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
                placements_meta[row_id] = {
                    "piece_index": piece_index,
                    "orient_code": step.orient_code,
                    "x": step.x,
                    "y": step.y,
                    "cells": [num - 1 for num in step.indices]
                }
                row_id += 1

    col_names = [f"Cell {i}" for i in range(total_cells)]
    col_names.extend([f"Piece {PIECE_MAP[i]}" for i in range(NUM_PIECES)])

    dlx = DLX(placements, col_names)
    all_solution_row_ids_list = dlx.search(max_solutions=3000)
    if not all_solution_row_ids_list:
        print("[red]No full pyramid solution found.[/red]")
        sys.exit(0)
    all_solutions: List[Dict[str, Any]] = []
    for sol in all_solution_row_ids_list:
        sol_list = []
        for rid in sol:
            sol_list.append(placements_meta[rid])
        all_solutions.append({"placements": sol_list})
    with open(solution_file, "w") as f:
        json.dump(all_solutions, f)
    print(f"[green]Stored {len(all_solutions)} solutions in '{solution_file}'.[/green]")
    return all_solutions

def load_solutions(solution_file: str) -> List[Dict[str, Any]]: # ... (load_solutions function - same as before)
    if not os.path.exists(solution_file):
        return [] # Return empty list if file doesn't exist yet
    with open(solution_file, "r") as f:
        solutions = json.load(f)
    print(f"[green]Loaded {len(solutions)} solutions from '{solution_file}'.[/green]")
    return solutions

def get_bottom_layer_indices(pyramid: PyramidPattern) -> List[int]: # ... (get_bottom_layer_indices function - same as before)
    return [num - 1 for num in pyramid.floors[-1]]

def filter_solutions(solutions: List[Dict[str, Any]], constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]: # ... (filter_solutions function - same as before)
    filtered = []
    for sol in solutions:
        valid = True
        placement_by_piece: Dict[int, List[int]] = {}
        for placement in sol["placements"]:
            placement_by_piece[placement["piece_index"]] = placement["cells"]
        for cons in constraints:
            if cons["type"] == "full":
                piece = cons["piece_index"]
                if piece not in placement_by_piece:
                    valid = False
                    break
                bottom_set = set(get_bottom_layer_indices(PyramidPattern(5)))
                placement_cells = set(placement_by_piece[piece])
                cons_cells = set(cons["cells"])
                if not placement_cells.issubset(bottom_set):
                    valid = False
                    break
                if placement_cells != cons_cells: # Must be exactly those cells
                    valid = False
                    break
            elif cons["type"] == "point":
                piece = cons["piece_index"]
                cell = cons["cell"]
                if piece not in placement_by_piece:
                    valid = False
                    break
                if cell not in placement_by_piece[piece]:
                    valid = False
                    break
        if valid:
            filtered.append(sol)
    return filtered

def display_solution(sol: Dict[str, Any], pyramid: PyramidPattern): # ... (display_solution function - same as before)
    total_cells = pyramid.size()
    solution_cells = ['.' for _ in range(total_cells)]
    for placement in sol["placements"]:
        letter = PIECE_MAP[placement["piece_index"]]
        for cell in placement["cells"]:
            solution_cells[cell] = letter
    cell_to_coord: Dict[int, Tuple[int,int,int]] = {}
    for floor in range(pyramid.ORDER):
        grid_size = floor + 1
        for j, cell_num in enumerate(pyramid.floors[floor]):
            r = j // grid_size
            c = j % grid_size
            cell_to_coord[cell_num - 1] = (floor, r, c)
    for floor in range(pyramid.ORDER):
        grid_size = floor + 1
        print(f"\n[bold]Floor {floor+1} ({grid_size}x{grid_size}):[/bold]")
        cells = [num - 1 for num in pyramid.floors[floor]]
        for r in range(grid_size):
            row_cells = []
            for c in range(grid_size):
                cell_idx = cells[r * grid_size + c]
                letter = solution_cells[cell_idx]
                color = RICH_COLORS[PIECE_MAP.index(letter)] if letter != '.' else "white"
                row_cells.append(Text(f"{letter} ", style=color))
            console.print(*row_cells, sep=" ")

    print("\n" + "-"*40)

def visualize_bottom_layer_constraints(constraints: List[Dict[str, Any]], pyramid: PyramidPattern): # ... (visualize_bottom_layer_constraints function - same as before)
    """Visualizes the bottom 5x5 layer with current pre-placement constraints."""
    bottom_layer_grid = [['.' for _ in range(5)] for _ in range(5)]
    bottom_layer_cells = get_bottom_layer_indices(pyramid)
    bottom_min_cell_val = min(bottom_layer_cells)

    for constraint in constraints:
        if constraint["type"] == "full":
            piece_index = constraint["piece_index"]
            piece_letter = PIECE_MAP[piece_index]
            for cell_index in constraint["cells"]:
                rel_cell_index = cell_index - bottom_min_cell_val
                if 0 <= rel_cell_index < 25: # Ensure it's within bottom layer
                    row = rel_cell_index // 5
                    col = rel_cell_index % 5
                    bottom_layer_grid[row][col] = piece_letter
        elif constraint["type"] == "point":
            piece_index = constraint["piece_index"]
            piece_letter = PIECE_MAP[piece_index]
            cell_index = constraint["cell"]
            rel_cell_index = cell_index - bottom_min_cell_val
            if 0 <= rel_cell_index < 25: # Ensure it's within bottom layer
                row = rel_cell_index // 5
                col = rel_cell_index % 5
                bottom_layer_grid[row][col] = piece_letter

    print("\n[bold]Current Bottom Layer Constraints:[/bold]")
    for row_index, row in enumerate(bottom_layer_grid):
        row_segments = []
        for cell_content in row:
            if cell_content == '.':
                rich_text_cell = Text(". ")
            else:
                color = RICH_COLORS[PIECE_MAP.index(cell_content)]
                rich_text_cell = Text(f"{cell_content} ", style=color)
            row_segments.append(rich_text_cell)
        console.print(*row_segments, sep="")
    print()


def get_preplacement_constraints(pyramid: PyramidPattern) -> List[Dict[str, Any]]: # ... (get_preplacement_constraints function - same as before)
    constraints: List[Dict[str, Any]] = []
    bottom_indices = set(get_bottom_layer_indices(pyramid))

    while True:
        visualize_bottom_layer_constraints(constraints, pyramid) # Display bottom layer every menu loop
        time.sleep(0.1) # Add small delay here
        print("\n[bold cyan]Pre-placement Constraint Menu[/bold cyan]")
        choice = questionary.select(
            "Choose an action:",
            choices=[
                "Add full piece pre-placement (bottom layer only)",
                "Add point constraint (bottom layer cell)",
                "View current constraints",
                "Clear all constraints",
                "Done"
            ]
        ).ask()
        if choice is None or choice == "Done":
            break
        if choice == "Clear all constraints":
            constraints = []
            print("[yellow]All constraints cleared.[/yellow]")
            continue
        if choice == "View current constraints":
            if not constraints:
                print("[dim]No constraints set.[/dim]")
            else:
                for i, cons in enumerate(constraints):
                    if cons["type"] == "full":
                        print(f"[dim]Constraint {i+1}: Full piece {PIECE_MAP[cons['piece_index']]} pre-placed in bottom layer, cells: {cons['cells']}[/dim]")
                    elif cons["type"] == "point":
                        cell_index = cons['cell']
                        floor_5_cells = get_bottom_layer_indices(pyramid)
                        if 0 <= cell_index < len(floor_5_cells):
                            rel_index = cell_index - min(floor_5_cells)
                            y_coord = rel_index // 5
                            x_coord = rel_index % 5
                            print(f"[dim]Constraint {i+1}: Point ({x_coord},{y_coord}) must be covered by piece {PIECE_MAP[cons['piece_index']]}[/dim]")
                        else:
                            print(f"[dim]Constraint {i+1}: Point (cell index {cell_index}) must be covered by piece {PIECE_MAP[cons['piece_index']]}[/dim]")
            continue

        if choice.startswith("Add full piece"): # ... (rest of "Add full piece" logic - same as before)
            available = [name for name in PIECE_MAP]
            piece_letter = questionary.autocomplete(
                "Choose a piece for full pre-placement (bottom layer only):",
                choices=available
            ).ask()
            if piece_letter is None:
                continue
            piece_letter = piece_letter.strip().upper()
            if piece_letter not in PIECE_MAP:
                print(f"[red]Invalid piece: {piece_letter}.[/red]")
                continue
            piece_index = PIECE_MAP.index(piece_letter)
            piece_shapes = get_piece_shapes(piece_index) # Get all shapes

            print(f"\nAvailable shapes for Piece {piece_letter}:") # Display shapes only once here
            for i, shape in enumerate(piece_shapes):  # Print visualizations before the choice prompt
                print(f"[bold]Shape {i+1}:[/bold]\n{visualize_piece_shape(shape)}")

            shape_choices = [str(i+1) for i in range(len(piece_shapes))] # Shape choices are just numbers

            selected_shape_choice = questionary.autocomplete(
                f"Choose shape for piece {piece_letter}:",
                choices=shape_choices,
                validate=lambda text: text.strip().isdigit() and 1 <= int(text.strip()) <= len(piece_shapes),
                style=questionary.Style([
                    ('answer', 'fg:#f44336 bold'),
                ])
            ).ask()
            if not selected_shape_choice:
                continue

            selected_shape_index = int(selected_shape_choice.strip()) - 1
            selected_piece_shape = piece_shapes[selected_shape_index]

            while True: # Loop for coordinate input
                coords_str = questionary.text("Enter bottom layer coordinates X,Y (0-4, e.g., 0,0):").ask()
                if not coords_str: # User cancelled coordinate input
                    break # Go back to constraint menu
                try:
                    x_str, y_str = coords_str.split(",")
                    x_coord = int(x_str.strip())
                    y_coord = int(y_str.strip())
                    if not (0 <= x_coord <= 4 and 0 <= y_coord <= 4):
                        print("[red]Coordinates must be between 0 and 4.[/red]")
                        continue

                    valid_placement = True
                    cell_list = []
                    bottom_layer_cells = pyramid.floors[-1] # 5x5 bottom layer
                    bottom_min_cell_val = min(bottom_layer_cells) -1 # to make 0-indexed

                    for p in selected_piece_shape.get_points():
                        new_x, new_y = x_coord + p.x, y_coord + p.y
                        if not (0 <= new_x <= 4 and 0 <= new_y <= 4): # Check if within 5x5 grid
                            valid_placement = False
                            break
                        cell_index_in_bottom_layer = new_y * 5 + new_x
                        cell_num = bottom_layer_cells[cell_index_in_bottom_layer]
                        cell_list.append(cell_num - 1) # Store 0-indexed cell numbers

                    if valid_placement:
                        constraint = {
                            "type": "full",
                            "piece_index": piece_index,
                            "cells": cell_list
                        }
                        constraints.append(constraint)
                        print(f"[green]Added full pre-placement constraint for piece {piece_letter}, shape {selected_shape_choice} at ({x_coord},{y_coord}).[/green]")
                        break # Exit coordinate input loop
                    else:
                        print("[red]Piece placement is not fully within the 5x5 bottom layer grid. Try again.[/red]")

                except ValueError:
                    print("[red]Invalid coordinate format. Please enter X,Y (e.g., 0,0).[/red]")


        elif choice.startswith("Add point constraint"): # ... (rest of "Add point constraint" logic - same as before)
            coord = questionary.text(
                "Enter bottom layer coordinate as X,Y (0-indexed, 0<=X,Y<=4):"
            ).ask()
            if coord is None:
                continue
            try:
                x_str, y_str = coord.split(",")
                x_coord = int(x_str.strip())
                y_coord = int(y_str.strip())
            except Exception as e:
                print("[red]Invalid coordinate format.[/red]")
                continue
            if not (0 <= x_coord <= 4 and 0 <= y_coord <= 4):
                print("[red]Coordinates must be between 0 and 4.[/red]")
                continue
            cell_index = pyramid.floors[-1][y_coord * 5 + x_coord] - 1
            piece_letter = questionary.autocomplete(
                "Enter the piece letter that must cover cell ({x_coord},{y_coord}):",
                choices=PIECE_MAP
            ).ask()
            if piece_letter is None:
                continue
            piece_letter = piece_letter.strip().upper()
            if piece_letter not in PIECE_MAP:
                print(f"[red]Invalid piece: {piece_letter}.[/red]")
                continue
            piece_index = PIECE_MAP.index(piece_letter)
            constraint = {
                "type": "point",
                "piece_index": piece_index,
                "cell": cell_index
            }
            constraints.append(constraint)
            print(f"[green]Added point constraint: cell ({x_coord},{y_coord}) must be covered by piece {piece_letter}.[/green]")
        visualize_bottom_layer_constraints(constraints, pyramid) # Visualize after adding constraint

    return constraints


def main(): # ... (main function - same as before)
    print("[bold blue]Welcome to the Pyramid Puzzle Pre-placement Constraint Tool![/bold blue]") # Clarification message
    solution_file = "pyramid_solver.json"
    all_solutions = load_solutions(solution_file)
    if not all_solutions: # if no solutions loaded or file doesn't exist, compute them
        print("[bold blue]Computing full pyramid solutions using DLX...[/bold blue]")
        all_solutions = compute_and_store_solutions(solution_file)
    print(f"[bold blue]Total solutions available: {len(all_solutions)}[/bold blue]")

    pyramid = PyramidPattern(5)
    constraints = get_preplacement_constraints(pyramid)
    if constraints:
        print("\n[bold blue]Filtering solutions with pre-placement constraints...[/bold blue]")
    else:
        print("\n[bold blue]No pre-placement constraints provided; showing all solutions.[/bold blue]")

    filtered_solutions = filter_solutions(all_solutions, constraints)
    print(f"[green]Solutions remaining after filtering: {len(filtered_solutions)}[/green]")
    if not filtered_solutions:
        print("[red]No solutions satisfy the pre-placement constraints.[/red]")
        sys.exit(0)

    if not filtered_solutions:
        print("[yellow]No solutions found with current constraints.[/yellow]")
        return

    while True: # ... (rest of main function - same as before)
        sol_index_str = questionary.text(
            f"Enter solution number to display (1 to {len(filtered_solutions)}; or 'q' to quit):"
        ).ask()
        if sol_index_str is None or sol_index_str.strip().lower() == 'q':
            break
        try:
            sol_index = int(sol_index_str.strip()) - 1
            if 0 <= sol_index < len(filtered_solutions):
                display_solution(filtered_solutions[sol_index], pyramid)
            else:
                print("[red]Invalid solution number.[/red]")
        except Exception as e:
            print("[red]Invalid input.[/red]")

if __name__ == "__main__":
    print("[bold blue]Welcome to the Pyramid Puzzle Pre-placement Solver![/bold blue]")
    main()