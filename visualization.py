import time
from typing import List

import inquirer
from rich.console import Console
from rich.progress import Progress
from rich.text import Text
from rich import print  # for other messages

# Global console used for output.
console = Console(force_terminal=True)

# Constants - Define parameters for the puzzle and pieces.
PIECES = 12  # Number of different puzzle pieces.
PIECE_DATA = [
    [
        0b1000,
        0b1000,
        0b1100,
        0b0000,
    ],  # Shape data for piece A (binary representation of 4x4 grid)
    [0b1000, 0b1100, 0b1100, 0b0000],  # Shape data for piece B
    [0b1000, 0b1000, 0b1000, 0b1100],  # Shape data for piece C
    [0b1000, 0b1000, 0b1100, 0b1000],  # Shape data for piece D
    [0b1000, 0b1000, 0b1100, 0b0100],  # Shape data for piece E
    [0b1000, 0b1100, 0b0000, 0b0000],  # Shape data for piece F
    [0b1000, 0b1000, 0b1110, 0b0000],  # Shape data for piece G
    [0b1000, 0b1100, 0b0110, 0b0000],  # Shape data for piece H
    [0b1100, 0b1000, 0b1100, 0b0000],  # Shape data for piece I
    [0b1000, 0b1000, 0b1000, 0b1000],  # Shape data for piece J
    [0b1100, 0b1100, 0b0000, 0b0000],  # Shape data for piece K
    [0b0100, 0b1110, 0b0100, 0b0000],  # Shape data for piece L
]
ROTATES = [
    8,
    8,
    8,
    8,
    8,
    4,
    4,
    4,
    4,
    2,
    1,
    1,
]  # Number of rotations/flips for each piece type. 8: all rotations and flips, 4: rotations only, 2: rotate 180, 1: no rotation/flip

# The mapping for piece letters, used for output and user interface.
PIECE_MAP = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]

# Instead of ANSI escapes, we use Rich markup for styled console output.
RICH_COLORS = [
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
]


# Data Structures - Define classes to represent points, steps, and pieces.
class Point:
    """Represents a point in 2D space."""

    def __init__(self, x: int, y: int):
        """Initializes a Point object.
        Args:
            x (int): The x-coordinate of the point.
            y (int): The y-coordinate of the point.
        """
        self.x = x
        self.y = y


class Step:
    """Represents a placement of a piece on the board."""

    def __init__(self, block_index: int, shape_index: int, x: int, y: int):
        """Initializes a Step object.
        Args:
            block_index (int): The index of the piece (0-11).
            shape_index (int): The index of the shape/rotation of the piece.
            x (int): The x-coordinate of the piece's placement on the board.
            y (int): The y-coordinate of the piece's placement on the board.
        """
        self.block_index = block_index
        self.shape_index = shape_index
        self.x = x
        self.y = y
        self.indices: List[int] = (
            []
        )  # indices on the board that this piece occupies, used for DLX algorithm


