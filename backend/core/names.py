"""Name-derived sorting keys.

The public participant list is displayed by full name but ordered by surname.
The database stores only the free-text ``name``, so the ordering column is
derived here with ``nameparser``:

* the surname is ``family_base`` (particles such as "van der" are ignored, the
  way directory listings file them);
* the given name(s) are the tie-breaker;
* the result is ASCII-folded and case-folded so SQLite's binary collation
  still orders Czech names correctly (``Š`` next to ``S``, not after ``Z``).

``nameparser`` parses a name into ``title``/``given``/``middle``/``family``/
``suffix``; see https://nameparser.readthedocs.io/.
"""

import unicodedata

from nameparser import Lexicon, Parser

# Czech post-nominals and generational suffixes. nameparser already knows
# "csc"; these additions cover the rest of the common Czech forms.
_CZECH_LEXICON = Lexicon.default().add(suffix_acronyms={"csc", "drsc", "ml", "st"})
_PARSER = Parser(lexicon=_CZECH_LEXICON)


def _fold(value: str) -> str:
    """Lowercase and remove diacritics for a stable, DB-independent order."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_marks.split())


def compute_sort_key(name: str) -> str:
    """Return the surname-first key used by ``sort_key`` columns.

    Examples (after folding):
    ``"Jana Novotná" -> "novotna jana"``,
    ``"Robert van der Sar" -> "sar robert"``,
    ``"Novák, Jan" -> "novak jan"``.
    """
    if not name or not name.strip():
        return ""

    parsed = _PARSER.parse(name)
    surname = _fold(parsed.family_base or parsed.family)
    given = _fold(parsed.given_names or parsed.given)

    if not surname:
        # Mononyms ("Cher") or unparseable input: sort by whatever was given.
        return given or _fold(name)
    return f"{surname} {given}".strip()
