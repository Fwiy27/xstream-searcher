from dataclasses import dataclass, field
from src.accounts import Account

@dataclass
class AppState:
    accounts: list[Account] = field(default_factory=list)
    active_account: Account | None = None
    search_terms: list[str] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=list)
    results: list = field(default_factory=list)
    current_view: str = "account_select"
    # Settings
    cache_hours: float = 12.0
    default_search_terms: list[str] = field(default_factory=list)
    default_blacklist: list[str] = field(default_factory=list)
    select_action: str = "copy"