class Piece:
    """Represents a puzzle piece and its possible shapes."""

    WIDTH = 4  # Fixed width of the piece representation grid.
    HEIGHT = 4  # Fixed height of the piece representation grid.

    def __init__(self, data: List[int], block_index: int):
        """Initializes a Piece object from shape data.
        Args:
            data (List[int]): Binary data representing the piece's shape.
            block_index (int): The index of the piece (0-11).
        """
        self.points: List[Point] = (
            []
        )  # List of Point objects representing the filled cells of the piece.
        self.block_index = block_index
        self.shape_index = 0  # Initial shape index is 0.
        for i in range(self.HEIGHT):
            for j in range(self.WIDTH):
                if (
                    data[i] & (1 << (self.WIDTH - 1 - j))
                ) != 0:  # Check if the j-th bit from the right in data[i] is set.
                    self.points.append(
                        Point(j, i)
                    )  # Add a Point if the bit is set (representing a filled cell).
        self._normalize()  # Normalize the piece shape to start from (0,0).

    def _normalize(self):
        """Normalizes the piece shape so that its top-leftmost filled cell is at (0,0)."""
        min_x = self.WIDTH
        min_y = self.HEIGHT
        for p in self.points:
            min_x = min(min_x, p.x)  # Find the minimum x-coordinate among all points.
            min_y = min(min_y, p.y)  # Find the minimum y-coordinate among all points.
        for p in self.points:
            p.x -= min_x  # Shift all x-coordinates to start from 0.
            p.y -= min_y  # Shift all y-coordinates to start from 0.

    def flip(self):
        """Flips the piece horizontally (around the vertical center line)."""
        for p in self.points:
            p.x = (
                self.WIDTH - 1 - p.x
            )  # Reflect x-coordinate across the vertical center.
        self._normalize()  # Re-normalize after flipping.
        self.shape_index += 1  # Increment shape index to represent a different shape.

    def rotate(self):
        """Rotates the piece 90 degrees clockwise."""
        for p in self.points:
            p.x, p.y = (
                self.HEIGHT - 1 - p.y,
                p.x,
            )  # Rotate coordinates: (x, y) becomes (HEIGHT - 1 - y, x).
        self._normalize()  # Re-normalize after rotating.
        self.shape_index += 1  # Increment shape index to represent a different shape.

    def size(self) -> int:
        """Returns the number of blocks in the piece."""
        return len(self.points)

    def get_points(self) -> List[Point]:
        """Returns a list of Point objects representing the shape of the piece."""
        return self.points


# Pattern Interfaces and Triangle Pattern Implementation - Define interfaces for puzzle patterns and implement the Triangle pattern.
class IPattern:
    """Interface for puzzle patterns."""

    def size(self) -> int:
        """Returns the total number of cells in the pattern."""
        raise NotImplementedError

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        """Returns a list of valid Steps for placing a given piece on the pattern."""
        raise NotImplementedError

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        """Formats the current state of the pattern as a matrix for output."""
        raise NotImplementedError

    def is_valid_placement(
        self, piece: Piece, x: int, y: int, current_matrix: List[int]
    ) -> bool:
        """Checks if placing a piece at (x, y) is valid in the current matrix."""
        raise NotImplementedError

    def place_piece(self, piece: Piece, x: int, y: int):
        """Places a piece on the board at the given coordinates, updating the board matrix."""
        raise NotImplementedError


class TrianglePattern(IPattern):
    """Implements the Triangle puzzle pattern."""

    ORDER = 10  # Order of the triangle (side length).

    def __init__(self):
        """Initializes a TrianglePattern object."""
        self.matrix: List[int] = (
            []
        )  # 1D representation of the triangle board, using indices.
        index = 0
        for y in range(self.ORDER):
            for x in range(self.ORDER):
                if x <= y:  # Condition for cells within the triangle.
                    self.matrix.append(
                        index + 1
                    )  # Assign unique index to each cell in the triangle.
                    index += 1
                else:
                    self.matrix.append(
                        0
                    )  # Mark cells outside the triangle as 0 (invalid).
        self.original_matrix = list(
            self.matrix
        )  # Store the initial board state for resetting.

    def reset_matrix(self):
        """Resets the board matrix to its original empty state."""
        self.matrix = list(self.original_matrix)

    def size(self) -> int:
        """Returns the total number of cells in the triangle pattern."""
        return self.ORDER * (self.ORDER + 1) // 2

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        """Finds all valid placements (Steps) for a given piece on the triangle pattern."""
        steps: List[Step] = []
        for y in range(self.ORDER):
            for x in range(self.ORDER):
                valid = True
                for p in piece.get_points():
                    px, py = (
                        p.x + x,
                        p.y + y,
                    )  # Calculate board coordinates for each point of the piece.
                    if not (
                        0 <= px < self.ORDER
                        and 0 <= py < self.ORDER
                        and px <= py
                        and self.matrix[py * self.ORDER + px] != 0
                    ):
                        # Check if the piece is within the triangle boundaries and on empty cells.
                        valid = False
                        break
                if valid:
                    step = Step(
                        piece.block_index, piece.shape_index, x, y
                    )  # Create a Step object for this valid placement.
                    for p in piece.get_points():
                        step.indices.append(
                            self.matrix[(p.y + y) * self.ORDER + (p.x + x)]
                        )  # Store the indices of the board cells occupied by the piece.
                    steps.append(step)
        return steps

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        """Formats the board state (with a solution) into a 2D matrix for output."""
        # Use -1 to indicate empty cells.
        piece_matrix = [-1] * (
            self.size() + 1
        )  # Initialize a 1D matrix with -1 (empty), size + 1 to align with 1-based indexing.
        for step in solution:
            for index in step.indices:
                piece_matrix[index] = (
                    step.block_index
                )  # Fill in piece indices based on the solution steps.
        result: List[List[int]] = []
        index = 0
        for y in range(self.ORDER):
            row = []
            for x in range(self.ORDER):
                if x <= y:
                    index += 1
                    row.append(
                        piece_matrix[index]
                    )  # Add piece index or -1 for each cell in the triangle row.
            result.append(row)
        return result

    def is_valid_placement(
        self, piece: Piece, x: int, y: int, current_matrix: List[int]
    ) -> bool:
        """Checks if placing a piece at (x, y) is valid given a current board matrix."""
        for p in piece.get_points():
            px, py = p.x + x, p.y + y
            if not (
                0 <= px < self.ORDER
                and 0 <= py < self.ORDER
                and px <= py
                and current_matrix[py * self.ORDER + px] != 0
            ):
                # Check bounds and if the target cells are empty (non-zero in the matrix).
                return False
        return True


