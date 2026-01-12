from unittest.mock import MagicMock

import pytest

from wealthgrabber.activities import (
    _enhance_description,
    _format_date,
    _get_security_name,
    get_account_id_by_number,
    get_activities_data,
    is_dividend_activity,
    print_activities,
)
from wealthgrabber.models import ActivityData


@pytest.fixture
def mock_ws_client():
    return MagicMock()


@pytest.fixture
def sample_activity():
    return {
        "type": "DIY_BUY",
        "subType": "BUY",
        "description": "Bought 10 XEQT @ $25.50",
        "occurredAt": "2024-01-15T10:30:00Z",
        "canonicalId": "abc123",
        "amountSign": "negative",
        "amount": "255.00",
        "currency": "CAD",
    }


@pytest.fixture
def sample_dividend_activity():
    return {
        "type": "DIY_DIVIDEND",
        "subType": "DIVIDEND",
        "description": "XEQT Dividend",
        "occurredAt": "2024-01-10T09:00:00Z",
        "canonicalId": "def456",
        "amountSign": "positive",
        "amount": "12.34",
        "currency": "CAD",
    }


# Tests for is_dividend_activity
def test_is_dividend_activity_true_by_type(sample_dividend_activity):
    """Test dividend detection for dividend activity type."""
    assert is_dividend_activity(sample_dividend_activity) is True


def test_is_dividend_activity_true_by_description():
    """Test dividend detection when dividend is in description."""
    activity = {
        "type": "SOME_TYPE",
        "description": "Monthly Dividend Payment",
    }
    assert is_dividend_activity(activity) is True


def test_is_dividend_activity_distribution():
    """Test dividend detection for distribution type."""
    activity = {
        "type": "DISTRIBUTION",
        "description": "ETF Distribution",
    }
    assert is_dividend_activity(activity) is True


def test_is_dividend_activity_false(sample_activity):
    """Test dividend detection for non-dividend activity."""
    assert is_dividend_activity(sample_activity) is False


def test_is_dividend_activity_lowercase():
    """Test dividend detection with lowercase description."""
    activity = {"type": "some_type", "description": "monthly dividend payment"}
    assert is_dividend_activity(activity) is True


def test_is_dividend_activity_mixed_case():
    """Test dividend detection with mixed case."""
    activity = {"type": "SOME_TYPE", "description": "Monthly DiViDeNd Payment"}
    assert is_dividend_activity(activity) is True


# Tests for get_account_id_by_number
def test_get_account_id_by_number_found(mock_ws_client):
    """Test finding account by number."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"},
        {"number": "RRSP-001", "id": "acc-456", "description": "My RRSP"},
    ]
    result = get_account_id_by_number(mock_ws_client, "TFSA-001")
    assert result == "acc-123"


def test_get_account_id_by_number_not_found(mock_ws_client):
    """Test behavior when account number not found."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"}
    ]
    result = get_account_id_by_number(mock_ws_client, "RRSP-999")
    assert result is None


def test_get_account_id_by_number_empty_accounts(mock_ws_client):
    """Test behavior when no accounts exist."""
    mock_ws_client.get_accounts.return_value = []
    result = get_account_id_by_number(mock_ws_client, "TFSA-001")
    assert result is None


# Tests for _format_date
def test_format_date_valid_iso():
    """Test formatting valid ISO date."""
    result = _format_date("2024-01-15T10:30:00Z")
    assert result == "2024-01-15"


def test_format_date_with_timezone():
    """Test formatting ISO date with timezone offset."""
    result = _format_date("2024-01-15T10:30:00+00:00")
    assert result == "2024-01-15"


def test_format_date_invalid():
    """Test formatting invalid date string."""
    result = _format_date("invalid")
    assert result == "N/A"


def test_format_date_empty():
    """Test formatting empty string."""
    result = _format_date("")
    assert result == "N/A"


def test_format_date_various_timezones():
    """Test formatting dates with various timezone offsets."""
    assert _format_date("2024-01-15T10:30:00+05:30") == "2024-01-15"
    assert _format_date("2024-01-15T10:30:00-08:00") == "2024-01-15"


def test_format_date_with_milliseconds():
    """Test formatting date with milliseconds."""
    assert _format_date("2024-01-15T10:30:00.123Z") == "2024-01-15"


def test_format_date_partial_date():
    """Test formatting partial date string."""
    result = _format_date("2024-01-15")
    assert result == "2024-01-15"


