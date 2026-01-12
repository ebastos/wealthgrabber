import re
from datetime import datetime
from typing import Optional

from ws_api import WealthsimpleAPI

from .formatters import get_formatter
from .models import ActivityData

DIVIDEND_TYPES = {"DIY_DIVIDEND", "DIVIDEND", "DISTRIBUTION"}


def is_dividend_activity(activity: dict) -> bool:
    """Check if activity is a dividend."""
    act_type = activity.get("type", "").upper()
    description = activity.get("description", "").upper()
    return any(div in act_type or div in description for div in DIVIDEND_TYPES)


def get_account_id_by_number(ws: WealthsimpleAPI, account_number: str) -> Optional[str]:
    """Look up account ID by account number."""
    accounts = ws.get_accounts()
    for account in accounts:
        if account.get("number") == account_number:
            return account.get("id")
    return None


def _get_security_name(ws: WealthsimpleAPI, security_id: str, cache: dict) -> str:
    """Get name for a security, using cache to avoid redundant API calls."""
    if security_id in cache:
        return cache[security_id]

    name = security_id  # Fallback to ID if lookup fails

    if security_id:
        try:
            market_data = ws.get_security_market_data(security_id, use_cache=False)
            if market_data and market_data.get("stock"):
                stock = market_data["stock"]
                symbol = stock.get("symbol", "")
                stock_name = stock.get("name", "")
                # Prefer symbol if available, otherwise use name
                name = symbol if symbol else (stock_name if stock_name else security_id)
        except Exception:
            # Fallback for securities that can't be looked up
            pass

    cache[security_id] = name
    return name


def _enhance_description(
    ws: WealthsimpleAPI, activity: dict, security_cache: dict
) -> str:
    """Enhance activity description by replacing security IDs with names."""
    description = activity.get("description", "N/A")

    # First, check if the activity has a direct security reference
    security = activity.get("security")
    security_id = None

    if security:
        security_id = security.get("id") if isinstance(security, dict) else security

    # If no direct security reference, try to extract from description
    # Look for patterns like [sec-s-XXXX or sec-s-XXXX
    if not security_id:
        # Try to find security ID in description
        match = re.search(r"\[?(sec-[a-z]-[a-f0-9]+)", description)
        if match:
            security_id = match.group(1)

    if security_id:
        security_name = _get_security_name(ws, security_id, security_cache)
        # Replace the security ID with the name in the description
        description = re.sub(r"\[?(sec-[a-z]-[a-f0-9]+)\]?", security_name, description)

        # For DIY_BUY activities that might not have security in description,
        # append the security name
        if "DIY_BUY" in activity.get("type", "") and security_name not in description:
            # Extract the quantity if present
            qty_match = re.search(r"buy (\d+\.?\d*)", description)
            if qty_match:
                description = (
                    f"Dividend reinvestment: buy {qty_match.group(1)} {security_name}"
                )

    return description


def _transform_activity(
    ws: WealthsimpleAPI,
    activity: dict,
    security_cache: dict,
    account_label: Optional[str] = None,
) -> ActivityData:
    """Transform raw activity dict to ActivityData.

    Args:
        ws: Authenticated WealthsimpleAPI client
        activity: Raw activity dict from API
        security_cache: Cache for security lookups
        account_label: Optional account label for grouping

    Returns:
        ActivityData object
    """
    date_str = _format_date(activity.get("occurredAt", ""))
    act_type = activity.get("type", "N/A")[:14]
    description = _enhance_description(ws, activity, security_cache)[:34]
    amount = float(activity.get("amount") or 0)
    currency = activity.get("currency", "CAD")
    sign = "+" if activity.get("amountSign") == "positive" else "-"

    return ActivityData(
        date=date_str,
        activity_type=act_type,
        description=description,
        amount=amount,
        currency=currency,
        sign=sign,
        account_label=account_label,
    )


