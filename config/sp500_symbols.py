"""
S&P 500 Stock Symbols Configuration

This file contains all 503 symbols that are part of the S&P 500 index.
Data source: https://stockanalysis.com/list/sp-500-stocks/
Last updated: January 2025
"""

# All 503 S&P 500 stock symbols (extracted from stockanalysis.com)
SP500_SYMBOLS = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "GOOG", "META", "AVGO", "TSLA",
    "JPM", "WMT", "LLY", "V", "ORCL", "NFLX", "MA", "XOM", "COST", "PG",
    "HD", "JNJ", "BAC", "ABBV", "PLTR", "KO", "PM", "UNH", "CSCO", "GE",
    "TMUS", "CRM", "AMD", "INTC", "CVX", "WFC", "ADBE", "MRK", "TMO", "NOW",
    "CAT", "INTU", "IBM", "RTX", "TXN", "SPGI", "LOW", "QCOM", "UBER", "NEE",
    "ISRG", "PFE", "HON", "GS", "SYK", "MS", "MDT", "VRTX", "AXP", "T",
    "CMCSA", "BSX", "AMAT", "DE", "LMT", "C", "BKNG", "ADI", "MU", "PANW",
    "SO", "DUK", "TJX", "BLK", "MDLZ", "SCHW", "PLD", "EOG", "BA", "LRCX",
    "CB", "REGN", "AMT", "SHW", "FI", "ETN", "CI", "MO", "ZTS", "PYPL",
    "MMC", "ICE", "SNPS", "FCX", "PGR", "KLAC", "CDNS", "CCI", "MCO", "USB",
    "APO", "GILD", "TGT", "AON", "CME", "HCA", "MSI", "CL", "GD", "EQIX",
    "ABNB", "PNC", "ORLY", "APH", "MPC", "EMR", "ITW", "FDX", "PSA",
    "TFC", "GM", "WM", "VLO", "SLB", "MCK", "WELL", "NOC", "AJG", "ECL",
    "COP", "AMP", "CMI", "ADSK", "MAR", "HLT", "COF", "RSG", "ROP", "FICO",
    "CARR", "NXPI", "AME", "PAYX", "O", "KMI", "AZO", "ALL", "DHI", "NSC",
    "URI", "FAST", "BDX", "SRE", "CPRT", "KMB", "VRSK", "AIG", "PSX", "BK",
    "GWW", "CTSH", "LULU", "PRU", "CNC", "PH", "MLM", "EXC", "YUM", "OTIS",
    "LHX", "DHR", "MMM", "OKE", "HES", "EA", "CTAS", "PWR", "ACGL",
    "HPQ", "CMG", "A", "PCAR", "MSC", "GRMN", "IDXX", "HSY", "KR", "NUE",
    "CHTR", "SBUX", "HUM", "XEL", "EXR", "PCG", "GLW", "TROW", "ED", "WTW",
    "MNST", "IT", "D", "ODFL", "RMD", "SPG", "GEHC", "IQV", "KDP", "FANG",
    "DXCM", "WEC", "BKR", "AVB", "MTB", "VICI", "VMC", "WAB", "ROK", "TSCO",
    "EIX", "NEM", "BIIB", "CSGP", "TPG", "HAL", "FSLR", "WY", "ETR", "ZBH",
    "ILMN", "AWK", "PPG", "MPWR", "KEYS", "ANSS", "CTVA", "DOV", "ESS", "HPE",
    "TDG", "DTE", "MTD", "FTV", "EQR", "STZ", "WMB", "CEG", "SMCI", "TSN",
    "COO", "HOLX", "IRM", "FE", "ATO", "STLD", "TT", "GPN", "EQT", "TER",
    "WST", "BRO", "CNP", "DG", "VLTO", "CLX", "LYB", "EL", "LH", "TRGP",
    "BALL", "RF", "SYF", "PEG", "IP", "CAH", "HBAN", "AVY", "FITB", "MOH",
    "WAT", "WRB", "K", "STX", "CF", "EFX", "TYL", "CBRE", "ON", "J",
    "HUBB", "NTAP", "LDOS", "DLTR", "PPL", "LUV", "SWKS", "ALGN", "JBHT", "NTRS",
    "AKAM", "EBAY", "TTWO", "JCI", "PFG", "KIM", "KEY", "RVTY", "ENPH", "EG",
    "MCHP", "NRG", "JKHY", "UDR", "REG", "POOL", "LNT", "SBAC", "EXPD", "MAS",
    "PAYC", "CHD", "BBY", "EXPE", "NDAQ", "VRSN", "TXT", "AMCR", "HST", "GPC",
    "SNA", "APTV", "TRMB", "FRT", "INVH", "LVS", "ARE", "CINF", "TECH", "CMS",
    "WDC", "CBOE", "MAA", "FFIV", "BXP", "ZBRA", "TRV", "CHRW", "NI",
    "SWK", "DRI", "CTRA", "ALLE", "BR", "PKG", "LYV", "AEE", "MKC", "DOW",
    "SOLV", "WBA", "EPAM", "CPT", "UHS", "CDW", "CAG", "DXC", "INCY",
    "KMX", "JNPR", "AIZ", "WYNN", "TAP", "LKQ", "HII", "AOS", "MGM", "CPB",
    "NCLH", "IPG", "HSIC", "DAY", "EMN", "PARA", "GNRC", "MKTX", "ALB", "AES",
    "MTCH", "LW", "CRL", "IVZ", "APA", "MHK", "CZR", "GL", "SJM", "HAS", "SPY",
    "QQQ", "IWM"
]

def get_sp500_symbols() -> list[str]:
    """
    Returns the complete list of S&P 500 stock symbols.
    
    Returns:
        list[str]: List of all S&P 500 stock symbols
    """
    return SP500_SYMBOLS.copy()
