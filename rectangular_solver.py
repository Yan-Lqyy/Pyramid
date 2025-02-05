import time
import sys
from typing import List, Dict, Tuple, Optional
from io import StringIO

import questionary
from rich.console import Console
from rich.text import Text
from rich import print

# Global console for output
console = Console(force_terminal=True)

# --- Constants ---
PIECES = 12  # Total number of pieces
WIDTH = 11   # Rectangular board dimensions
HEIGHT = 5
TOTAL_CELLS = WIDTH * HEIGHT

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

# --- Data Structures ---
class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"({self.x},{self.y})"

class Step:
    def __init__(self, block_index: int, shape_index: int, x: int, y: int):
        self.block_index = block_index
        self.shape_index = shape_index
        self.x = x
        self.y = y
        self.indices: List[int] = []

class Piece:
    WIDTH = 4
    HEIGHT = 4

    def __init__(self, data: List[int], block_index: int, points=None, shape_index=0):
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

# --- DLX Implementation ---
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

    def search(self, k: int = 0, solutions: Optional[List[List[int]]] = None, max_solutions: int = -1) -> List[List[int]]: # max_solutions = -1 for all solutions
        if solutions is None:
            solutions = []

        if self.header.R == self.header:
            solutions.append([node.row_id for node in self.solution])
            if max_solutions > 0 and len(solutions) >= max_solutions:
                return solutions # Stop if max solutions reached, if limit is set
            return solutions # Found a solution, continue searching for more

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
            if max_solutions > 0 and len(solutions) >= max_solutions:
                break # Stop if max solutions reached, if limit is set
            self.solution.append(r)
            j = r.R
            while j != r:
                self.cover(j.C)
                j = j.R
            solutions = self.search(k+1, solutions, max_solutions) # Pass solutions list
            if max_solutions > 0 and len(solutions) >= max_solutions:
                break # Stop if max solutions reached, if limit is set
            self.solution.pop()
            j = r.L
            while j != r:
                self.uncover(j.C)
                j = j.L
            r = r.D
        self.uncover(col)
        return solutions