def _process_account_activities(
    ws: WealthsimpleAPI,
    account_id: str,
    account_label: Optional[str],
    security_cache: dict,
    dividends_only: bool,
    limit: int,
) -> list[ActivityData]:
    """Process activities for a single account.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Account ID to fetch activities for
        account_label: Optional label for grouping (e.g., "TFSA (ACC-001)")
        security_cache: Shared cache for security lookups
        dividends_only: Whether to filter for dividend activities only
        limit: Maximum number of activities to return

    Returns:
        List of ActivityData objects for the account
    """
    activities = ws.get_activities(account_id)

    if dividends_only:
        activities = [a for a in activities if is_dividend_activity(a)]

    activities = activities[:limit]

    return [
        _transform_activity(ws, act, security_cache, account_label)
        for act in activities
    ]


def get_activities_data(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    dividends_only: bool = False,
    limit: int = 50,
) -> list[ActivityData]:
    """Fetch and transform activity data.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter activities
        dividends_only: Whether to include only dividend activities
        limit: Maximum number of activities per account

    Returns:
        List of ActivityData objects
    """
    result = []
    security_cache: dict[str, str] = {}

    if account_id:
        # Single account mode: no account label
        result = _process_account_activities(
            ws, account_id, None, security_cache, dividends_only, limit
        )
    else:
        # All accounts mode - fetch accounts for labeling
        accounts = ws.get_accounts()
        if not accounts:
            return []

        for account in accounts:
            acc_id = account.get("id")
            acc_label = f"{account.get('description', 'Unknown')} ({account.get('number', 'N/A')})"
            result.extend(
                _process_account_activities(
                    ws, acc_id, acc_label, security_cache, dividends_only, limit
                )
            )

    return result


def print_activities(
    ws: WealthsimpleAPI,
    account_id: Optional[str] = None,
    dividends_only: bool = False,
    limit: int = 50,
    output_format: str = "table",
    verbose: bool = False,
) -> None:
    """Fetch and print activities.

    Args:
        ws: Authenticated WealthsimpleAPI client
        account_id: Optional account ID to filter activities
        dividends_only: Whether to show only dividend activities
        limit: Maximum number of activities per account
        output_format: Output format - 'table', 'json', or 'csv' (default 'table')
        verbose: If True, print status messages during execution
    """
    if verbose:
        print("\nFetching activities...")

    activities_data = get_activities_data(ws, account_id, dividends_only, limit)

    if not activities_data:
        print("No activities found.")
        return

    formatter = get_formatter(output_format)

    if output_format == "table":
        # For table format, group by account if multi-account
        from itertools import groupby

        if not account_id:
            # Multi-account mode: group by account label
            activities_data_sorted = sorted(
                activities_data, key=lambda a: a.account_label or ""
            )

            for account_label, group_iter in groupby(
                activities_data_sorted, key=lambda a: a.account_label
            ):
                group = list(group_iter)
                # Print header with account label
                suffix = " - Dividends Only" if dividends_only else ""
                print("\n" + "=" * 80)
                if account_label:
                    print(f"Account: {account_label}{suffix}")
                print("=" * 80)
                print(f"{'Date':<12} {'Type':<14} {'Description':<34} {'Amount':>18}")
                print("-" * 80)

                # Print activities using formatter (will skip account header)
                for act in group:
                    print(
                        f"{act.date:<12} {act.activity_type:<14} {act.description:<34} "
                        f"{act.sign}{act.amount:>14,.2f} {act.currency}"
                    )

            print("=" * 80)
        else:
            # Single account mode
            output = formatter.format_activities(activities_data)
            print(output)
    else:
        # For JSON and CSV, use formatter directly
        output = formatter.format_activities(activities_data)
        print(output)


def _format_date(iso_date: str) -> str:
    """Format ISO date to YYYY-MM-DD."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_date[:10] if len(iso_date) >= 10 else "N/A"
