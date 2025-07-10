from finvizfinance.screener.overview import Overview

# Custom Stock Universe of Interest
UNIVERSE_CRITERIA = {
  "Exchange": "Any",
  "Price": "Over $10",
  "Average Volume": "Over 1M",
  "Country": "USA",
  "Market Cap.": "+Small (over $300mln)"
}

def screener(filters: dict):
    """
    Returns a dataframe of the screener with the given filters, sorted by market cap.
    """
    view = Overview()
    view.set_filter(filters_dict=filters)
    df = view.screener_view(verbose=0)
    return df.sort_values(by='Market Cap', ascending=False)

def fetch_custom_universe():
    """
    Returns a dataframe of the custom universe of interest.
    """
    return screener(UNIVERSE_CRITERIA)
