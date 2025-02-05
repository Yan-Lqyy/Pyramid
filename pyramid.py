import time
from typing import List, Tuple, Optional

import inquirer
from rich import print
from rich.console import Console
from rich.progress import Progress

# Constants - Same as before
PIECES = 12
PIECE_DATA = [
    [0b1000, 0b1000, 0b1100, 0b0000],
    [0b1000, 0b1100, 0b1100, 0b0000],
    [0b1000, 0b1000, 0b1000, 0b1100],
    [0b1000, 0b1000, 0b1100, 0b1000],
    [0b1000, 0b1000, 0b1100, 0b0100],
    [0b1000, 0b1100, 0b0000, 0b0000],
    [0b1000, 0b1000, 0b1110, 0b0000],
    [0b1000, 0b1100, 0b0110, 0b0000],
    [0b1100, 0b1000, 0b1100, 0b0000],
    [0b1000, 0b1000, 0b1000, 0b1000],
    [0b1100, 0b1100, 0b0000, 0b0000],
    [0b0100, 0b1110, 0b0100, 0b0000]
]
ROTATES = [8, 8, 8, 8, 8, 4, 4, 4, 4, 2, 1, 1]
FACTOR = 3

PIECE_MAP = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
ANSI_COLOR = [
    "\033[1;37m",  # White
    "\033[1;31m",  # Red
    "\033[1;32m",  # Green
    "\033[0;32m",  # Green dim
    "\033[1;33m",  # Yellow
    "\033[0;33m",  # Yellow dim
    "\033[1;34m",  # Blue
    "\033[0;34m",  # Blue dim
    "\033[1;35m",  # Magenta
    "\033[0;35m",  # Magenta dim
    "\033[1;36m",  # Cyan
    "\033[0;36m",  # Cyan dim
    "\033[0m"     # Reset
]


# Data Structures - Same as before
class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

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

    def __init__(self, data: List[int], block_index: int):
        self.points: List[Point] = []
        self.block_index = block_index
        self.shape_index = 0
        for i in range(self.HEIGHT):
            for j in range(self.WIDTH):
                if (data[i] & (1 << (self.WIDTH - 1 - j))) != 0:
                    self.points.append(Point(j, i))
        self._normalize()

    def _normalize(self):
        min_x = self.WIDTH
        min_y = self.HEIGHT
        for p in self.points:
            min_x = min(min_x, p.x)
            min_y = min(min_y, p.y)
        for p in self.points:
            p.x -= min_x
            p.y -= min_y

    def flip(self):
        for p in self.points:
            p.x = self.WIDTH - 1 - p.x
        self._normalize()
        self.shape_index += 1

    def rotate(self):
        for p in self.points:
            p.x, p.y = self.HEIGHT - 1 - p.y, p.x
        self._normalize()
        self.shape_index += 1

    def size(self) -> int:
        return len(self.points)

    def get_points(self) -> List[Point]:
        return self.points


# Pattern Interfaces and Implementations - Same as before
class IPattern:
    def size(self) -> int:
        raise NotImplementedError

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        raise NotImplementedError

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        raise NotImplementedError


class TrianglePattern(IPattern):
    ORDER = 10

    def __init__(self):
        self.matrix: List[int] = []
        index = 0
        for y in range(self.ORDER):
            for x in range(self.ORDER):
                if x <= y:
                    self.matrix.append(index + 1)
                    index += 1
                else:
                    self.matrix.append(0)

    def size(self) -> int:
        return self.ORDER * (self.ORDER + 1) // 2

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        steps: List[Step] = []
        count = 0
        for y in range(self.ORDER):
            for x in range(self.ORDER):
                valid = True
                for p in piece.get_points():
                    if not (0 <= p.x + x < self.ORDER and 0 <= p.y + y < self.ORDER and self.matrix[(p.y + y) * self.ORDER + p.x + x] != 0):
                        valid = False
                        break
                if valid:
                    step = Step(piece.block_index, piece.shape_index, x, y)
                    for p in piece.get_points():
                        step.indices.append(self.matrix[(p.y + y) * self.ORDER + p.x + x])
                    steps.append(step)
                    count += 1
        return steps

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        piece_matrix = [0] * (self.size() + 1)
        for step in solution:
            for index in step.indices:
                piece_matrix[index] = step.block_index

        result: List[List[int]] = []
        index = 0
        for y in range(self.ORDER):
            result.append([])
            for x in range(self.ORDER):
                if x <= y:
                    index += 1
                    result[y].append(piece_matrix[index])
        return result


