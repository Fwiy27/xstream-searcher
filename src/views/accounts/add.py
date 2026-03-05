from blessed import Terminal
from src.accounts import save_account, name_exists
from src.ui_helpers import render_help_text

term = Terminal()

def _read_field(label: str, y: int, secret: bool = False, error: str = "") -> str | None:
    value = ""
    while True:
        if value == "" and error:
            display = term.red(error)
        else:
            display = "*" * len(value) if secret else value
        print(term.move_xy(0, y) + term.clear_eol() + f"> {label}: {display}_")
        key = term.inkey()
        if key.name == "KEY_ESCAPE":
            return None
        elif key.name == "KEY_ENTER":
            return value
        elif key.name in ("KEY_BACKSPACE", "KEY_DELETE"):
            value = value[:-1]
            if error:
                print(term.move_xy(0, y + 1) + term.clear_eol())
                error = ""
        elif not key.is_sequence:
            value += str(key)


def run(state) -> None:
    print(term.clear())
    print(term.move_xy(0, 0) + "Add Account")
    print(term.move_xy(0, 1) + "Press enter to confirm each field")
    render_help_text(term, "(esc) cancel")

    while True:
        name = _read_field("Account name", 2)
        if name is None:
            state.current_view = "account_select"
            return
        if not name:
            continue
        if name_exists(name):
            name = _read_field("Account name", 2, error=f"'{name}' is already taken, choose another")
            if name is None:
                state.current_view = "account_select"
                return
        else:
            break

    url = _read_field("URL", 3)
    if url is None:
        state.current_view = "account_select"
        return

    username = _read_field("Username", 4)
    if username is None:
        state.current_view = "account_select"
        return

    password = _read_field("Password", 5, secret=True)
    if password is None:
        state.current_view = "account_select"
        return

    save_account(name, url, username, password)
    print(term.move_xy(0, 7) + f"Account '{name}' saved!")
    term.inkey(timeout=1.5)
    state.current_view = "account_select"