from blessed import Terminal
from src.accounts import save_account, name_exists, Account, delete_account
from src.state import AppState
from src.ui_helpers import render_help_text

term = Terminal()

def _read_field(label: str, y: int, secret: bool = False, error: str = "", default: str = "") -> str | None:
    value = default
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


def run(state: AppState) -> None:
    if state.account_to_edit is None:
        state.current_view = "account_select"
        return

    account = state.account_to_edit
    original_name = account.name

    print(term.clear())
    print(term.move_xy(0, 0) + f"Edit Account: {original_name}")
    print(term.move_xy(0, 1) + "Press enter to confirm each field")
    render_help_text(term, "(esc) cancel")

    while True:
        name = _read_field("Account name", 2, default=original_name)
        if name is None:
            state.current_view = "account_select"
            return
        if not name:
            continue
        # Check if name exists and it's not the original name
        if name != original_name and name_exists(name):
            name = _read_field("Account name", 2, error=f"'{name}' is already taken, choose another", default=original_name)
            if name is None:
                state.current_view = "account_select"
                return
        else:
            break

    url = _read_field("URL", 3, default=account.url)
    if url is None:
        state.current_view = "account_select"
        return

    username = _read_field("Username", 4, default=account.username)
    if username is None:
        state.current_view = "account_select"
        return

    # For password, start with empty but allow user to keep existing
    print(term.move_xy(0, 5) + term.clear_eol() + "> Password: (leave empty to keep current)")
    password = _read_field("Password", 6, secret=True)
    if password is None:
        state.current_view = "account_select"
        return

    # If name changed, delete the old account first
    if name != original_name:
        delete_account(original_name)

    # Use existing password if user didn't provide a new one
    if not password:
        password = account.password

    save_account(name, url, username, password)
    print(term.move_xy(0, 8) + f"Account '{name}' updated!")
    term.inkey(timeout=1.5)
    state.current_view = "account_select"
