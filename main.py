import logging
import pandas as pd

from signals_common_core import log
from signals_common_core.data import tickers
from signals_common_core.secrets import get_secret_value
from signals_common_core.connectors import slack, eodhd

from mappers import eod_mapper


NUMERAI_UNIVERSE_URL = (
    "https://numerai-signals-public-data.s3-us-west-2.amazonaws.com/universe/latest.csv"
)
SLACK_TOKEN_SECRET_NAME = "slack-token-alert-bot"

logger = log.get_logger(__name__)


def main():
    slack_client = slack.SlackClient(get_secret_value(SLACK_TOKEN_SECRET_NAME))

    logger.info("Downloading ticker map")
    ticker_map = tickers.read_ticker_map()

    logging.info("Checking for uplicate tickers")
    duplicated = ticker_map[ticker_map.duplicated(subset="ticker", keep=False)]
    if not duplicated.empty:
        slack_client.send_message(
            channel="signals-alerts",
            text=f"Duplicates found in ticker map, please review {', '.join(list(duplicated.index))}",
        )

    logger.info("Checkin for new tickers from Numerai")
    known_universe_tickers = set(ticker_map.index.to_list())
    # fetching the latest numerai universe
    numerai_latest_universe = pd.read_csv(NUMERAI_UNIVERSE_URL).set_index(
        "bloomberg_ticker"
    )
    with open("numerai_blacklist.txt", encoding="utf-8") as f:
        numerai_blacklisted = set(f.read().splitlines())
        logger.info("Filtered %s blacklisted stocks", len(numerai_blacklisted))
    latest_universe_tickers = (
        set(numerai_latest_universe.index.to_list()) - numerai_blacklisted
    )

    #### ADDING THE NEW TICKERS TO OUR UNIVERSE ####
    new_tickers = list(latest_universe_tickers - known_universe_tickers)
    if new_tickers:
        logger.info(
            f"Found {len(new_tickers)} new tickers latest Numerai universe. Adding them to our mapping. ({', '.join(new_tickers)})"
        )
        complete_mapping = eod_mapper.complete_numerai_mapping()
        # building a new ticker mapping, this will include all current and historical
        # tickers from numerai universes
        ticker_map = ticker_map.merge(
            numerai_latest_universe, how="outer", on="bloomberg_ticker"
        )
        ticker_map.update(complete_mapping, overwrite=False)
        ticker_map["eodhd_ticker"] = ticker_map["ticker"]  # TODO stop using "ticker"

    ## FILLING COUNTRY
    logging.info("Filling missing countries")
    ticker_map.update(
        (
            ticker_map[ticker_map["country"].isna()]
            .index.to_series()
            .apply(tickers.get_country)
            .rename("country")
        )
    )

    ## FILLING POLYGON TICKER
    logging.info("Filling missing polygon tickers")
    ticker_map.update(
        (
            ticker_map[ticker_map["polygon_ticker"].isna()]
            .index.to_series()
            .apply(tickers.get_polygon_ticker)
            .rename("polygon_ticker")
        )
    )

    # before adding new info from EODHD, we set the index
    ticker_map = ticker_map.reset_index().set_index("eodhd_ticker")

    ## FETCHING SEARCH FOR TICKERS WHICH ARE MISSING ISIN
    logger.info("Checking for missing ISIN numbers")
    missing_isin = list(ticker_map[ticker_map["isin"].isna()].index)
    if missing_isin:
        isins = eodhd.search(*missing_isin)["isin"].dropna()
        if not isins.empty:
            ticker_map.update(isins, overwrite=False)

    ### FETCHING FUNDAMENTALES FOR TICKERS WHICH ARE MISSING IT
    logger.info("Checking for missing fundamental data")
    missing_fund = list(
        ticker_map[
            (ticker_map["industry"].isna())
            | (ticker_map["isin"].isna())
            | (ticker_map["sector"].isna())
        ].index
    )
    if missing_fund:
        fundamentals = eodhd.get_fundamentals(
            *list(missing_fund),
            fields=["General::Industry", "General::Sector", "General::ISIN"],
        )
        ticker_map.update(fundamentals, overwrite=False)

    # done adding info from EODHD, reset the index to bloomberg_ticker
    ticker_map = ticker_map.reset_index().set_index("bloomberg_ticker")

    logger.info("Pushing the map")
    tickers.push_ticker_map(ticker_map)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Failed updating ticker map")
        slack_client = slack.SlackClient(get_secret_value(SLACK_TOKEN_SECRET_NAME))
        slack_client.send_message("signals-alerts", f"Failed updating ticker map. {e}")