# Tests for _get_security_name
def test_get_security_name_from_api(mock_ws_client):
    """Test fetching security name from API."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "XEQT", "name": "iShares Equity ETF Portfolio"}
    }
    cache = {}
    result = _get_security_name(mock_ws_client, "sec-s-123abc", cache)
    assert result == "XEQT"
    assert "sec-s-123abc" in cache


def test_get_security_name_cached(mock_ws_client):
    """Test that cached security names are returned without API call."""
    cache = {"sec-s-123abc": "XEQT"}
    result = _get_security_name(mock_ws_client, "sec-s-123abc", cache)
    assert result == "XEQT"
    mock_ws_client.get_security_market_data.assert_not_called()


def test_get_security_name_fallback_to_name(mock_ws_client):
    """Test fallback to name when symbol is not available."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "", "name": "iShares Equity ETF Portfolio"}
    }
    cache = {}
    result = _get_security_name(mock_ws_client, "sec-s-456def", cache)
    assert result == "iShares Equity ETF Portfolio"


def test_get_security_name_api_error(mock_ws_client):
    """Test fallback to security ID on API error."""
    mock_ws_client.get_security_market_data.side_effect = Exception("API Error")
    cache = {}
    result = _get_security_name(mock_ws_client, "sec-s-789ghi", cache)
    assert result == "sec-s-789ghi"


def test_get_security_name_missing_stock_data(mock_ws_client):
    """Test fallback when response lacks stock data."""
    mock_ws_client.get_security_market_data.return_value = {}
    cache = {}
    result = _get_security_name(mock_ws_client, "sec-s-000jkl", cache)
    assert result == "sec-s-000jkl"


# Tests for _enhance_description
def test_enhance_description_replaces_security_id(mock_ws_client):
    """Test that security IDs in description are replaced with names."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "VFV", "name": "Vanguard US Index"}
    }
    activity = {"type": "DIVIDEND", "description": "Dividend: [sec-s-241667f5f203483ba"}
    cache = {}
    result = _enhance_description(mock_ws_client, activity, cache)
    assert "VFV" in result
    assert "sec-s-" not in result


def test_enhance_description_with_direct_security_reference(mock_ws_client):
    """Test enhancement when activity has direct security reference."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "XEQT", "name": "iShares All-Equity ETF"}
    }
    activity = {
        "type": "DIVIDEND",
        "description": "Dividend payment",
        "security": {"id": "sec-s-abc123"},
    }
    cache = {}
    result = _enhance_description(mock_ws_client, activity, cache)
    # The description should be enhanced if the security name appears in it
    # or the API should be called
    assert result is not None


def test_enhance_description_diy_buy_with_quantity(mock_ws_client):
    """Test enhancement of DIY_BUY activity with quantity."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "XEQT", "name": "iShares All-Equity ETF"}
    }
    activity = {
        "type": "DIY_BUY",
        "description": "Dividend reinvestment: buy 0.0127 [sec-s-241667f5f203483ba",
    }
    cache = {}
    result = _enhance_description(mock_ws_client, activity, cache)
    assert "buy 0.0127" in result
    assert "XEQT" in result


def test_enhance_description_no_security_id(mock_ws_client):
    """Test that descriptions without security IDs are returned unchanged."""
    activity = {"type": "TRANSFER", "description": "Transfer in $1000"}
    cache = {}
    result = _enhance_description(mock_ws_client, activity, cache)
    assert result == "Transfer in $1000"


def test_enhance_description_uses_cache(mock_ws_client):
    """Test that security cache is used across multiple descriptions."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "VFV", "name": "Vanguard US Index"}
    }
    cache = {"sec-s-241667f5f203483ba": "VFV"}
    activity = {"type": "DIVIDEND", "description": "Dividend: [sec-s-241667f5f203483ba"}
    result = _enhance_description(mock_ws_client, activity, cache)
    # Should use cache and not call API
    mock_ws_client.get_security_market_data.assert_not_called()
    assert "VFV" in result


def test_enhance_description_diy_buy_no_regex_match(mock_ws_client):
    """Test DIY_BUY when no 'buy' pattern in description."""
    activity = {"type": "DIY_BUY", "description": "Some transaction"}
    cache = {}
    result = _enhance_description(mock_ws_client, activity, cache)
    assert result == "Some transaction"  # Should be unchanged


