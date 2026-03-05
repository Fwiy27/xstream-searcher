import json
import keyring
import time
import tomllib
import tomli_w
import requests

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import cache

APP_NAME = "io.github.yourname.xstream-searcher"
CONFIG_PATH = Path.home() / ".config" / "xstream-searcher" / "config.toml"
CACHE_PATH = Path.home() / ".config" / "xstream-searcher" / "streams_cache.json"
DEFAULT_CACHE_HOURS = 12


@dataclass(frozen=True)
class Account:
    name: str
    url: str
    username: str

    @property
    def password(self) -> str:
        password = keyring.get_password(APP_NAME, self.name)
        if password is None:
            raise RuntimeError(f"No password found for {self.name}")
        return password

    @cache
    def get_expiration(self) -> str:
        """Returns formatted expiration date and time (e.g., "Mon, January 15, 2026 3:45 PM (CST)")."""
        def format_date(d: datetime) -> str:
            day = d.day  # int, no padding
            hour = d.strftime("%I").lstrip("0") or "12"
            year = d.year

            return (
                f"{d.strftime('%a, %B ')}"
                f"{day}, {year} "
                f"{hour}:{d.strftime('%M %p (%Z)')}"
            )

        exp = get_expiration(self)

        t_utc = datetime.fromtimestamp(exp, ZoneInfo("UTC"))
        return format_date(t_utc)

    @cache
    def get_streams(self) -> list['Stream']:
        """Get all available streams for this profile.

        Returns streams from disk cache if within the configured TTL, otherwise
        fetches from the API and updates the cache.

        Returns:
            list[Stream]: List of all streams available to this profile.

        Raises:
            RuntimeError: If unable to fetch streams from API.
        """
        return get_streams(self)


@dataclass(frozen=True)
class Stream:
    """Represents a single streaming channel."""
    name: str
    stream_id: str
    category_id: str

    def url(self, account: Account) -> str:
        """Generate streaming URL for this stream using profile credentials."""
        return (
            f"{account.url}/live/"
            f"{account.username}/"
            f"{account.password}/"
            f"{self.stream_id}.m3u8"
        )


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def _save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(config, f)


def _get_cache_ttl() -> float:
    """Return the configured cache TTL in seconds, falling back to DEFAULT_CACHE_HOURS."""
    config = _load_config()
    hours = config.get("settings", {}).get("cache_hours", DEFAULT_CACHE_HOURS)
    return float(hours) * 3600


def _load_stream_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_stream_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


def clear_stream_cache() -> None:
    """Clear all cached streams."""
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()


def load_settings() -> dict:
    """Load settings from config file.

    Returns:
        dict with keys: cache_hours, default_search_terms, default_blacklist, select_action
    """
    config = _load_config()
    settings = config.get("settings", {})
    return {
        "cache_hours": settings.get("cache_hours", DEFAULT_CACHE_HOURS),
        "default_search_terms": settings.get("default_search_terms", []),
        "default_blacklist": settings.get("default_blacklist", []),
        "select_action": settings.get("select_action", "iina")
    }


def save_settings(cache_hours: float, default_search_terms: list[str], default_blacklist: list[str], select_action: str) -> None:
    """Save settings to config file."""
    config = _load_config()
    if "settings" not in config:
        config["settings"] = {}

    config["settings"]["cache_hours"] = cache_hours
    config["settings"]["default_search_terms"] = default_search_terms
    config["settings"]["default_blacklist"] = default_blacklist
    config["settings"]["select_action"] = select_action

    _save_config(config)


def load_accounts() -> list[Account]:
    config = _load_config()
    accounts = config.get("accounts", {})
    return [
        Account(name=n, url=info["url"], username=info["username"])
        for n, info in accounts.items()
    ]


def name_exists(name: str) -> bool:
    config = _load_config()
    return name in config.get("accounts", {})


def save_account(name: str, url: str, username: str, password: str) -> Account:
    config = _load_config()
    if "accounts" not in config:
        config["accounts"] = {}
    config["accounts"][name] = {"url": url, "username": username}
    _save_config(config)

    keyring.set_password(APP_NAME, name, password)
    return Account(name=name, url=url, username=username)


def delete_account(name: str):
    keyring.delete_password(APP_NAME, name)
    config = _load_config()
    if "accounts" in config and name in config["accounts"]:
        del config["accounts"][name]
        _save_config(config)

    # Also evict from stream cache
    cache = _load_stream_cache()
    if name in cache:
        del cache[name]
        _save_stream_cache(cache)


def get_expiration(account: Account) -> int:
    """Get expiration timestamp for an account from the API."""
    url = f"{account.url}/player_api.php"
    params = {
        "username": account.username,
        "password": account.password
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    # Get response
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        raise RuntimeError(f"Request timed out connecting to {account.url}")
    except requests.ConnectionError:
        raise RuntimeError(f"Failed to connect to {account.url}")
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code} from {account.url}")
    except requests.RequestException as e:
        raise RuntimeError(f"Request failed: {e}")

    # Parse response
    try:
        data: dict[str, dict[str, str]] = response.json()
    except ValueError as e:
        raise RuntimeError(f"Invalid JSON response from {account.url}: {e}")

    user_info: dict[str, str] = data.get("user_info", {})

    if "exp_date" not in user_info:
        raise RuntimeError("Can not find exp_date in profile response")

    expiration_timestamp: str | None = user_info.get("exp_date")
    if not expiration_timestamp:
        raise RuntimeError("No timestamp provided for exp_date")

    return int(expiration_timestamp)


def get_streams(account: Account) -> list[Stream]:
    """Get all available streams for a profile, using disk cache if still fresh."""
    ttl = _get_cache_ttl()
    cache = _load_stream_cache()
    entry = cache.get(account.name)

    if entry and (time.time() - entry["fetched_at"]) < ttl:
        return [
            Stream(s["name"], s["stream_id"], s["category_id"])
            for s in entry["streams"]
        ]

    streams = _fetch_streams(account)

    cache[account.name] = {
        "fetched_at": time.time(),
        "streams": [
            {"name": s.name, "stream_id": s.stream_id, "category_id": s.category_id}
            for s in streams
        ],
    }
    _save_stream_cache(cache)

    return streams


def _fetch_streams(account: Account) -> list[Stream]:
    """Fetch all available streams for a profile directly from the API."""
    url = f"{account.url}/player_api.php"
    params = {
        "username": account.username,
        "password": account.password,
        "action": "get_live_streams"
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.Timeout:
        raise RuntimeError(f"Request timed out getting streams from {account.url}")
    except requests.ConnectionError:
        raise RuntimeError(f"Failed to connect to {account.url}")
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code} getting streams")
    except requests.RequestException as e:
        raise RuntimeError(f"Request failed: {e}")

    try:
        streams_json: list[dict[str, str | int]] = response.json()
    except ValueError as e:
        raise RuntimeError(f"Invalid JSON response: {e}")

    return [
        Stream(
            str(s.get("name", "")),
            str(s.get("stream_id", "")),
            str(s.get("category_id", "")),
        )
        for s in streams_json
    ]