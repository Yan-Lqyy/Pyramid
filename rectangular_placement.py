import time
from typing import List
from io import StringIO

import questionary
from rich.console import Console
from rich.text import Text
from rich import print  # for messages

# Global console for output.
console = Console(force_terminal=True)

# --- Constants ---

PIECES = 12  # Total number of pieces.
PIECE_DATA = [
    [0b1000, 0b1000, 0b1100, 0b0000],  # Piece A
    [0b1000, 0b1100, 0b1100, 0b0000],  # Piece B
    [0b1000, 0b1000, 0b1000, 0b1100],  # Piece C
    [0b1000, 0b1000, 0b1100, 0b1000],  # Piece D
    [0b1000, 0b1000, 0b1100, 0b0100],  # Piece E
    [0b1000, 0b1100, 0b0000, 0b0000],  # Piece F
    [0b1000, 0b1000, 0b1110, 0b0000],  # Piece G
    [0b1000, 0b1100, 0b0110, 0b0000],  # Piece H
    [0b1100, 0b1000, 0b1100, 0b0000],  # Piece I
    [0b1000, 0b1000, 0b1000, 0b1000],  # Piece J
    [0b1100, 0b1100, 0b0000, 0b0000],  # Piece K
    [0b0100, 0b1110, 0b0100, 0b0000]   # Piece L
]
# Number of rotations/flips allowed for each piece.
ROTATES = [8, 8, 8, 8, 8, 4, 4, 4, 4, 2, 1, 1]
# Mapping piece index to letter.
PIECE_MAP = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
# Colors for visualization.
RICH_COLORS = [
    "gray50",          # A - gray
    "light_sky_blue1", # B - light blue
    "light_pink1",     # C - light pink
    "light_green",     # D - light green
    "purple",          # E - purple
    "magenta2",        # F - purplish pink
    "blue1",           # G - deep blue
    "orange1",         # H - orange
    "gainsboro",       # I - whitish gray
    "green4",          # J - deep green
    "yellow1",         # K - yellow
    "red1",            # L - red
]

# --- Data Structures ---

class Point:
    """Represents a point (cell) in a piece shape."""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"({self.x}, {self.y})"


class Step:
    """Represents the placement of a piece on the board."""
    def __init__(self, block_index: int, shape_index: int, x: int, y: int):
        self.block_index = block_index   # Which piece (0-11)
        self.shape_index = shape_index   # Which rotation/flip variant
        self.x = x  # Board column (0-indexed)
        self.y = y  # Board row (0-indexed)
        self.indices: List[int] = []  # The valid cell numbers that this piece occupies