def visualize_piece_colored(piece: Piece, piece_name: str, orientation_num: int, color_index: int):
    color = RICH_COLORS[color_index % len(RICH_COLORS)]
    print(f"\nPiece [bold {color}]{piece_name}[/]: Orientation {orientation_num}")
    piece_data = [[0] * Piece.WIDTH for _ in range(Piece.HEIGHT)]
    for point in piece.get_points():
        piece_data[point.y][point.x] = 1

    cell_width = 2  # Desired width for each cell (including padding)

    for row in piece_data:
        row_segments = []
        for cell in row:
            if cell == 1:
                cell_content = "#"  # Base content for filled cell
                padded_content = f"{cell_content:<{cell_width}}" # Left-pad to cell_width
                rich_text_cell = Text(padded_content, style=color) # Apply color to the padded content
            else:
                cell_content = "."  # Base content for empty cell
                padded_content = f"{cell_content:<{cell_width}}" # Left-pad to cell_width
                rich_text_cell = Text(padded_content) # No style for empty cell, padded

            row_segments.append(rich_text_cell)
        console.print(*row_segments, sep="")  # Print segments for the row

if __name__ == "__main__":
    print("Piece Orientations Visualization:")
    for i in range(PIECES):
        piece_data = PIECE_DATA[i]
        piece_name = PIECE_MAP[i]
        rotations = ROTATES[i]
        piece = Piece(piece_data, i)
        original_piece_points = [
            Point(p.x, p.y) for p in piece.get_points()
        ]  # Store original points for reset
        orientation_count = 0

        # Visualize original orientation
        orientation_count += 1
        visualize_piece_colored(piece, piece_name, orientation_count, i)

        if rotations >= 2:
            # Rotate 180 degrees if rotations allow
            piece.rotate()
            piece.rotate()
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)
            piece = Piece(piece_data, i)  # Reset to original orientation

        if rotations >= 4:
            # Visualize 90 and 270 rotations
            piece.rotate()
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)

            piece.rotate()  # 180 already done
            piece.rotate()  # 270
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)
            piece = Piece(piece_data, i)  # Reset to original orientation

        if rotations == 8:
            # Visualize flipped versions of original and rotated 90 degrees
            piece.flip()
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)

            piece.rotate()  # Flipped and rotated 90
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)

            piece.rotate()  # Flipped and rotated 180
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)

            piece.rotate()  # Flipped and rotated 270
            orientation_count += 1
            visualize_piece_colored(piece, piece_name, orientation_count, i)
            piece = Piece(piece_data, i)  # Reset to original orientation

        print("-" * 20)
