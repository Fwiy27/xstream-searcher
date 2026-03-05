import subprocess
import pyperclip

from blessed import Terminal
from src.state import AppState
from src.search_logic import SearchTerms, search
from src.accounts import Stream, Account
from src.ui_helpers import render_help_text

term = Terminal()
PREFIX_WIDTH = 6  # "[NNN] " prefix width

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

def render(streams: list[Stream], selected: int, scroll_offset: int, max_show: int, green: bool) -> None:
    print(term.move_xy(0, 0) + term.clear)

    render_help_text(term, "(enter) select", "(esc) edit search")
    print(term.move_xy(0, 0) + "Choose a stream:")
    visible = streams[scroll_offset : scroll_offset + max_show]
    max_name_len = term.width - PREFIX_WIDTH

    for i, stream in enumerate(visible):
        name = stream.name
        if len(name) > max_name_len:
            name = name[: max_name_len - 1] + "…"

        actual_index = scroll_offset + i
        is_selected = i == selected
        line = f"[{actual_index}] {name}"

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

    render(result, selected, scroll_offset, max_show, action_performed)
    while True:
        key = term.inkey()

        action_performed = False

        if key == ".":
            selected = 0
            scroll_offset = 0
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

        render(result, selected, scroll_offset, max_show, action_performed)