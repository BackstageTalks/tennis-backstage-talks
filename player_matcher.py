import re
import unicodedata


SUFFIX_TOKENS = {
    "jr",
    "sr",
    "junior",
    "senior",
    "ii",
    "iii",
    "iv",
}


def normalize_name(name):
    if not name:
        return ""

    text = str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    text = text.lower().strip()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace(",", " ")

    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)

    tokens = [
        token for token in text.split()
        if token not in SUFFIX_TOKENS
    ]

    return " ".join(tokens).strip()


def name_tokens(name):
    text = normalize_name(name)

    if not text:
        return []

    return text.split()


def last_name(name):
    tokens = name_tokens(name)
    if not tokens:
        return ""
    return tokens[-1]


def first_name(name):
    tokens = name_tokens(name)
    if not tokens:
        return ""
    return tokens[0]


def token_overlap_score(a, b):
    a_tokens = set(name_tokens(a))
    b_tokens = set(name_tokens(b))

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens.intersection(b_tokens))
    denominator = max(len(a_tokens), len(b_tokens))

    return overlap / denominator


def initial_match_score(a, b):
    a_first = first_name(a)
    b_first = first_name(b)

    if not a_first or not b_first:
        return 0.0

    if a_first == b_first:
        return 1.0

    if a_first[0] == b_first[0]:
        return 0.65

    return 0.0


def compact_name_score(a, b):
    a_tokens = name_tokens(a)
    b_tokens = name_tokens(b)

    if not a_tokens or not b_tokens:
        return 0.0

    if last_name(a) != last_name(b):
        return 0.0

    a_initials = "".join(token[0] for token in a_tokens[:-1] if token)
    b_initials = "".join(token[0] for token in b_tokens[:-1] if token)

    if not a_initials or not b_initials:
        return 0.0

    shorter = min(a_initials, b_initials, key=len)
    longer = max(a_initials, b_initials, key=len)

    if longer.startswith(shorter):
        return 0.75

    return 0.0


def player_name_match_score(query_name, candidate_name):
    q = normalize_name(query_name)
    c = normalize_name(candidate_name)

    if not q or not c:
        return 0.0, "empty"

    if q == c:
        return 1.0, "exact"

    q_last = last_name(q)
    c_last = last_name(c)

    token_score = token_overlap_score(q, c)
    initial_score = initial_match_score(q, c)
    compact_score = compact_name_score(q, c)

    score = token_score * 0.55

    if q_last and c_last and q_last == c_last:
        score += 0.30

    score += initial_score * 0.10
    score += compact_score * 0.05

    if q_last and c_last and q_last != c_last:
        score *= 0.45

    score = max(0.0, min(1.0, score))
