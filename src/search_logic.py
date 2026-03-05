import unicodedata

from src.accounts import Stream
from dataclasses import dataclass, field

@dataclass(frozen=True)
class SearchTerms:
    """Container for search include and exclude terms."""
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


def normalize(name: str) -> str:
    """Normalize string for case-insensitive, accent-insensitive comparison."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', name.lower())
        if unicodedata.category(c) != 'Mn'
    )


def score_stream(terms: SearchTerms, stream: Stream) -> int | None:
    """Score a stream based on how well it matches search terms."""
    name = normalize(stream.name)

    # Exclude streams with blacklisted terms
    if any(term in name for term in terms.exclude):
        return None

    # Score stream based on term priority
    score = 0
    for i, term in enumerate(terms.include):
        if term in name:
            weight = len(terms.include) - i
            score += weight

    return score


def search(streams: list[Stream], terms: SearchTerms) -> list[Stream]:
    """Search and filter streams based on include/exclude terms."""
    # Build (stream, score) list
    matches: list[tuple[Stream, int]] = []
    for stream in streams:
        score = score_stream(terms, stream)
        if score is None or score == 0:
            continue
        matches.append((stream, score))

    # Sort highest score first, and then by name for stable ties
    matches.sort(key=lambda x: (-x[1], len(x[0].name)))

    # Return just the streams
    return [stream for stream, score in matches]
