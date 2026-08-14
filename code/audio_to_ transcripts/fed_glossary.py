"""Domain priors for transcribing interviews about U.S. monetary policy.

Whisper handles general English well but misspells this domain's proper nouns
(Clarida -> Clarita, FOMC -> F O M C, ten-year -> tenure). Two levers: an
``initial_prompt`` injected before decoding, whose main effect is style rather than
vocabulary, and ``CORRECTIONS`` applied afterwards.

New vocabulary belongs in ``CORRECTIONS`` -- it costs no tokens and cannot distort
decoding, unlike ``hotwords`` (see README). Match a surname bare only when it is
not also a real word: ``r"Beth Hammock"``, not ``r"Hammock"``.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 1. initial_prompt -- running prose, not a keyword list: the model is continuing
#    this text, so the closer it reads to the target the better it works.
# ---------------------------------------------------------------------------

# Policy body, about 75 tokens, shared corpus-wide.
_POLICY_BODY = (
    "The speakers discuss the Federal Reserve and the FOMC, Chair Jerome Powell, "
    "the federal funds rate and a 25 basis point hike, quantitative tightening and "
    "balance sheet runoff, the neutral rate and the dot plot, the yield curve "
    "inversion between the 2-year and the 10-year Treasury, core PCE inflation and "
    "nonfarm payrolls, and whether the Fed is hawkish, dovish, or data dependent."
)

# Opening sentences, 20-35 tokens each. Reporters introduce themselves on air
# ("Steve Liesman, CNBC"), so priming those names is cheap; irrelevant ones dilute.
INTERVIEW_CONTEXTS: dict[str, str] = {
    "bloomberg": (
        "The following is a Bloomberg Television interview on U.S. monetary policy "
        "with Tom Keene, Jonathan Ferro, Lisa Abramowicz, and Michael McKee."
    ),
    "cnbc": (
        "The following is a CNBC interview on U.S. monetary policy with senior "
        "economics reporter Steve Liesman, along with Sara Eisen, Becky Quick, "
        "Andrew Ross Sorkin, and Rick Santelli."
    ),
    "fox_business": (
        "The following is a Fox Business Network interview on U.S. monetary policy "
        "with Edward Lawrence, Maria Bartiromo, Neil Cavuto, Charles Payne, and "
        "Liz Claman."
    ),
    "cnn": (
        "The following is a CNN interview on U.S. monetary policy with Matt Egan, "
        "Julia Chatterley, Richard Quest, and Christine Romans."
    ),
    "yahoo": (
        "The following is a Yahoo Finance interview on U.S. monetary policy with "
        "Fed reporter Jennifer Schonberger, along with Brian Cheung, Julie Hyman, "
        "and Brad Smith."
    ),
    # Press conferences. The outlets have to be primed too: without them
    # "Timiraos" is essentially never transcribed correctly.
    "presser": (
        "The following is a Federal Reserve press conference. Reporters identify "
        "themselves before asking questions: Nick Timiraos of The Wall Street "
        "Journal, Steve Liesman of CNBC, Howard Schneider of Reuters, Edward "
        "Lawrence of Fox Business, Jennifer Schonberger of Yahoo Finance, and "
        "Colby Smith of The New York Times."
    ),
    # Default: naming the wrong network's anchors invites the model to hallucinate
    # them, and the names it does misrecognise are caught by CORRECTIONS anyway.
    "generic": (
        "The following is a financial television interview on U.S. monetary policy "
        "with a Federal Reserve official."
    ),
}

DEFAULT_NETWORK = "generic"


def build_initial_prompt(network: str | None = None, extra: str | None = None) -> str:
    """Assemble the prompt for one ``INTERVIEW_CONTEXTS`` key.

    ``extra`` appends a sentence, e.g. "The official being interviewed is Vice Chair
    Richard Clarida." -- the safest way to prime a name when it is known.
    """
    key = (network or DEFAULT_NETWORK).lower().replace("-", "_")
    if key not in INTERVIEW_CONTEXTS:
        raise ValueError(f"unknown network {network!r}; "
                         f"choose from {sorted(INTERVIEW_CONTEXTS)}")
    parts = [INTERVIEW_CONTEXTS[key], _POLICY_BODY]
    if extra:
        parts.append(extra.strip())
    return " ".join(parts)


# ---------------------------------------------------------------------------
# 2. CORRECTIONS
# ---------------------------------------------------------------------------


def _split_acronym(acronym: str) -> str:
    """Match "F O M C" or "F.O.M.C" but not "FOMC".

    The separator is required: made optional, the pattern replaces the acronym with
    itself, which fills the hit counts with noise and defeats auditing.
    """
    letters = list(acronym)
    dotted = r"\.\s?".join(letters)   # F.O.M.C -- the final dot is left in place
    spaced = r"\s+".join(letters)     # F O M C
    return f"(?:{dotted}|{spaced})"


# Acronyms Whisper tends to spell out, and this material is dense with them.
_ACRONYMS = (
    "FOMC", "PCE", "CPI", "PPI", "GDP", "ECB", "QE", "QT",
    "SEP", "IORB", "BLS", "BEA", "CBO", "ISM", "PMI", "ADP", "ECI",
    "MBS", "TIPS", "SOFR", "BTFP", "RRP",
)

# Case-insensitive, on word boundaries. \1 works in replacements: the wrapper adds a
# non-capturing group, so numbering is unaffected.
CORRECTIONS: dict[str, str] = {
    **{_split_acronym(a): a for a in _ACRONYMS},

    # ---- Governors and Reserve Bank presidents ----
    # Unanchored: these spellings are not English words.
    r"Clarita|Klarida|Claritas|Clarido": "Clarida",
    r"Cash Cari|Cash Carey|Kashkarai|Cashkari|Kash Kari": "Kashkari",
    r"Gools Bee|Gulsbee|Goolsbe|Goles Bee": "Goolsbee",
    r"Musallem|Musalim|Moosalem|Musa Lem": "Musalem",
    r"Kuggler|Koogler|Cougler": "Kugler",
    r"Bernanky|Bernankey|Bernanki": "Bernanke",
    r"Yellan": "Yellen",
    r"Rosengrin|Rosengreen": "Rosengren",
    r"Bouillard": "Bullard",
    # Anchored: the surname alone is a real word or another real surname.
    r"Beth Hammock": "Beth Hammack",
    r"Raphael Bostick|Rafael Bostic": "Raphael Bostic",
    r"Mary Daley|Mary Daily": "Mary Daly",
    r"Laurie Logan|Lori Logan": "Lorie Logan",
    r"(?:Tom|Thomas) Barkan": "Tom Barkin",
    r"(?:Jeffrey|Jeff) Schmidt": "Jeffrey Schmid",
    r"Lael Brainerd": "Lael Brainard",
    r"Randal+ Quarrels": "Randal Quarles",
    r"Loretta Meister": "Loretta Mester",
    r"Stephen (?:Meeran|Mirren)": "Stephen Miran",
    r"Phillip Jefferson": "Philip Jefferson",
    r"(?:Jerome|Jay) Powel(?!l)": "Jerome Powell",
    r"Austan Goolsby": "Austan Goolsbee",

    # ---- Reporters and anchors ----
    r"Leesman|Leesmann|Lisman": "Liesman",
    r"Timaros|Tamiraos|Timiros|Timerios|Tim Iraos": "Timiraos",
    r"Shonberger|Schoenberger|Shomberger": "Schonberger",
    r"Quintania|Quintinilla": "Quintanilla",
    r"Lacua|Laqua|Lakwa": "Lacqua",
    r"Bartaromo|Bartiroma": "Bartiromo",
    r"Cavudo|Kavuto": "Cavuto",
    r"Santelly|Santeli": "Santelli",
    r"Chatterly": "Chatterley",
    r"Rugabber|Roogaber": "Rugaber",
    r"Smialeck|Smilek": "Smialek",
    r"Lisa Abramowitz": "Lisa Abramowicz",
    r"Liz Clayman": "Liz Claman",
    r"Joe Kern(?:an|on)": "Joe Kernen",
    r"Sarah Eisen": "Sara Eisen",

    # ---- Terminology ----
    # "tenure" for "ten-year" is the classic error in financial audio; since tenure
    # is a real word, the noun after it is required.
    r"tenure (yield|Treasury|note|bond|paper)": r"10-year \1",
    r"basis point s": "basis points",
    r"dot-plot": "dot plot",
    r"quantitative tight?ning": "quantitative tightening",
    r"Jackson Hall": "Jackson Hole",
    r"Humphrey Hawkins": "Humphrey-Hawkins",
    r"non-farm payrolls": "nonfarm payrolls",
    r"R star": "r-star",
    r"dis-inflation": "disinflation",
    r"stag-flation": "stagflation",
    r"soft-landing": "soft landing",
    r"GDP Now": "GDPNow",
    r"S and P 500": "S&P 500",
}

# Casing-only rules, kept separate because they must be case-sensitive: in the table
# above "Beige Book" would match its own rule and be replaced by itself.
CASE_CORRECTIONS: dict[str, str] = {
    r"Beige book": "Beige Book",
    r"beige book": "Beige Book",
    r"Fed funds": "fed funds",
    r"federal reserve": "Federal Reserve",
    r"treasury yield": "Treasury yield",
}

# Compiled once. Word boundaries keep "CPI" from matching inside "CPIX".
_COMPILED = [
    (re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE), replacement)
    for pattern, replacement in CORRECTIONS.items()
] + [
    (re.compile(rf"\b(?:{pattern})\b"), replacement)
    for pattern, replacement in CASE_CORRECTIONS.items()
]


def apply_corrections(text: str) -> tuple[str, dict[str, int]]:
    """Apply the substitutions; return the text and a hit count per rule.

    No rule matches its own output, so every count is a real edit and an
    implausible one flags a rule that over-matches.
    """
    hits: dict[str, int] = {}
    for pattern, replacement in _COMPILED:
        text, count = pattern.subn(replacement, text)
        if count:
            hits[replacement] = hits.get(replacement, 0) + count
    return text, hits
