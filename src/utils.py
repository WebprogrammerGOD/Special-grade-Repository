import pandas as pd


def normalize_text(value) -> str:
    return str(value).strip().lower()


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    text = normalize_text(text)
    return any(keyword in text for keyword in keywords)


def format_value(value) -> str:
    """Format a value for a readable chatbot response."""
    if pd.isna(value):
        return "N/A"
    return str(value)


def search_dataframe(
    df: pd.DataFrame,
    query: str,
    search_columns: list[str],
    limit: int = 8,
) -> pd.DataFrame:
    """
    Search relevant columns using the whole phrase first,
    then score rows by the number of matching words.
    """
    if df.empty:
        return df

    normalized_query = normalize_text(query)

    words = [
        word.strip(".,!?;:()[]{}\"'")
        for word in normalized_query.split()
        if len(word.strip(".,!?;:()[]{}\"'")) >= 2
    ]

    valid_columns = [col for col in search_columns if col in df.columns]
    if not valid_columns:
        return df.head(limit)

    searchable = (
        df[valid_columns]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )

    exact_mask = searchable.str.contains(
        normalized_query,
        regex=False,
        na=False,
    )
    exact_matches = df.loc[exact_mask]

    if not exact_matches.empty:
        return exact_matches.head(limit)

    if words:
        scores = searchable.apply(
            lambda text: sum(word in text for word in words)
        )
        best = df.loc[scores > 0].copy()

        if not best.empty:
            best["_match_score"] = scores.loc[best.index]
            best = best.sort_values("_match_score", ascending=False)
            return best.drop(columns="_match_score").head(limit)

    return df.head(limit)


def format_table(
    df: pd.DataFrame,
    columns: list[tuple[str, str]],
    title: str,
) -> str:
    """Create a compact Markdown response from selected DataFrame columns."""
    if df.empty:
        return f"### {title}\nNo matching information was found."

    lines = [f"### {title}", ""]

    for _, row in df.iterrows():
        parts = []

        for column, label in columns:
            if column in df.columns:
                parts.append(
                    f"**{label}:** {format_value(row[column])}"
                )

        if parts:
            lines.append(" • ".join(parts))
            lines.append("")

    return "\n".join(lines)


def detect_request(prompt: str) -> str:
    """
    Classify the request into one supported function.
    Supports common English and Vietnamese keywords.
    """
    text = normalize_text(prompt)

    # A trip-planning prompt can mention a hotel or flight as a constraint.
    # Detect it before those secondary services so it receives destination
    # recommendations rather than a dataset lookup.
    if contains_any(
        text,
        (
            "travel",
            "destination",
            "trip",
            "tour",
            "place",
            "vacation",
            "holiday",
            "getaway",
            "visit",
            "explore",
            "where to go",
            "where should i go",
            "where should we go",
            "recommend somewhere",
            "recommend a place",
            "suggest a destination",
            "plan a trip",
            "transportation",
        ),
    ):
        return "travel"

    if contains_any(
        text,
        (
            "hotel",
            "accommodation",
            "accomodation",
            "lodge",
            "stay",
            "khách sạn",
            "lưu trú",
            "chỗ ở",
        ),
    ):
        return "hotel"

    if contains_any(
        text,
        (
            "plane",
            "flight",
            "ticket",
            "airfare",
            "route",
            "máy bay",
            "vé máy bay",
            "chuyến bay",
            "vé",
        ),
    ):
        return "plane"

    if contains_any(
        text,
        (
            "travel",
            "destination",
            "trip",
            "tour",
            "place",
            "vacation",
            "holiday",
            "getaway",
            "visit",
            "explore",
            "where to go",
            "where should i go",
            "where should we go",
            "recommend somewhere",
            "recommend a place",
            "suggest a destination",
            "plan a trip",
            "transportation",
            "du lịch",
            "điểm đến",
            "địa điểm",
            "chuyến đi",
        ),
    ):
        return "travel"

    if contains_any(
        text,
        (
            "viejar mucho",
            "company",
            "introduce",
            "about you",
            "công ty",
            "giới thiệu",
            "thông tin công ty",
        ),
    ):
        return "company"

    if contains_any(
        text,
        (
            "help",
            "support",
            "service",
            "function",
            "hỗ trợ",
            "dịch vụ",
            "chức năng",
        ),
    ):
        return "help"

    return "other"
