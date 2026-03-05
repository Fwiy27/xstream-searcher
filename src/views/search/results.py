import subprocess
import pyperclip
import threading
import json

from blessed import Terminal
from src.state import AppState
from src.search_logic import SearchTerms, search
from src.accounts import Stream, Account
from src.ui_helpers import render_help_text

term = Terminal()
PREFIX_WIDTH = 6  # "[NNN] " prefix width


def fetch_resolution(account: Account, stream: Stream, resolutions: dict, stream_id: str) -> None:
    """Fetch resolution info for a stream using ffprobe in a background thread."""
    try:
        url = stream.url(account)

        # Use ffprobe to get stream info
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 'v:0',  # First video stream
                '-i', url
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            if streams:
                width = streams[0].get('width')
                height = streams[0].get('height')
                if width and height:
                    resolutions[stream_id] = f"{width}x{height}"
                else:
                    resolutions[stream_id] = "?"
            else:
                resolutions[stream_id] = "?"
        else:
            resolutions[stream_id] = "error"
    except subprocess.TimeoutExpired:
        resolutions[stream_id] = "timeout"
    except FileNotFoundError:
        resolutions[stream_id] = "no ffprobe"
    except Exception:
        resolutions[stream_id] = "error"

def action_on_enter(account: Account, streams: list[Stream], index: int, select_action: str) -> None:
    if (0 > index or index >= len(streams)):
        return

    url = streams[index].url(account)

    # Parse comma-separated actions
    actions = [action.strip() for action in select_action.split(",")]

    for action in actions:
        if action == "iina":
            subprocess.run(["open", "-a", "IINA", url])
        elif action == "copy":
            pyperclip.copy(url)
        elif action == "mpc":
            subprocess.run(["mpc-hc.exe", url])

def render(streams: list[Stream], selected: int, scroll_offset: int, max_show: int, green: bool, resolutions: dict, fetching: set) -> None:
    print(term.move_xy(0, 0) + term.clear)

    render_help_text(term, "(enter) select", "(i) get resolution", "(esc) edit search")
    print(term.move_xy(0, 0) + "Choose a stream:")
    visible = streams[scroll_offset : scroll_offset + max_show]

    for i, stream in enumerate(visible):
        actual_index = scroll_offset + i

        # Build prefix with resolution info
        prefix = f"[{actual_index}]"

        # Add resolution if available
        if stream.stream_id in resolutions:
            res = resolutions[stream.stream_id]
            prefix += f" [{res}]"
        elif stream.stream_id in fetching:
            prefix += " [...]"  # Loading indicator

        name = stream.name
        # Calculate remaining space for name
        available_width = term.width - len(prefix) - 1
        if len(name) > available_width:
            name = name[: available_width - 1] + "…"

        is_selected = i == selected
        line = f"{prefix} {name}"

        if is_selected:
            line = term.reverse(line)
            if green:
                line = term.green(line)
        print(term.move_xy(0, 1 + i) + line)


def run(state: AppState):
    if state.active_account is None:
        raise RuntimeError("Account should not be None at this point.")

    terms = SearchTerms(state.search_terms, state.blacklist)
    result = search(state.active_account.get_streams(), terms)
    selected = 0
    scroll_offset = 0
    max_show = term.height - 2 - 1
    action_performed = False

    # Track resolution info
    resolutions: dict[str, str] = {}  # stream_id -> resolution string
    fetching: set[str] = set()  # stream_ids currently being fetched

    render(result, selected, scroll_offset, max_show, action_performed, resolutions, fetching)
    while True:
        key = term.inkey(timeout=0.1)  # Add timeout for periodic re-renders

        if not key:
            # Timeout - just re-render to update any new resolution info
            render(result, selected, scroll_offset, max_show, action_performed, resolutions, fetching)
            continue

        action_performed = False

        if key == ".":
            selected = 0
            scroll_offset = 0
        elif key == "i":
            # Fetch resolution for selected stream
            actual_index = scroll_offset + selected
            if 0 <= actual_index < len(result):
                stream = result[actual_index]
                if stream.stream_id not in resolutions and stream.stream_id not in fetching:
                    fetching.add(stream.stream_id)
                    thread = threading.Thread(
                        target=fetch_resolution,
                        args=(state.active_account, stream, resolutions, stream.stream_id),
                        daemon=True
                    )
                    thread.start()
                    # Also remove from fetching set once done (will be handled by periodic render)
                    def cleanup():
                        thread.join()
                        fetching.discard(stream.stream_id)
                    threading.Thread(target=cleanup, daemon=True).start()
        elif key.name == "KEY_UP":
            if selected > 0:
                selected -= 1
            elif scroll_offset > 0:
                scroll_offset -= 1
        elif key.name == "KEY_DOWN":
            if selected < min(max_show, len(result)) - 1:
                selected += 1
            elif scroll_offset + max_show < len(result):
                scroll_offset += 1
        elif key.name == "KEY_LEFT":
            for _ in range(5):
                if selected > 0:
                    selected -= 1
                elif scroll_offset > 0:
                    scroll_offset -= 1
        elif key.name == "KEY_RIGHT":
            for _ in range(5):
                if selected < min(max_show, len(result)) - 1:
                    selected += 1
                elif scroll_offset + max_show < len(result):
                    scroll_offset += 1
        elif key.name == "KEY_ENTER":
            actual_index = scroll_offset + selected
            action_on_enter(state.active_account, result, actual_index, state.select_action)
            action_performed = True
        elif key.name == "KEY_ESCAPE":
            state.current_view = "search_config"
            return

        render(result, selected, scroll_offset, max_show, action_performed, resolutions, fetching)