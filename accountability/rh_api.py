"""
Module for interacting with Robinhood API, providing portfolio and transaction data.
Handles historical data retrieval and percentage calculations with caching support.
"""

import datetime
import logging
import os

import robin_stocks.robinhood as rh

from accountability.caching import cache_result
from accountability.rh_types import (
    EquityHistorical,
    HistoricalPortfolio,
    PercentageDate,
    convert_dict_to_typed_dict,
    FidelityType,
    SpanType,
    BoundsType,
    BankTransfer,
)

# Get the current directory and create absolute path for debug.log
current_dir = os.path.dirname(os.path.abspath(__file__))
debug_log_path = os.path.join(current_dir, "debug.log")

# Set up logging with more detailed configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.FileHandler(debug_log_path, mode="a"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Test logging immediately
logger.info("Logging system initialized")
logger.info("Writing logs to: %s", debug_log_path)


def _get_historical_portfolio_percentage(
    historicals: list[EquityHistorical],
) -> list[PercentageDate]:
    """
    Get the percentage change of the portfolio from the historical data.
    """
    if len(historicals) == 0:
        return []

    prev_close = historicals[0]["close_equity"]
    percentages = []
    for h in historicals:
        percentages.append((h["close_equity"] - prev_close) / prev_close)
        prev_close = h["close_equity"]
    return [
        PercentageDate(date=h["begins_at"], percentage=p)
        for h, p in zip(historicals, percentages)
    ]


@cache_result(table_name="portfolio_data", ttl_seconds=3600)
def get_historical_portfolio(
    fidelity: FidelityType = "day",
    span: SpanType = "week",
    bounds: BoundsType = "regular",
) -> list[EquityHistorical]:
    logger.info(f"[get_historical_portfolio] {fidelity=}, {span=}, {bounds=}")
    historical = rh.get_historical_portfolio(fidelity, span, bounds)
    result: HistoricalPortfolio | None = convert_dict_to_typed_dict(
        historical, HistoricalPortfolio
    )
    if not result:
        return []
    return result["equity_historicals"]


def get_historical_portfolio_percentage(
    fidelity: FidelityType = "day",
    span: SpanType = "week",
    bounds: BoundsType = "regular",
) -> list[PercentageDate]:
    logger.info(
        f"[get_historical_portfolio_percentage] {fidelity=}, {span=}, {bounds=}"
    )
    historical = rh.get_historical_portfolio(fidelity, span, bounds)
    result: HistoricalPortfolio | None = convert_dict_to_typed_dict(
        historical, HistoricalPortfolio
    )
    if not result:
        return []
    percentages = _get_historical_portfolio_percentage(result["equity_historicals"])
    return percentages


@cache_result(table_name="bank_transfers", ttl_seconds=3600)
def get_bank_transfers() -> list[BankTransfer]:
    """
    Get a list of bank transfers from Robinhood.
    Returns a list of BankTransfer objects, sorted by date.
    """
    logger.info("[get_bank_transfers] Fetching bank transfers")
    transfers = rh.get_bank_transfers()
    transfers_list = [
        convert_dict_to_typed_dict(transfer, BankTransfer) for transfer in transfers
    ]
    # Filter out None values and sort by date
    return sorted(
        [t for t in transfers_list if t is not None],
        key=lambda x: x["updated_at"],  # Now using dot notation since it's a dataclass
    )


def get_running_ytd_percentage() -> list[PercentageDate]:
    """
    Get the percentage change of the portfolio from the start of the year to the current date,
    accounting for deposits and withdrawals.

    Returns:
        list[PercentageDate]: List of daily percentage changes with dates
    """
    historical: list[EquityHistorical] = get_historical_portfolio(
        fidelity="day", span="year", bounds="regular"
    )
    transfers = get_bank_transfers()

    # Shift all transfer dates by one day
    for transfer in transfers:
        transfer["created_at"] -= datetime.timedelta(days=1)

    cur_year = historical[-1]["begins_at"].date().year
    start_equity = historical[0]["open_equity"]
    start_date = datetime.date(cur_year, 1, 1)

    # filter historical to only include days after the start date
    historical = [h for h in historical if h["begins_at"].date() >= start_date]
    # filter transfers to only include transfers after the start date
    transfers = [t for t in transfers if t["created_at"].date() >= start_date]

    # Track total deposits to adjust the base investment amount
    total_deposits = 0
    current_transfer_idx = 0

    percentages = [PercentageDate(date=start_date, percentage=0)]

    for day in historical[1:]:
        # Add any transfers that occurred on this day
        while (
            current_transfer_idx < len(transfers)
            and transfers[current_transfer_idx]["created_at"] < day["begins_at"]
        ):
            transfer = transfers[current_transfer_idx]
            if transfer["direction"] == "deposit" and transfer["state"] == "completed":
                total_deposits += transfer["amount"]
            current_transfer_idx += 1

        # Adjust the percentage calculation to account for deposits
        adjusted_start = start_equity + total_deposits
        if adjusted_start != 0:  # Prevent division by zero
            percentage = (day["close_equity"] - adjusted_start) / adjusted_start
            percentages.append(
                PercentageDate(date=day["begins_at"], percentage=percentage)
            )

    return percentages
