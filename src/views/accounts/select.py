from blessed import Terminal
from src.accounts import Account, load_accounts, delete_account
from src.state import AppState
from src.ui_helpers import render_help_text

term = Terminal()

def load_account_information(account: Account) -> None:
    print(term.clear())
    print(term.move_xy(0, (term.height-2) // 2) + term.center(f"Loading streams..."))
    account.get_expiration()
    account.get_streams()

def render(accounts: list[Account], selected: int, is_deleting: bool) -> None:
    print(term.clear())

    render_help_text(term, "(↑↓) navigate", "(enter) select", "(e) edit", "(d) delete", "(s) settings", "(escape) quit")

    print(term.move_xy(0, 0) + "Select an account:")

    options = [a.name for a in accounts] + ["+ Add new account"]


    start_x = 0
    start_y = 1
    for i, option in enumerate(options):
        if i == selected:
            if is_deleting:
                line = term.red(f"> {option}")
            else:
                line = f"> {option}"
        else:
            line = f"  {option}"

        if i == selected:
            print(term.move_xy(start_x, start_y + i) + term.reverse(line))
        else:
            print(term.move_xy(start_x, start_y + i) + line)



def run(state: AppState) -> None:
    accounts = load_accounts()
    selected = 0
    options_count = len(accounts) + 1
    is_deleting = False

    render(accounts, selected, is_deleting)

    while True:
        key = term.inkey()

        # Check if user is quitting app
        if key.name == "KEY_ESCAPE":
            quit()

        # Clear deleting status if not "d" again
        if key != "d":
            is_deleting = False

        if key.name == "KEY_UP":
            selected = (selected - 1) % options_count
        elif key.name == "KEY_DOWN":
            selected = (selected + 1) % options_count
        elif key.name == "KEY_ENTER":
            if selected == len(accounts):
                state.current_view = "account_add"
            else:
                state.active_account = accounts[selected]
                load_account_information(state.active_account)
                state.current_view = "search_config"
            return
        elif key == "d" and selected < len(accounts):
            if is_deleting:
                delete_account(accounts[selected].name)
                accounts = load_accounts()
                options_count = len(accounts) + 1
                selected = min(selected, options_count - 1)
                is_deleting = False
            else:
                is_deleting = True
        elif key == "e" and selected < len(accounts):
            state.account_to_edit = accounts[selected]
            state.current_view = "account_edit"
            return
        elif key == "s":
            state.current_view = "settings"
            return

        render(accounts, selected, is_deleting)