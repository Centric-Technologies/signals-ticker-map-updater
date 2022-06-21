import io
import logging
import pandas as pd
import functions_framework
from google.cloud import storage

from signals_common_core import log
from signals_common_core.data import tickers
from signals_common_core.secrets import get_secret_value
from signals_common_core.connectors.slack import SlackClient

from mappers import eod_mapper


NUMERAI_UNIVERSE_URL = (
    "https://numerai-signals-public-data.s3-us-west-2.amazonaws.com/universe/latest.csv"
)
SLACK_TOKEN_SECRET_NAME = "slack-token-alert-bot"

logger = log.get_logger(__name__)


@functions_framework.http
def main(request):
    slack = SlackClient(get_secret_value(SLACK_TOKEN_SECRET_NAME))

    logger.info("Downloading ticker map")
    ticker_map = tickers.read_ticker_map()

    # finding duplicates
    duplicated = ticker_map[ticker_map.duplicated(subset="ticker", keep=False)]
    if not duplicated.empty:
        utils.notify_duplicated_mapping(list(duplicated.index))

    logger.info("Downloading Numerai's universe")
    known_universe_tickers = set(ticker_map.index.to_list())
    numerai_latest_universe = pd.read_csv(NUMERAI_UNIVERSE_URL).set_index(
        "bloomberg_ticker"
    )

    with open("numerai_blacklist.txt", encoding="utf-8") as f:
        numerai_blacklisted = set(f.read().splitlines())
        logger.info("Filtered %s blacklisted stocks", len(numerai_blacklisted))

    numerai_latest_universe = pd.read_csv(NUMERAI_UNIVERSE_URL).set_index(
        "bloomberg_ticker"
    )

    latest_universe_tickers = (
        set(numerai_latest_universe.index.to_list()) - numerai_blacklisted
    )

    new_tickers = latest_universe_tickers - known_universe_tickers
    if new_tickers:
        logger.info(
            "Found %s new tickers latest Numerai universe. Adding them to our mapping. %s",
            len(new_tickers),
            new_tickers,
        )

        full_ticker_mapping = eod_mapper.build_map()
        ticker_map = ticker_map.merge(
            numerai_latest_universe, how="outer", on="bloomberg_ticker"
        )
        ticker_map.update(full_ticker_mapping, overwrite=False)
        tickers.push_ticker_map(ticker_map)

    universe = io.StringIO()
    for t in list(numerai_latest_universe.index):
        universe.write(f"{t}\n")

    storage_client = storage.Client()
    blob = storage_client.bucket("signals-stocks-lists").blob("numerai-universe.txt")
    universe.seek(0)
    blob.upload_from_file(universe)
    logging.info("Done")
    return "ok"


if __name__ == "__main__":
    main(None)