class RectanglePattern(IPattern):
    WIDTH = 11
    HEIGHT = 5

    def __init__(self):
        self.matrix: List[int] = []
        index = 0
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self.matrix.append(index + 1)
                index += 1

    def size(self) -> int:
        return self.WIDTH * self.HEIGHT

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        steps: List[Step] = []
        count = 0
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                valid = True
                for p in piece.get_points():
                    if not (0 <= p.x + x < self.WIDTH and 0 <= p.y + y < self.HEIGHT and self.matrix[(p.y + y) * self.WIDTH + p.x + x] != 0):
                        valid = False
                        break
                if valid:
                    step = Step(piece.block_index, piece.shape_index, x, y)
                    for p in piece.get_points():
                        step.indices.append(self.matrix[(p.y + y) * self.WIDTH + p.x + x])
                    steps.append(step)
                    count += 1
        return steps

    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        piece_matrix = [0] * (self.size() + 1)
        for step in solution:
            for index in step.indices:
                piece_matrix[index] = step.block_index

        result: List[List[int]] = []
        index = 0
        for y in range(self.HEIGHT):
            result.append([])
            for x in range(self.WIDTH):
                index += 1
                result[y].append(piece_matrix[index])
        return result


class PyramidPattern(IPattern):
    def __init__(self, order: int):
        self.ORDER = order
        self.floors: List[List[int]] = [[] for _ in range(self.ORDER)]
        self.diagonals_left: List[List[int]] = [[] for _ in range(2 * self.ORDER - 1)]
        self.diagonals_right: List[List[int]] = [[] for _ in range(2 * self.ORDER - 1)]

        index = 0
        for floor in range(self.ORDER):
            for y in range(floor + 1):
                for x in range(floor + 1):
                    self.floors[floor].append(index + 1)
                    index += 1

        for plane in range(2 * self.ORDER - 1):
            size = self.ORDER - abs(self.ORDER - 1 - plane)
            for y in range(size):
                for x in range(size):
                    if x <= y:
                        floor = self.ORDER - 1 - (y - x)
                        offset = plane - self.ORDER + 1
                        if offset < 0:
                            self.diagonals_left[plane].append(self.floors[floor][x * (floor + 1) + floor + offset - x])
                            self.diagonals_right[plane].append(self.floors[floor][(floor + offset - x) * (floor + 1) + floor - x])
                        else:
                            self.diagonals_left[plane].append(self.floors[floor][(x + offset) * (floor + 1) + floor - x])
                            self.diagonals_right[plane].append(self.floors[floor][(floor - x) * (floor + 1) + floor - offset - x])
                    else:
                        self.diagonals_left[plane].append(0)
                        self.diagonals_right[plane].append(0)

    def size(self) -> int:
        return self.ORDER * (self.ORDER + 1) * (self.ORDER * 2 + 1) // 6

    def get_valid_steps(self, piece: Piece) -> List[Step]:
        steps: List[Step] = []
        count = 0
        for floor in range(self.ORDER):
            for y in range(floor + 1):
                for x in range(floor + 1):
                    valid = True
                    for p in piece.get_points():
                        if not (0 <= p.x + x <= floor and 0 <= p.y + y <= floor and self.floors[floor][(p.y + y) * (floor + 1) + p.x + x] != 0):
                            valid = False
                            break
                    if valid:
                        step = Step(piece.block_index, (floor << 3) | piece.shape_index, x, y)
                        for p in piece.get_points():
                            step.indices.append(self.floors[floor][(p.y + y) * (floor + 1) + p.x + x])
                        steps.append(step)
                        count += 1

        for plane in range(2 * self.ORDER - 1):
            size = self.ORDER - abs(self.ORDER - 1 - plane)
            for y in range(size):
                for x in range(size):
                    valid = True
                    for p in piece.get_points():
                        if not (0 <= p.x + x < size and 0 <= p.y + y < size and self.diagonals_left[plane][(p.y + y) * size + p.x + x] != 0):
                            valid = False
                            break
                    if valid:
                        step = Step(piece.block_index, (1 << 6) | (plane << 3) | piece.shape_index, x, y)
                        for p in piece.get_points():
                            step.indices.append(self.diagonals_left[plane][(p.y + y) * size + p.x + x])
                        steps.append(step)
                        count += 1

        for plane in range(2 * self.ORDER - 1):
            size = self.ORDER - abs(self.ORDER - 1 - plane)
            for y in range(size):
                for x in range(size):
                    valid = True
                    for p in piece.get_points():
                        if not (0 <= p.x + x < size and 0 <= p.y + y < size and self.diagonals_right[plane][(p.y + y) * size + p.x + x] != 0):
                            valid = False
                            break
                    if valid:
                        step = Step(piece.block_index, (1 << 7) | (plane << 3) | piece.shape_index, x, y)
                        for p in piece.get_points():
                            step.indices.append(self.diagonals_right[plane][(p.y + y) * size + p.x + x])
                        steps.append(step)
                        count += 1
        return steps


    def format_matrix(self, solution: List[Step]) -> List[List[int]]:
        piece_matrix = [0] * (self.size() + 1)
        for step in solution:
            for index in step.indices:
                piece_matrix[index] = step.block_index

        result: List[List[int]] = []
        for i in range(self.ORDER):
            result.append([])
            for j in range(self.ORDER):
                for k in range(j + 1):
                    if j >= i:
                        result[i].append(piece_matrix[self.floors[j][i * (j + 1) + k]])
                    else:
                        result[i].append(-1)
                result[i].append(-1) # Separator
        return result



