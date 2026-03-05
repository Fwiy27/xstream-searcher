from blessed import Terminal
from src.state import AppState
from src.views.accounts import add as account_add, edit as account_edit, select as account_select
from src.views.search import config as search_config, results
from src.views import settings
from src import accounts

term = Terminal()

def main():
    state = AppState()

    # Load settings from config
    saved_settings = accounts.load_settings()
    state.cache_hours = saved_settings["cache_hours"]
    state.default_search_terms = saved_settings["default_search_terms"]
    state.default_blacklist = saved_settings["default_blacklist"]
    state.select_action = saved_settings["select_action"]
    # Initialize search terms with defaults
    state.search_terms = state.default_search_terms.copy()
    state.blacklist = state.default_blacklist.copy()

    view_map = {
        "account_select": account_select.run,
        "account_add":    account_add.run,
        "account_edit":   account_edit.run,
        "search_config":  search_config.run,
        "results":        results.run,
        "settings":       settings.run,
    }

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        while True:
            view_map[state.current_view](state)

if __name__ == "__main__":
    main()