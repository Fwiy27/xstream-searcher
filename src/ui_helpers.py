from blessed import Terminal

def render_help_text(term: Terminal, *terms: str, y_offset: int = 2, max_lines: int = 2) -> None:
    """
    Render help text at the bottom of the terminal, handling overflow gracefully.

    Args:
        term: Terminal instance
        *terms: Individual help text items (automatically joined with "   ")
        y_offset: Lines from bottom (2 = term.height - 2)
        max_lines: Maximum lines to use for wrapping
    """
    # Join terms with three spaces
    text = "   ".join(terms)
    width = term.width

    # If text fits, center it on one line
    if len(text) <= width:
        print(term.move_xy(0, term.height - y_offset) + term.center(text))
        return

    # Use the provided terms as parts
    parts = list(terms)

    if max_lines == 1:
        # Single line: truncate with ellipsis
        truncated = text[:width - 3] + "..." if len(text) > width else text
        print(term.move_xy(0, term.height - y_offset) + truncated)
        return

    # Multi-line: distribute shortcuts across lines
    lines = []
    current_line = ""

    for part in parts:
        test_line = current_line + ("   " if current_line else "") + part
        if len(test_line) <= width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = part

            # If even a single part is too long, truncate it
            if len(current_line) > width:
                current_line = current_line[:width - 3] + "..."

    if current_line:
        lines.append(current_line)

    # Limit to max_lines
    lines = lines[:max_lines]
    if len(parts) > len(lines):
        # Add ellipsis to last line if we're cutting off content
        if lines:
            lines[-1] = lines[-1][:width - 3] + "..."

    # Render lines from bottom up
    for i, line in enumerate(reversed(lines)):
        y_pos = term.height - y_offset - i
        print(term.move_xy(0, y_pos) + term.center(line))