# Dancing Links X Algorithm - Same as before
class DancingLinkX:
    def __init__(self, node_count: int, row_count: int, column_count: int, is_complete: bool):
        self.left: List[int] = [0] * node_count
        self.right: List[int] = [0] * node_count
        self.up: List[int] = [0] * node_count
        self.down: List[int] = [0] * node_count

        self.column: List[int] = [0] * node_count
        self.row: List[int] = [0] * node_count

        self.count: List[int] = [0] * (column_count + 1)
        self.header: List[int] = [0] * (row_count + 1)

        self.counter: int = column_count

        self.answer: List[int] = []
        self.answers: List[List[int]] = []

        self.max_column = column_count if is_complete else column_count - PIECES

        for i in range(column_count + 1):
            self.left[i] = column_count if i == 0 else i - 1
            self.right[i] = 0 if i == column_count else i + 1
            self.up[i] = i
            self.down[i] = i

            self.column[i] = i
            self.row[i] = 0

            self.count[i] = 0

    def link(self, row: int, col: int):
        self.counter += 1
        self.column[self.counter] = col
        self.row[self.counter] = row
        self.count[col] += 1

        self.up[self.counter] = self.up[col]
        self.down[self.counter] = col
        self.down[self.up[col]] = self.counter
        self.up[col] = self.counter

        if self.header[row] == 0:
            self.header[row] = self.counter
            self.left[self.counter] = self.counter
            self.right[self.counter] = self.counter
        else:
            self.left[self.counter] = self.left[self.header[row]]
            self.right[self.counter] = self.header[row]
            self.right[self.left[self.header[row]]] = self.counter
            self.left[self.header[row]] = self.counter

    def known_step(self, index: int):
        self._delete(self.column[self.header[index]])
        self.answer.append(index)
        i = self.right[self.header[index]]
        while i != self.header[index]:
            self._delete(self.column[i])
            i = self.right[i]
        return

    def _delete(self, col: int):
        self.right[self.left[col]] = self.right[col]
        self.left[self.right[col]] = self.left[col]
        i = self.down[col]
        while i != col:
            j = self.right[i]
            while j != i:
                self.up[self.down[j]] = self.up[j]
                self.down[self.up[j]] = self.down[j]
                self.count[self.column[j]] -= 1
                j = self.right[j]
            i = self.down[i]

    def recover(self, col: int):
        i = self.up[col]
        while i != col:
            j = self.left[i]
            while j != i:
                self.up[self.down[j]] = j
                self.down[self.up[j]] = j
                self.count[self.column[j]] += 1
                j = self.left[j]
            i = self.up[i]
        self.right[self.left[col]] = col
        self.left[self.right[col]] = col

    def spread(self, level: int, level_needed: int, steps_list: List[List[int]]):
        if level >= level_needed:
            steps = list(self.answer)
            steps_list.append(steps)
            return

        now = self.right[0]
        least_count = float('inf')
        i = self.right[0]
        while i != 0 and i <= self.max_column:
            if self.count[i] < least_count:
                least_count = self.count[i]
                now = i
            i = self.right[i]

        self._delete(now)
        i = self.down[now]
        while i != now:
            self.answer.append(self.row[i])
            j = self.right[i]
            while j != i:
                self._delete(self.column[j])
                j = self.right[j]

            self.spread(level + 1, level_needed, steps_list)

            j = self.left[i]
            while j != i:
                self.recover(self.column[j])
                j = self.left[j]
            self.answer.pop()
            i = self.down[i]
        self.recover(now)
        return


    def dance(self):
        now = self.right[0]
        if now == 0 or now > self.max_column:
            result = list(self.answer)
            self.answers.append(result)
            return

        least_count = float('inf')
        i = self.right[0]
        while i != 0 and i <= self.max_column:
            if self.count[i] < least_count:
                least_count = self.count[i]
                now = i
            i = self.right[i]

        self._delete(now)
        i = self.down[now]
        while i != now:
            self.answer.append(self.row[i])
            j = self.right[i]
            while j != i:
                self._delete(self.column[j])
                j = self.right[j]

            self.dance()

            j = self.left[i]
            while j != i:
                self.recover(self.column[j])
                j = self.left[j]
            self.answer.pop()
            i = self.down[i]
        self.recover(now)
        return

    def get_result(self) -> List[List[int]]:
        return self.answers