class Piece:
    """Represents a puzzle piece and its possible rotations/flips."""
    WIDTH = 4   # Fixed 4x4 grid
    HEIGHT = 4

    def __init__(self, data: List[int], block_index: int, points=None, shape_index=0):
        self.points: List[Point] = []
        self.block_index = block_index
        self.shape_index = shape_index
        self.data_template = list(data)  # Save original data
        for i in range(self.HEIGHT):
            for j in range(self.WIDTH):
                if (data[i] & (1 << (self.WIDTH - 1 - j))) != 0:
                    self.points.append(Point(j, i))
        self._normalize()
        if points is not None:  # Allow overriding points (to copy a shape)
            self.points = points
            self.shape_index = shape_index

    def _normalize(self):
        """Shift the piece so that its top-left filled cell is at (0,0)."""
        if not self.points:
            return
        min_x = min(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        for p in self.points:
            p.x -= min_x
            p.y -= min_y

    def flip(self):
        """Flip the piece horizontally."""
        for p in self.points:
            p.x = self.WIDTH - 1 - p.x
        self._normalize()
        self.shape_index += 1

    def rotate(self):
        """Rotate the piece 90° clockwise."""
        new_points = []
        for p in self.points:
            new_points.append(Point(self.HEIGHT - 1 - p.y, p.x))
        self.points = new_points
        self._normalize()
        self.shape_index += 1

    def size(self) -> int:
        return len(self.points)

    def get_points(self) -> List[Point]:
        return self.points

    def __repr__(self):
        return f"Piece {PIECE_MAP[self.block_index]}, Shape {self.shape_index}, Points: {self.points}"


# --- Pattern Interfaces and Rectangular Pattern Implementation ---

class IPattern:
    """Interface for puzzle patterns."""
    def size(self) -> int:
        raise NotImplementedError

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        raise NotImplementedError

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        raise NotImplementedError

    def is_valid_placement(self, piece: Piece, x: int, y: int, current_matrix: List[int]) -> bool:
        raise NotImplementedError


class RectangularPattern(IPattern):
    """
    Implements a rectangular board.
    
    The board has a fixed width and height (in this example, width=11 and height=5).
    The board cells are numbered from 1 to (width * height). A cell is free if its number
    is nonzero, and when a piece is placed the corresponding cells are set to 0.
    """
    WIDTH = 11
    HEIGHT = 5

    def __init__(self):
        # Create a board with cells numbered 1..(WIDTH*HEIGHT)
        self.matrix: List[int] = [i for i in range(1, self.WIDTH * self.HEIGHT + 1)]
        # Save an unmodified copy.
        self.original_matrix = list(self.matrix)
        # occupancy is used to check free/occupied cells.
        self.occupancy = list(self.matrix)

    def reset_matrix(self):
        self.occupancy = list(self.matrix)

    def size(self) -> int:
        return self.WIDTH * self.HEIGHT

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        steps: List[Step] = []
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                valid = True
                for p in piece.get_points():
                    px, py = p.x + x, p.y + y
                    if not (0 <= px < self.WIDTH and 0 <= py < self.HEIGHT and self.occupancy[py * self.WIDTH + px] != 0):
                        valid = False
                        break
                if valid:
                    step = Step(piece.block_index, piece.shape_index, x, y)
                    for p in piece.get_points():
                        step.indices.append(self.original_matrix[(p.y + y) * self.WIDTH + (p.x + x)])
                    steps.append(step)
        return steps

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        """
        Build a display matrix from the solution steps.
        For each cell (numbered from 1 to N), if a piece was placed there,
        replace the cell number with the piece’s index; otherwise show -1.
        """
        board_display = [-1] * (self.size() + 1)  # Index 0 unused.
        for step in solution:
            for cell in step.indices:
                board_display[cell] = step.block_index
        result: List[List[int]] = []
        cell_num = 1
        for row in range(self.HEIGHT):
            current_row = []
            for col in range(self.WIDTH):
                current_row.append(board_display[cell_num])
                cell_num += 1
            result.append(current_row)
        return result

    def is_valid_placement(self, piece: Piece, x: int, y: int, current_matrix: List[int]) -> bool:
        """Checks if a piece placement is valid at the given coordinates."""
        for p in piece.get_points():
            px, py = p.x + x, p.y + y
            if not (0 <= px < self.WIDTH and 0 <= py < self.HEIGHT and current_matrix[py * self.WIDTH + px] != 0):
                return False
        return True

    def place_piece(self, piece: Piece, x: int, y: int) -> bool:
        """
        Attempt to place a piece at (x, y) by marking its occupied cells in the occupancy board.
        Returns True if placement is successful.
        """
        if not self.is_valid_placement(piece, x, y, self.occupancy):
            print("[bold red]Invalid placement in place_piece[/bold red]")
            return False

        print(f"[dim]Placing piece at ({x},{y})[/dim]")
        for p in piece.get_points():
            px, py = p.x + x, p.y + y
            matrix_index = py * self.WIDTH + px
            print(f"[dim]  - Point ({px},{py}), Matrix Index: {matrix_index}[/dim]")
            if 0 <= matrix_index < len(self.occupancy):
                self.occupancy[matrix_index] = 0  # Mark cell as occupied.
            else:
                print(f"[bold red]Matrix index {matrix_index} out of bounds![/bold red]")
                return False
        return True

    def is_board_full(self) -> bool:
        """Checks if all cells on the board have been filled."""
        return all(cell == 0 for cell in self.occupancy)


# --- Output Functions ---

def visualize_board_colored(pattern: RectangularPattern, solution: List[Step] = None):
    """Visualize the rectangular board using Rich markup."""
    board_matrix = pattern.format_matrix(solution if solution else [])
    cell_width = 2
    print("\n[bold]Current Board State:[/bold]")
    for row in board_matrix:
        row_segments = []
        for piece_index in row:
            if piece_index == -1:
                padded = f"{'.':<{cell_width}}"
                cell_text = Text(padded)
            else:
                piece_letter = PIECE_MAP[piece_index]
                color = RICH_COLORS[piece_index % len(RICH_COLORS)]
                padded = f"{piece_letter:<{cell_width}}"
                cell_text = Text(padded, style=color)
            row_segments.append(cell_text)
        console.print(*row_segments, sep=" ")

def display_board(pattern: RectangularPattern, pre_placed_solution: List[Step] = None):
    visualize_board_colored(pattern, pre_placed_solution)


def visualize_piece_shape(piece: Piece) -> str:
    """
    Visualize a piece shape as a 4x4 grid string with proper spacing and coloring.
    We use the same cell width (2 characters per cell) and Rich markup.
    """
    cell_width = 2
    piece_color = RICH_COLORS[piece.block_index % len(RICH_COLORS)]
    piece_letter = PIECE_MAP[piece.block_index]
    lines = []
    for y in range(Piece.HEIGHT):
        line = ""
        for x in range(Piece.WIDTH):
            if any(p.x == x and p.y == y for p in piece.get_points()):
                padded = f"[{piece_color}]{piece_letter:<{cell_width}}[/]"
            else:
                padded = " " * cell_width
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
    print(f"\n[bold magenta]Shapes generated for Piece {PIECE_MAP[block_index]}:[/bold magenta]")
    for i, shape in enumerate(shapes):
        print(f"  Shape {i+1}: {shape}")
    return shapes


# --- Main Interactive Loop ---

def main():
    pattern = RectangularPattern()  # Create the rectangular board.
    pre_placed_solution: List[Step] = []  # List to store placements.
    used_piece_indices = set()  # To avoid placing the same piece twice.

    print("[bold blue]Rectangular Board Puzzle Solver - Placement Debug[/bold blue]")

    while True:
        display_board(pattern, pre_placed_solution)

        # Check for victory condition.
        if len(used_piece_indices) == PIECES and pattern.is_board_full():
            print("[bold green]Congratulations! You've solved the puzzle![/bold green]")
            break

        # Determine available pieces.
        available_pieces = [(piece_name, index) for index, piece_name in enumerate(PIECE_MAP)
                            if index not in used_piece_indices]
        if not available_pieces:
            print("[bold yellow]All pieces are used or pre-placed.[/bold yellow]")
            time.sleep(2)
            continue

        # Build piece choices as just the letter.
        piece_choices = [name for name, index in available_pieces]

        selected_piece_choice = questionary.autocomplete(
            "Choose a piece to place:",
            choices=piece_choices,
            validate=lambda text: True,
            style=questionary.Style([
                ('answer', 'fg:#f44336 bold'),
            ])
        ).ask()

        if not selected_piece_choice:
            continue  # If cancelled, re-prompt

        # Normalize to uppercase so input is case-insensitive.
        selected_piece_name = selected_piece_choice.strip().upper()
        if selected_piece_name not in PIECE_MAP:
            print(f"[red]Invalid piece '{selected_piece_choice}'. Please choose one of {', '.join(PIECE_MAP)}.[/red]")
            continue
        selected_piece_index = PIECE_MAP.index(selected_piece_name)
        piece_shapes = get_piece_shapes(selected_piece_index)

        print(f"\nAvailable shapes for Piece {selected_piece_name}:")
        for i, shape in enumerate(piece_shapes):
            print(f"[bold]Shape {i+1}:[/bold]\n{visualize_piece_shape(shape)}")

        # For shape selection, use numbers as strings.
        shape_choices = [str(i+1) for i in range(len(piece_shapes))]

        selected_shape_choice = questionary.autocomplete(
            f"Choose shape for piece {selected_piece_name}:",
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

        # Loop until valid coordinates are entered.
        while True:
            coords = questionary.text("Enter X and Y coordinates separated by a comma (e.g., 0,0):").ask()
            if not coords:
                break  # Allow canceling coordinate input to go back to shape selection.
            try:
                x_str, y_str = coords.split(",")
                x_coord = int(x_str.strip())
                y_coord = int(y_str.strip())
                if pattern.place_piece(selected_piece_shape, x_coord, y_coord):
                    pre_placed_step = Step(selected_piece_index, selected_piece_shape.shape_index, x_coord, y_coord)
                    for p in selected_piece_shape.get_points():
                        idx = pattern.original_matrix[(p.y + y_coord) * pattern.WIDTH + (p.x + x_coord)]
                        pre_placed_step.indices.append(idx)
                    pre_placed_solution.append(pre_placed_step)
                    used_piece_indices.add(selected_piece_index)
                    print(f"[green]Piece {selected_piece_name} placed at ({x_coord},{y_coord}).[/green]")
                    break
                else:
                    print("[red]Invalid placement. Piece out of bounds or overlaps. Try again.[/red]")
            except ValueError:
                print("[red]Invalid coordinates. Please enter numbers separated by a comma (e.g., 0,0).[/red]")


if __name__ == "__main__":
    main()