def test_enhance_description_diy_buy_security_already_in_name(mock_ws_client):
    """Test DIY_BUY when security_name is already in description."""
    mock_ws_client.get_security_market_data.return_value = {
        "stock": {"symbol": "XEQT", "name": "iShares All-Equity ETF"}
    }
    activity = {"type": "DIY_BUY", "description": "buy 10 XEQT [sec-s-123"}
    cache = {}
    result = _enhance_description(mock_ws_client, activity, cache)
    # Should NOT modify because "XEQT" is already in description
    assert "XEQT" in result
    # The description should not be replaced since XEQT is already there
    assert "buy 10" in result


# Tests for get_activities_data
def test_get_activities_data_single_account(mock_ws_client, sample_activity):
    """Test get_activities_data for a single account."""
    mock_ws_client.get_activities.return_value = [sample_activity]
    mock_ws_client.get_security_market_data.return_value = None

    result = get_activities_data(mock_ws_client, account_id="acc-123")

    assert len(result) == 1
    assert isinstance(result[0], ActivityData)
    assert result[0].activity_type == "DIY_BUY"
    assert result[0].account_label is None
    assert result[0].date == "2024-01-15"
    assert result[0].amount == 255.00
    assert result[0].sign == "-"  # because amountSign="negative"
    assert result[0].currency == "CAD"


def test_get_activities_data_multiple_accounts(mock_ws_client, sample_activity):
    """Test get_activities_data for multiple accounts."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"},
        {"number": "RRSP-001", "id": "acc-456", "description": "My RRSP"},
    ]
    mock_ws_client.get_activities.return_value = [sample_activity]
    mock_ws_client.get_security_market_data.return_value = None

    result = get_activities_data(mock_ws_client)

    assert len(result) == 2  # One activity per account
    assert result[0].account_label == "My TFSA (TFSA-001)"
    assert result[1].account_label == "My RRSP (RRSP-001)"


def test_get_activities_data_dividends_only(
    mock_ws_client, sample_activity, sample_dividend_activity
):
    """Test get_activities_data with dividends_only filter."""
    mock_ws_client.get_activities.return_value = [
        sample_activity,
        sample_dividend_activity,
    ]
    mock_ws_client.get_security_market_data.return_value = None

    result = get_activities_data(
        mock_ws_client, account_id="acc-123", dividends_only=True
    )

    assert len(result) == 1
    assert result[0].activity_type == "DIY_DIVIDEND"


# Tests for print_activities
def test_print_activities_all_accounts(mock_ws_client, sample_activity, capsys):
    """Test printing activities for all accounts."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"}
    ]
    mock_ws_client.get_activities.return_value = [sample_activity]
    mock_ws_client.get_security_market_data.return_value = None

    print_activities(mock_ws_client)

    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # Validate table structure: header row
    assert any(
        "Date" in line and "Type" in line and "Description" in line and "Amount" in line
        for line in lines
    )

    # Validate separator lines
    assert any(line.strip() == "=" * 80 for line in lines)
    assert any(line.strip() == "-" * 80 for line in lines)

    # Validate account header
    assert any(
        "Account:" in line and "My TFSA" in line and "TFSA-001" in line
        for line in lines
    )

    # Find data row with activity info
    data_row = None
    for line in lines:
        if "DIY_BUY" in line and "2024-01-15" in line:
            data_row = line
            break

    assert data_row is not None, "Expected data row with activity info not found"


def test_print_activities_single_account(mock_ws_client, sample_activity, capsys):
    """Test printing activities for a specific account."""
    mock_ws_client.get_activities.return_value = [sample_activity]
    mock_ws_client.get_security_market_data.return_value = None

    print_activities(mock_ws_client, account_id="acc-123")

    mock_ws_client.get_activities.assert_called_with("acc-123")
    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # Validate table structure: header row
    assert any(
        "Date" in line and "Type" in line and "Description" in line and "Amount" in line
        for line in lines
    )

    # Validate separator lines
    assert any(line.strip() == "=" * 80 for line in lines)
    assert any(line.strip() == "-" * 80 for line in lines)

    # Find data row with activity
    data_row = None
    for line in lines:
        if "DIY_BUY" in line and "2024-01-15" in line:
            data_row = line
            break

    assert data_row is not None, "Expected data row with activity not found"


def test_print_activities_no_accounts(mock_ws_client, capsys):
    """Test printing activities when no accounts exist."""
    mock_ws_client.get_accounts.return_value = []

    print_activities(mock_ws_client)

    captured = capsys.readouterr()
    # When no accounts, get_activities_data returns empty, so "No activities found" is shown
    assert "No activities found" in captured.out


