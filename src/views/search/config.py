import shlex
from blessed import Terminal
from src.state import AppState
from src.ui_helpers import render_help_text

term = Terminal()


def _parse_input(entry: str) -> tuple[bool, list[str]]:
    """Parse an entry into (is_blacklist, terms).

    Handles quoted phrases as single terms and splits unquoted words individually.
    A leading '-' on the whole entry signals blacklist mode.

    Examples:
        'espn basketball'         -> (False, ['espn', 'basketball'])
        '"espn basketball"'       -> (False, ['espn basketball'])
        'espn "basketball"'       -> (False, ['espn', 'basketball'])
        '-espn basketball'        -> (True,  ['espn', 'basketball'])
        '-"espn basketball"'      -> (True,  ['espn basketball'])
    """
    is_blacklist = entry.startswith("-")
    if is_blacklist:
        entry = entry[1:]
    try:
        tokens = shlex.split(entry)
    except ValueError:
        # Unmatched quote — fall back to splitting on whitespace
        tokens = entry.replace('"', "").split()
    return is_blacklist, [t for t in tokens if t]


def render(state: AppState, current_input: str) -> None:
    if state.active_account is None:
        raise RuntimeError("Account should not be None at this point.")

    print(term.clear())

    print(term.move_xy(0, term.height - 4) + term.center(f"(Account: {state.active_account.name})  (streams) {len(state.active_account.get_streams())}  (expires) {state.active_account.get_expiration()}"))
    render_help_text(term, "(enter) confirm", "(-term) blacklist", "(r) reset to defaults", "(esc) select account")

    print(term.move_xy(0, 0) + "Include: " + (term.green(",".join(state.search_terms)) if state.search_terms else "none"))

    print(term.move_xy(0, 1) + "Exclude: " + (term.red(",".join(state.blacklist)) if state.blacklist else "none"))

    print(term.move_xy(0, 2) + f"> {current_input}_")


def run(state: AppState) -> None:
    current_input = ""

    render(state, current_input)

    while True:
        key = term.inkey()

        if key.name == "KEY_ESCAPE":
            state.current_view = "account_select"
            return
        elif key.name == "KEY_ENTER":
            if current_input == "":
                state.current_view = "results"
                return

            entry = current_input.strip()
            current_input = ""

            if not entry:
                continue

            if entry == "r":
                state.blacklist = state.default_blacklist.copy()
                state.search_terms = state.default_search_terms.copy()
            else:
                is_blacklist, tokens = _parse_input(entry)
                for token in tokens:
                    if is_blacklist:
                        if token in state.blacklist:
                            state.blacklist.remove(token)
                        elif token in state.search_terms:
                            state.search_terms.remove(token)
                            state.blacklist.append(token)
                        else:
                            state.blacklist.append(token)
                    else:
                        if token in state.search_terms:
                            state.search_terms.remove(token)
                        elif token in state.blacklist:
                            state.blacklist.remove(token)
                            state.search_terms.append(token)
                        else:
                            state.search_terms.append(token)

        elif key.name in ("KEY_BACKSPACE", "KEY_DELETE"):
            current_input = current_input[:-1]
        elif not key.is_sequence:
            current_input += str(key)

        render(state, current_input)