# Output functions - Using rich for console output
def output_to_console(matrix: List[List[int]]):
    for line in matrix:
        for block_index in line:
            if block_index == -1:
                print(" ", end="")
            else:
                print(f"{ANSI_COLOR[block_index]}{PIECE_MAP[block_index]}{ANSI_COLOR[PIECES]}", end="")
        print()
    print()

def output_to_file(matrix: List[List[int]], filename: str):
    with open(filename, 'w') as fout:
        for line in matrix:
            for block_index in line:
                if block_index == -1:
                    fout.write(" ")
                else:
                    fout.write(PIECE_MAP[block_index])
            fout.write("\n")
        fout.write("\n")


def main():
    console = Console()

    questions = [
        inquirer.List('pattern_type',
                      message="Choose the puzzle pattern type:",
                      choices=['Triangle Pattern (t)', 'Rectangle Pattern (r)', '4-Level Pyramid Pattern (p4)', '5-Level Pyramid Pattern (p5)'],
                      carousel=True),
        inquirer.Confirm('output_to_file',
                         message="Do you want to save the solution(s) to a file?",
                         default=False),
        inquirer.Text('output_filename',
                      message="Enter the output filename:",
                      validate=lambda _, x: x != '' if questions[1]['output_to_file'] else True, # Require filename if output_to_file is True
                      ignore=lambda answers: not answers['output_to_file']), # Only ask if output_to_file is True
        inquirer.Text('level', # Changed from inquirer.Number to inquirer.Text
                        message=f"Enter spread level for decomposition (1-12, default: {FACTOR}):",
                        default=str(FACTOR), # Default should be string for Text input
                        validate=lambda _, x: x.isdigit() and 1 <= int(x) <= 12
                        )
    ]

    answers = inquirer.prompt(questions) # Removed console=console argument

    if not answers: # User cancelled the prompts
        print("[bold red]Operation cancelled by user.[/bold red]")
        return 0

    pattern_type_choice = answers['pattern_type']
    output_to_file_choice = answers['output_to_file']
    output_filename = answers['output_filename']
    level_str = answers['level']
    level = int(level_str)

    pattern: Optional[IPattern] = None
    if pattern_type_choice == 'Triangle Pattern (t)':
        print("[bold blue]Solving Triangle Pattern Puzzle...[/bold blue]")
        pattern = TrianglePattern()
    elif pattern_type_choice == 'Rectangle Pattern (r)':
        print("[bold blue]Solving Rectangle Pattern Puzzle...[/bold blue]")
        pattern = RectanglePattern()
    elif pattern_type_choice == '4-Level Pyramid Pattern (p4)':
        print("[bold blue]Solving 4-Level Pyramid Pattern Puzzle (Order 4)...[/bold blue]")
        pattern = PyramidPattern(4)
    elif pattern_type_choice == '5-Level Pyramid Pattern (p5)':
        print("[bold blue]Solving 5-Level Pyramid Pattern Puzzle (Order 5)...[/bold blue]")
        pattern = PyramidPattern(5)
    else:
        print("[bold red]Error: Invalid pattern type selected.[/bold red]")
        return 1

    print(f"[dim]Spread Level: {level}[/dim]")

    start_time = time.time()

    pieces: List[Piece] = []
    piece_node_count = 0
    for block_index in range(PIECES):
        piece = Piece(PIECE_DATA[block_index], block_index)
        pieces.append(piece)
        piece_node_count += piece.size()
        rotations = ROTATES[block_index]
        if rotations == 8:
            for _ in range(3):
                piece.rotate()
                pieces.append(Piece(PIECE_DATA[block_index], block_index))
                pieces[-1].shape_index = piece.shape_index
            piece.flip()
            pieces.append(Piece(PIECE_DATA[block_index], block_index))
            pieces[-1].shape_index = piece.shape_index
            for _ in range(3):
                piece.rotate()
                pieces.append(Piece(PIECE_DATA[block_index], block_index))
                pieces[-1].shape_index = piece.shape_index
        elif rotations == 4:
            for _ in range(3):
                piece.rotate()
                pieces.append(Piece(PIECE_DATA[block_index], block_index))
                pieces[-1].shape_index = piece.shape_index
        elif rotations == 2:
            piece.rotate()
            pieces.append(Piece(PIECE_DATA[block_index], block_index))
            pieces[-1].shape_index = piece.shape_index
        elif rotations == 1:
            pass

    steps: List[Step] = []
    for piece in pieces:
        steps.extend(pattern.get_valid_steps(piece))

    node_count = 0
    for step in steps:
        node_count += len(step.indices) + 1
    node_count += PIECES + pattern.size() + 1

    dlx = DancingLinkX(node_count, len(steps), pattern.size() + PIECES, (pattern.size() == piece_node_count))
    for i in range(len(steps)):
        for index in steps[i].indices:
            dlx.link(i + 1, index)
        dlx.link(i + 1, steps[i].block_index + pattern.size() + 1)

    steps_list: List[List[int]] = []
    dlx.spread(0, level, steps_list)

    results: List[List[int]] = []

    with Progress(console=console, transient=True) as progress:
        task = progress.add_task("[cyan]Solving puzzle...", total=len(steps_list))
        for step_set in steps_list:
            clone_dlx = DancingLinkX(node_count, len(steps), pattern.size() + PIECES, (pattern.size() == piece_node_count))
            clone_dlx.left = list(dlx.left)
            clone_dlx.right = list(dlx.right)
            clone_dlx.up = list(dlx.up)
            clone_dlx.down = list(dlx.down)
            clone_dlx.column = list(dlx.column)
            clone_dlx.row = list(dlx.row)
            clone_dlx.count = list(dlx.count)
            clone_dlx.header = list(dlx.header)
            clone_dlx.counter = dlx.counter
            clone_dlx.max_column = dlx.max_column

            for step_index in step_set:
                clone_dlx.known_step(step_index)
            clone_dlx.dance()
            results.extend(clone_dlx.get_result())
            progress.advance(task)

    end_time = time.time()
    duration = end_time - start_time

    solutions_steps: List[List[Step]] = []
    for result_indices in results:
        solution_step_list: List[Step] = []
        for index in result_indices:
            solution_step_list.append(steps[index - 1])
        solution_step_list.sort(key=lambda step: step.block_index)
        solutions_steps.append(solution_step_list)

    solutions_steps.sort(key=lambda solution: [(s.shape_index, s.x, s.y) for s in solution])

    if not solutions_steps:
        print("[bold yellow]No solution found.[/bold yellow]")
    else:
        print(f"[bold green]{len(solutions_steps)} solution(s) found.[/bold green]")

    print(f"[dim]Time Spend: {duration:.3f} Seconds[/dim]")

    if output_to_file_choice:
        print(f"[magenta]Outputting solution(s) to '{output_filename}'...[/magenta]")
        if not solutions_steps:
            output_to_file([["No solution found."]], output_filename)
        else:
            output_to_file([[f"{len(solutions_steps)} solution(s) found."]], output_filename)
            for solution in solutions_steps:
                output_to_file(pattern.format_matrix(solution), output_filename)
        print("[green]Output Complete.[/green]")
    else:
        if solutions_steps:
            print("[bold magenta]Solutions:[/bold magenta]")
            for solution in solutions_steps:
                output_to_console(pattern.format_matrix(solution))
        else:
            print() # Just to add a newline if no solutions were printed


    return 0

if __name__ == "__main__":
    main()