# --- Puzzle Solver ---
class RectangularSolver:
    def __init__(self):
        self.board_map = {(x, y): y * WIDTH + x for y in range(HEIGHT) for x in range(WIDTH)}
        self.reverse_board_map = {v: k for k, v in self.board_map.items()}
        self.original_matrix = [i for i in range(TOTAL_CELLS)] # Cell indices 0 to 54
        self.occupancy = list(self.original_matrix) # Use indices directly
        self.pre_solution: List[Step] = []
        self.used_pieces = set()

    def reset(self):
        self.occupancy = list(self.original_matrix)
        self.pre_solution.clear()
        self.used_pieces.clear()

    def visualize_board(self, solution: List[Step] = None):
        if solution is None:
            solution = self.pre_solution
        board_display = [-1] * TOTAL_CELLS
        for step in solution:
            piece = get_piece_shapes(step.block_index)[step.shape_index]
            for p in piece.get_points():
                board_index = self.board_map[(step.x + p.x, step.y + p.y)]
                board_display[board_index] = step.block_index

        print("\n[bold]Current Board State:[/bold]")
        for y in range(HEIGHT):
            row_segments = []
            for x in range(WIDTH):
                piece_index = board_display[self.board_map[(x,y)]]
                if piece_index == -1:
                    padded = f"{'.':<2}"
                    cell_text = Text(padded)
                else:
                    piece_letter = PIECE_MAP[piece_index]
                    color = RICH_COLORS[piece_index % len(RICH_COLORS)]
                    padded = f"{piece_letter:<2}"
                    cell_text = Text(padded, style=color)
                row_segments.append(cell_text)
            console.print(*row_segments, sep=" ")

    def get_piece_shapes(self, block_index: int) -> List[Piece]:
        return get_piece_shapes(block_index) # Use the global function

    def manual_placement(self):
        while True:
            self.visualize_board()
            action = questionary.select(
                "Choose action:",
                choices=["Place piece", "Solve", "View Solutions", "Reset", "Exit"]
            ).ask()

            if action == "Exit":
                sys.exit(0)
            elif action == "Reset":
                self.reset()
            elif action == "Solve":
                solutions = self.solve()
                if solutions:
                    self._display_solutions_interactive(solutions)
                else:
                    print("[red]No solution found[/red]")
            elif action == "View Solutions":
                if hasattr(self, 'last_solutions') and self.last_solutions:
                    self._display_solutions_interactive(self.last_solutions)
                else:
                    print("[yellow]No solutions found yet. Solve first.[/yellow]")
            elif action == "Place piece":
                self._place_piece_interactive()
            if action is None: # Handle Ctrl+C
                continue
        return None # To satisfy type hint, though unreachable

    def _display_solutions_interactive(self, solutions: List[List[Step]]):
        if not solutions:
            print("[red]No solutions found.[/red]")
            return

        self.last_solutions = solutions # Store solutions for viewing later

        print(f"[bold green]Found {len(solutions)} solutions![/bold green]")
        print("[bold]Displaying first solution:[/bold]")
        self.visualize_board(solutions[0])

        while True:
            if len(solutions) > 1:
                answer = questionary.text(
                    "Enter solution number to view (e.g., 2, 5, 10), range (e.g., 2-5), 'all', or 'back':"
                ).ask()
                if not answer:
                    continue

                if answer.lower() == 'back':
                    break
                elif answer.lower() == 'all':
                    if len(solutions) > 10: # Warn if many solutions
                        if not questionary.confirm(f"Display all {len(solutions)} solutions? This might be lengthy.").ask():
                            continue # Go back to prompt if user cancels
                    for i, sol in enumerate(solutions):
                        print(f"[bold]Solution #{i+1}:[/bold]")
                        self.visualize_board(sol)
                    break # Exit after showing all

                try:
                    indices_to_show = self._parse_solution_input(answer, len(solutions))
                    if indices_to_show:
                        for index in indices_to_show:
                            if 1 <= index <= len(solutions):
                                print(f"[bold]Solution #{index}:[/bold]")
                                self.visualize_board(solutions[index-1])
                            else:
                                print(f"[yellow]Solution number {index} is out of range (1-{len(solutions)}).[/yellow]")
                    else:
                        print("[red]Invalid input format for solution selection.[/red]")

                except ValueError:
                    print("[red]Invalid input. Please enter a number, range (e.g., 2-5), 'all', or 'back'.[/red]")
            else:
                if questionary.confirm("No more solutions to view. Back to menu?").ask():
                    break
                else:
                    continue


    def _parse_solution_input(self, input_str: str, num_solutions: int) -> Optional[List[int]]:
        input_str = input_str.strip().lower()
        if not input_str:
            return None

        if input_str == 'back':
            return None # Signal to go back

        if '-' in input_str:
            try:
                start_str, end_str = input_str.split('-')
                start_index = int(start_str)
                end_index = int(end_str)
                if start_index > end_index or start_index < 1 or end_index > num_solutions:
                    raise ValueError
                return list(range(start_index, end_index + 1))
            except ValueError:
                raise ValueError # Re-raise to be caught in display function
        else:
            try:
                sol_index = int(input_str)
                if 1 <= sol_index <= num_solutions:
                    return [sol_index]
                else:
                    raise ValueError
            except ValueError:
                raise ValueError # Re-raise to be caught in display function


    def _place_piece_interactive(self):
        available_pieces = [(piece_name, index) for index, piece_name in enumerate(PIECE_MAP)
                            if index not in self.used_pieces]
        if not available_pieces:
            print("[bold yellow]All pieces are used or pre-placed.[/bold yellow]")
            time.sleep(1)
            return

        piece_choices = [name for name, index in available_pieces]

        selected_piece_choice = questionary.autocomplete(
            "Choose a piece to place:",
            choices=piece_choices,
        ).ask()

        if not selected_piece_choice:
            return

        selected_piece_name = selected_piece_choice.strip().upper()
        selected_piece_index = PIECE_MAP.index(selected_piece_name)
        piece_shapes = self.get_piece_shapes(selected_piece_index)

        print(f"\nAvailable shapes for Piece {selected_piece_name}:")
        for i, shape in enumerate(piece_shapes):
            cell_width = 2
            lines = []
            for row in range(Piece.HEIGHT):
                line = ""
                for col in range(Piece.WIDTH):
                    if any(p.x==col and p.y==row for p in shape.get_points()):
                        line += f"[{RICH_COLORS[selected_piece_index]}]{selected_piece_name:<{cell_width}}[/]"
                    else:
                        line += " " * cell_width
                lines.append(line)
            print(f"Shape {i+1}:\n" + "\n".join(lines))

        shape_choices = [str(i+1) for i in range(len(piece_shapes))]
        while True: # Loop for valid shape choice
            selected_shape_choice = questionary.autocomplete(
                f"Choose shape for piece {selected_piece_name}:",
                choices=shape_choices,
            ).ask()

            if not selected_shape_choice:
                return

            try:
                selected_shape_index = int(selected_shape_choice.strip()) - 1
                if 0 <= selected_shape_index < len(piece_shapes):
                    selected_piece_shape = piece_shapes[selected_shape_index]
                    break # Valid shape chosen, exit shape choice loop
                else:
                    print("[red]Invalid shape number. Please choose from the available shapes.[/red]")
            except ValueError:
                print("[red]Invalid input. Please enter a number for the shape.[/red]")


        while True: # Loop for valid coordinate input
            coords = questionary.text("Enter X,Y coordinates (e.g., 0,0):").ask()
            if not coords:
                break
            try:
                x_str, y_str = coords.split(",")
                x_coord = int(x_str.strip())
                y_coord = int(y_str.strip())

                valid_placement = True
                indices = []
                for p in selected_piece_shape.get_points():
                    px, py = x_coord + p.x, y_coord + p.y
                    if not (0 <= px < WIDTH and 0 <= py < HEIGHT and self.occupancy[self.board_map[(px, py)]] != -1 ): #check if within board and not occupied
                        valid_placement = False
                        break
                    indices.append(self.board_map[(px, py)])

                if valid_placement:
                    step = Step(selected_piece_index, selected_shape_index, x_coord, y_coord)
                    step.indices = indices
                    self.pre_solution.append(step)
                    self.used_pieces.add(selected_piece_index)
                    for idx in indices: # Mark as occupied in occupancy
                        self.occupancy[idx] = -1
                    print(f"[green]Piece {selected_piece_name} placed at ({x_coord},{y_coord}).[/green]")
                    break # Valid placement, exit coordinate input loop
                else:
                    print("[red]Invalid placement: Piece out of bounds or overlaps.[/red]")

            except ValueError:
                print("[red]Invalid coordinates. Please enter X,Y as numbers separated by comma.[/red]")


    def solve(self) -> Optional[List[List[Step]]]: # Return list of solutions
        placements = []
        placements_meta = {}
        used_cell_indices = set()
        for step in self.pre_solution:
            for index in step.indices:
                used_cell_indices.add(index)

        row_id = 0
        for piece_idx in range(PIECES):
            if piece_idx in self.used_pieces:
                continue
            shapes = self.get_piece_shapes(piece_idx)
            for shape in shapes:
                for y in range(HEIGHT):
                    for x in range(WIDTH):
                        valid_placement = True
                        covered_indices = []
                        for p in shape.get_points():
                            px, py = x + p.x, y + p.y
                            if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                                valid_placement = False
                                break
                            cell_index = self.board_map[(px, py)]
                            if self.occupancy[cell_index] == -1 or cell_index in used_cell_indices: # Check against occupancy and pre-placed
                                valid_placement = False
                                break
                            covered_indices.append(cell_index)
                        if valid_placement:
                            row = sorted(covered_indices) + [TOTAL_CELLS + piece_idx] # Piece column index
                            placements.append(row)
                            placements_meta[row_id] = (piece_idx, shape.shape_index, x, y) # Key is row_id (int)
                            row_id += 1

        col_names = [f"Cell{i+1}" for i in range(TOTAL_CELLS)] + [f"Piece{PIECE_MAP[i]}" for i in range(PIECES)]
        dlx = DLX(placements, col_names)

        # Apply pre-placement constraints
        for step in self.pre_solution:
            piece_col_idx = TOTAL_CELLS + step.block_index
            if piece_col_idx < len(dlx.columns): # safety check for column index
                dlx.cover(dlx.columns[piece_col_idx])
            for index in step.indices:
                if index < len(dlx.columns): # safety check for column index
                    dlx.cover(dlx.columns[index])

        solutions_rows_list = dlx.search(max_solutions=-1) # Get all solutions

        if solutions_rows_list:
            all_solutions = []
            for solutions_rows in solutions_rows_list: # Iterate over list of solutions (each is a list of row indices)
                current_solution = self.pre_solution.copy() # Start with pre-placed pieces for each solution
                for row_index in solutions_rows: # For each row index in the current solution
                    piece_index, shape_index, x_coord, y_coord = placements_meta[row_index] # Get placement metadata
                    step = Step(piece_index, shape_index, x_coord, y_coord)
                    shape = get_piece_shapes(piece_index)[shape_index]
                    indices = []
                    for p in shape.get_points():
                        indices.append(self.board_map[(x_coord + p.x, y_coord + p.y)])
                    step.indices = indices
                    current_solution.append(step)
                all_solutions.append(current_solution) # Add the fully constructed solution
            return all_solutions
        return None


if __name__ == "__main__":
    solver = RectangularSolver()
    print("[bold blue]Rectangular Puzzle Solver[/bold blue]")
    solver.manual_placement() # Start interactive mode