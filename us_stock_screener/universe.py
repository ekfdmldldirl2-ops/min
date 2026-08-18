"""Candidate universe of large-cap US stocks.

There is no free, reliable "top 50 by market cap" API, so instead we keep a
generous candidate list (well over 50 well-known mega/large-cap US names
spanning every sector) and let the screener rank them by *live* market cap
each run, keeping only the top N. This means the list below does not need to
be perfectly accurate or current -- as long as it contains the real top 50,
the ranking step will surface them correctly. Edit this list any time you
notice a name that should be added (recent IPOs, spin-offs, etc.).
"""

CANDIDATE_TICKERS = [
    # Mega-cap tech / communication services
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO",
    "ORCL", "NFLX", "ADBE", "CRM", "AMD", "CSCO", "QCOM", "INTU", "IBM",
    "TXN", "NOW", "UBER", "AMAT", "PANW", "MU", "ADI", "LRCX", "KLAC",
    "SNPS", "CDNS", "PLTR", "APP",

    # Financials
    "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "SCHW",
    "BLK", "C", "SPGI", "PGR", "CB",

    # Healthcare
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN",
    "ISRG", "VRTX", "GILD", "BSX", "REGN", "SYK", "MDT", "CI", "ELV",

    # Consumer discretionary / staples
    "WMT", "HD", "COST", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "LOW",
    "TJX", "BKNG", "TGT", "CL", "MDLZ", "MNST",

    # Industrials / energy / materials
    "XOM", "CVX", "GE", "CAT", "RTX", "HON", "UNP", "BA", "DE", "LMT",
    "UPS", "COP", "NEE", "LIN", "ETN", "ADP",

    # Communication services
    "DIS", "CMCSA", "T", "VZ", "TMUS",

    # Semis / other tech hardware
    "ASML", "TSM",
]

# de-duplicate while preserving order
CANDIDATE_TICKERS = list(dict.fromkeys(CANDIDATE_TICKERS))
