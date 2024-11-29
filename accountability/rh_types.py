"""
Type definitions for Robinhood API responses and helper functions for type conversion.
Includes TypedDict definitions for portfolio data, holdings, and bank transfers.
"""

import datetime
import logging
from typing import (
    TypedDict,
    Optional,
    Literal,
    Any,
    get_type_hints,
    get_args,
    get_origin,
)

logger = logging.getLogger(__name__)


class PercentageDate(TypedDict):
    """Represents a percentage change at a specific date."""

    date: datetime.datetime
    percentage: float


class Holding(TypedDict):
    """Represents a stock holding in a portfolio."""

    price: float
    quantity: float
    average_buy_price: float
    equity: float
    equity_change: float
    percent_change: float
    percentage: float
    name: str
    id: str
    pe_ratio: float
    type: str
    intraday_percent_change: float


class EquityHistorical(TypedDict):
    """Historical equity data point."""

    adjusted_open_equity: float
    adjusted_close_equity: float
    open_equity: float
    close_equity: float
    open_market_value: float
    close_market_value: float
    begins_at: datetime.datetime
    net_return: float
    session: str


class HistoricalPortfolio(TypedDict):
    """Complete historical portfolio data."""

    adjusted_open_equity: float
    adjusted_previous_close_equity: float
    open_equity: float
    previous_close_equity: float
    open_time: datetime.datetime
    interval: str
    span: str
    bounds: str
    total_return: float
    equity_historicals: list[EquityHistorical]
    use_new_hp: bool


class BankTransfer(TypedDict):
    """Represents a bank transfer transaction."""

    id: str
    url: str
    ref_id: str
    cancel: Optional[str]
    ach_relationship: str
    account: str
    amount: float
    direction: str  # 'deposit' or 'withdraw'
    state: str  # 'completed', 'pending', etc.
    created_at: datetime.datetime
    updated_at: datetime.datetime


# Type aliases with proper PascalCase naming
FidelityType = Literal["5minute", "10minute", "hour", "day", "week"]
SpanType = Literal["day", "week", "month", "3month", "year"]
BoundsType = Literal["regular", "extended", "trading"]


def _convert_value_to_type(value: Any, target_type: type) -> Any:
    """Helper function to convert a value to a specific type."""
    if value is None:
        return None

    if target_type == datetime.datetime and isinstance(value, str):
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))

    if target_type == float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                logger.error("Could not convert string '%s' to float", value)
                return 0.0
        return 0.0

    return value


def convert_dict_to_typed_dict(data: dict | None, target_type: type) -> Any:
    """
    Convert a dictionary to a TypedDict with proper type conversion.

    Args:
        data: Source dictionary to convert
        target_type: Target TypedDict class

    Returns:
        Converted TypedDict instance or None if conversion fails
    """
    if data is None:
        logger.error("Received None data when converting to %s", target_type.__name__)
        return None

    if not isinstance(data, dict):
        logger.error(
            "Expected dict, got %s when converting to %s",
            type(data),
            target_type.__name__,
        )
        return None

    try:
        type_hints = get_type_hints(target_type)
        result = {}

        for field_name, field_type in type_hints.items():
            try:
                field_value = data.get(field_name)

                # Handle list types
                if get_origin(field_type) is list:
                    element_type = get_args(field_type)[0]
                    if isinstance(field_value, list):
                        result[field_name] = [
                            (
                                convert_dict_to_typed_dict(item, element_type)
                                if isinstance(item, dict)
                                else item
                            )
                            for item in field_value
                        ]
                    else:
                        result[field_name] = []
                # Handle nested TypedDicts
                elif hasattr(field_type, "__annotations__"):
                    result[field_name] = convert_dict_to_typed_dict(
                        field_value, field_type
                    )
                # Handle basic types
                else:
                    result[field_name] = _convert_value_to_type(field_value, field_type)

            except Exception as e:
                logger.error("Error converting field %s: %s", field_name, str(e))
                result[field_name] = None

        return result

    except Exception as e:
        logger.error("Error in convert_dict_to_typed_dict: %s", str(e))
        logger.error("Target type: %s", target_type.__name__)
        logger.error("Input data: %s", data)
        return None
