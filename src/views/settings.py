import shlex
from blessed import Terminal
from src.state import AppState
from src import accounts

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


def render(state: AppState, current_input: str, editing_field: str, message: str = "") -> None:
    print(term.clear())

    # Instructions
    print(term.move_xy(0, term.height - 4) + term.center("(tab) next field   (enter) save   (r) clear cache   (esc) cancel"))

    if message:
        print(term.move_xy(0, term.height - 2) + term.center(term.green(message)))

    # Field displays
    y = 0

    # Cache hours
    cache_color = term.bold_cyan if editing_field == "cache_hours" else term.normal
    print(term.move_xy(0, y) + cache_color + "Cache Hours: " + term.normal + f"{state.cache_hours}")
    if editing_field == "cache_hours":
        print(term.move_xy(0, y + 1) + f"> {current_input}_")
        y += 2
    else:
        y += 1

    y += 1

    # Default include
    include_color = term.bold_cyan if editing_field == "default_search_terms" else term.normal
    print(term.move_xy(0, y) + include_color + "Default Include: " + term.normal +
          (term.green(",".join(state.default_search_terms)) if state.default_search_terms else "none"))
    if editing_field == "default_search_terms":
        print(term.move_xy(0, y + 1) + f"> {current_input}_")
        y += 2
    else:
        y += 1

    y += 1

    # Default exclude
    exclude_color = term.bold_cyan if editing_field == "default_blacklist" else term.normal
    print(term.move_xy(0, y) + exclude_color + "Default Exclude: " + term.normal +
          (term.red(",".join(state.default_blacklist)) if state.default_blacklist else "none"))
    if editing_field == "default_blacklist":
        print(term.move_xy(0, y + 1) + f"> {current_input}_")
        y += 2
    else:
        y += 1

    y += 1

    # Select action
    action_color = term.bold_cyan if editing_field == "select_action" else term.normal
    print(term.move_xy(0, y) + action_color + "Select Action: " + term.normal + f"{state.select_action}")
    if editing_field == "select_action":
        print(term.move_xy(0, y + 1) + f"> {current_input}_")


def run(state: AppState) -> None:
    current_input = ""
    editing_field = "cache_hours"  # Start with cache_hours
    message = ""

    render(state, current_input, editing_field, message)

    while True:
        key = term.inkey()

        if key.name == "KEY_ESCAPE":
            # Cancel - reload settings
            settings = accounts.load_settings()
            state.cache_hours = settings["cache_hours"]
            state.default_search_terms = settings["default_search_terms"]
            state.default_blacklist = settings["default_blacklist"]
            state.select_action = settings["select_action"]
            state.current_view = "account_select"
            return

        elif key.name == "KEY_TAB":
            # Move to next field
            if editing_field == "cache_hours":
                editing_field = "default_search_terms"
            elif editing_field == "default_search_terms":
                editing_field = "default_blacklist"
            elif editing_field == "default_blacklist":
                editing_field = "select_action"
            else:
                editing_field = "cache_hours"
            current_input = ""
            message = ""

        elif key.name == "KEY_ENTER":
            if editing_field == "cache_hours":
                if current_input.strip():
                    try:
                        hours = float(current_input.strip())
                        if hours > 0:
                            state.cache_hours = hours
                            current_input = ""
                            message = "Cache hours updated"
                        else:
                            message = "Error: Cache hours must be positive"
                    except ValueError:
                        message = "Error: Invalid number"
                else:
                    # Save and exit
                    accounts.save_settings(
                        state.cache_hours,
                        state.default_search_terms,
                        state.default_blacklist,
                        state.select_action
                    )
                    state.current_view = "account_select"
                    return

            elif editing_field in ("default_search_terms", "default_blacklist"):
                if current_input.strip():
                    entry = current_input.strip()
                    current_input = ""

                    if entry == "r":
                        # Clear the current field
                        if editing_field == "default_search_terms":
                            state.default_search_terms = []
                        else:
                            state.default_blacklist = []
                        message = "Cleared"
                    else:
                        is_blacklist, tokens = _parse_input(entry)

                        if editing_field == "default_search_terms":
                            # Add/remove from default_search_terms
                            for token in tokens:
                                if is_blacklist:
                                    # Remove from include
                                    if token in state.default_search_terms:
                                        state.default_search_terms.remove(token)
                                else:
                                    # Toggle in include
                                    if token in state.default_search_terms:
                                        state.default_search_terms.remove(token)
                                    else:
                                        state.default_search_terms.append(token)
                        else:  # default_blacklist
                            # Add/remove from default_blacklist
                            for token in tokens:
                                if is_blacklist:
                                    # Toggle in blacklist
                                    if token in state.default_blacklist:
                                        state.default_blacklist.remove(token)
                                    else:
                                        state.default_blacklist.append(token)
                                else:
                                    # Remove from blacklist
                                    if token in state.default_blacklist:
                                        state.default_blacklist.remove(token)
                        message = ""
                else:
                    # Save and exit
                    accounts.save_settings(
                        state.cache_hours,
                        state.default_search_terms,
                        state.default_blacklist,
                        state.select_action
                    )
                    state.current_view = "account_select"
                    return

            elif editing_field == "select_action":
                if current_input.strip():
                    action = current_input.strip().lower()
                    if action in ("iina", "copy", "both"):
                        state.select_action = action
                        current_input = ""
                        message = f"Select action set to: {action}"
                    else:
                        message = "Error: Must be 'iina', 'copy', or 'both'"
                        current_input = ""
                else:
                    # Save and exit
                    accounts.save_settings(
                        state.cache_hours,
                        state.default_search_terms,
                        state.default_blacklist,
                        state.select_action
                    )
                    state.current_view = "account_select"
                    return

        elif key == "r" and not current_input:
            # Clear stream cache
            accounts.clear_stream_cache()
            message = "Stream cache cleared"

        elif key.name in ("KEY_BACKSPACE", "KEY_DELETE"):
            current_input = current_input[:-1]
            message = ""

        elif not key.is_sequence:
            current_input += str(key)
            message = ""

        render(state, current_input, editing_field, message)