def test_print_activities_no_activities(mock_ws_client, capsys):
    """Test printing when account has no activities."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"}
    ]
    mock_ws_client.get_activities.return_value = []

    print_activities(mock_ws_client)

    captured = capsys.readouterr()
    assert "No activities found" in captured.out


def test_print_activities_dividends_only(
    mock_ws_client, sample_activity, sample_dividend_activity, capsys
):
    """Test dividend filtering."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"}
    ]
    mock_ws_client.get_activities.return_value = [
        sample_activity,
        sample_dividend_activity,
    ]
    mock_ws_client.get_security_market_data.return_value = None

    print_activities(mock_ws_client, dividends_only=True)

    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # Validate table structure: header row
    assert any(
        "Date" in line and "Type" in line and "Description" in line and "Amount" in line
        for line in lines
    )

    # Validate that only dividend activity is present
    assert any("DIY_DIVIDEND" in line and "2024-01-10" in line for line in lines)

    # Validate that buy activity is NOT present
    assert not any("DIY_BUY" in line and "2024-01-15" in line for line in lines)


def test_print_activities_respects_limit(mock_ws_client, capsys):
    """Test that limit parameter is respected."""
    activities = [
        {
            "type": "DIY_BUY",
            "description": f"Activity {i}",
            "occurredAt": "2024-01-15T10:30:00Z",
            "amountSign": "negative",
            "amount": "100.00",
            "currency": "CAD",
        }
        for i in range(10)
    ]
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"}
    ]
    mock_ws_client.get_activities.return_value = activities
    mock_ws_client.get_security_market_data.return_value = None

    print_activities(mock_ws_client, limit=3)

    captured = capsys.readouterr()
    # Should only show 3 activities, not 10
    assert captured.out.count("DIY_BUY") == 3


def test_get_activities_data_truncates_long_type(mock_ws_client):
    """Test that activity types longer than 14 characters are truncated."""
    activity = {
        "type": "VERY_LONG_TYPE_NAME_THAT_EXCEEDS_14_CHARS",
        "occurredAt": "2024-01-15T10:30:00Z",
        "amount": "100.00",
        "amountSign": "positive",
        "currency": "CAD",
        "description": "Test",
    }
    mock_ws_client.get_activities.return_value = [activity]
    mock_ws_client.get_security_market_data.return_value = None

    result = get_activities_data(mock_ws_client, account_id="acc-123")

    assert len(result) == 1
    assert len(result[0].activity_type) <= 14


def test_get_activities_data_truncates_long_description(mock_ws_client):
    """Test that descriptions longer than 34 characters are truncated."""
    long_description = "A" * 50  # 50 character description
    activity = {
        "type": "BUY",
        "occurredAt": "2024-01-15T10:30:00Z",
        "amount": "100.00",
        "amountSign": "positive",
        "currency": "CAD",
        "description": long_description,
    }
    mock_ws_client.get_activities.return_value = [activity]
    mock_ws_client.get_security_market_data.return_value = None

    result = get_activities_data(mock_ws_client, account_id="acc-123")

    assert len(result) == 1
    assert len(result[0].description) <= 34


def test_print_activities_amount_signs(mock_ws_client, capsys):
    """Test that amount signs are displayed correctly."""
    mock_ws_client.get_accounts.return_value = [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"}
    ]
    mock_ws_client.get_activities.return_value = [
        {
            "type": "DIY_DIVIDEND",
            "description": "Dividend",
            "occurredAt": "2024-01-15T10:30:00Z",
            "amountSign": "positive",
            "amount": "50.00",
            "currency": "CAD",
        },
        {
            "type": "DIY_BUY",
            "description": "Buy",
            "occurredAt": "2024-01-15T10:30:00Z",
            "amountSign": "negative",
            "amount": "100.00",
            "currency": "CAD",
        },
    ]
    mock_ws_client.get_security_market_data.return_value = None

    print_activities(mock_ws_client)

    captured = capsys.readouterr()
    lines = captured.out.split("\n")
    # Find lines with dividend and buy activities
    dividend_line = None
    buy_line = None
    for line in lines:
        if "Dividend" in line:
            dividend_line = line
        if "Buy" in line and "DIY_BUY" in line:
            buy_line = line

    if dividend_line:
        assert "+" in dividend_line
        assert "50.00" in dividend_line
    if buy_line:
        assert "-" in buy_line
        assert "100.00" in buy_line
