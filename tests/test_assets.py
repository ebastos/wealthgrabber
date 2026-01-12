from unittest.mock import MagicMock

import pytest

from wealthgrabber.assets import (
    _get_position_account_ids,
    _position_has_account,
    get_assets_data,
    print_assets,
)


@pytest.fixture
def mock_ws_client():
    client = MagicMock()

    # Mock get_security_market_data to return stock info based on security ID
    def mock_market_data(security_id, use_cache=False):
        mapping = {
            "sec-s-xeqt": {
                "stock": {"symbol": "XEQT", "name": "iShares Core Equity ETF"}
            },
            "sec-s-vfv": {"stock": {"symbol": "VFV", "name": "Vanguard S&P 500 ETF"}},
            "sec-s-large": {
                "stock": {"symbol": "LARGE", "name": "Large Position Fund"}
            },
        }
        return mapping.get(security_id, {"stock": {"symbol": "N/A", "name": "Unknown"}})

    client.get_security_market_data.side_effect = mock_market_data
    return client


@pytest.fixture
def sample_position():
    return {
        "id": "pos-123",
        "quantity": "100.50",
        "accounts": [{"id": "acc-123", "__typename": "Account"}],
        "security": {"id": "sec-s-xeqt", "__typename": "Security"},
        "totalValue": {"amount": "2525.00", "currency": "CAD"},
        "bookValue": {"amount": "2400.00", "currency": "CAD"},
    }


@pytest.fixture
def sample_position_2():
    return {
        "id": "pos-456",
        "quantity": "50.00",
        "accounts": [{"id": "acc-456", "__typename": "Account"}],
        "security": {"id": "sec-s-vfv", "__typename": "Security"},
        "totalValue": {"amount": "3150.00", "currency": "CAD"},
        "bookValue": {"amount": "3000.00", "currency": "CAD"},
    }


@pytest.fixture
def sample_position_loss():
    """Position with a loss (market value < book value)."""
    return {
        "id": "pos-loss",
        "quantity": "200.00",
        "accounts": [{"id": "acc-123", "__typename": "Account"}],
        "security": {"id": "sec-s-large", "__typename": "Security"},
        "totalValue": {"amount": "1800.00", "currency": "CAD"},
        "bookValue": {"amount": "2000.00", "currency": "CAD"},
    }


@pytest.fixture
def sample_accounts():
    return [
        {"number": "TFSA-001", "id": "acc-123", "description": "My TFSA"},
        {"number": "RRSP-001", "id": "acc-456", "description": "My RRSP"},
    ]


# Tests for helper functions
def test_position_has_account_true(sample_position):
    """Test position belongs to account."""
    assert _position_has_account(sample_position, "acc-123") is True


def test_position_has_account_false(sample_position):
    """Test position doesn't belong to account."""
    assert _position_has_account(sample_position, "acc-999") is False


def test_get_position_account_ids(sample_position):
    """Test getting account IDs from position."""
    assert _get_position_account_ids(sample_position) == ["acc-123"]


def test_get_position_account_ids_empty():
    """Test getting account IDs when empty."""
    assert _get_position_account_ids({}) == []


# Tests for print_assets
def test_print_assets_aggregated(mock_ws_client, sample_position, capsys):
    """Test printing aggregated assets."""
    mock_ws_client.get_identity_positions.return_value = [sample_position]

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # Validate table structure: header row
    assert any(
        "Symbol" in line
        and "Name" in line
        and "Qty" in line
        and "Market Value" in line
        and "P&L" in line
        for line in lines
    )

    # Validate separator lines (94 chars for assets table)
    assert any(line.strip() == "=" * 94 for line in lines)
    assert any(line.strip() == "-" * 94 for line in lines)

    # Find data row with position info
    data_row = None
    for line in lines:
        if "XEQT" in line and "100.50" in line and "2,525.00" in line:
            data_row = line
            break

    assert data_row is not None, "Expected data row with position info not found"

    # Validate total row
    assert any("Total" in line and "2,525.00" in line for line in lines)


def test_print_assets_multiple_positions(
    mock_ws_client, sample_position, sample_position_2, capsys
):
    """Test printing multiple positions with total."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,
        sample_position_2,
    ]

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # Validate table structure: header row
    assert any(
        "Symbol" in line
        and "Name" in line
        and "Qty" in line
        and "Market Value" in line
        and "P&L" in line
        for line in lines
    )

    # Validate separator lines
    assert any(line.strip() == "=" * 94 for line in lines)
    assert any(line.strip() == "-" * 94 for line in lines)

    # Find both position rows
    xeqt_row = None
    vfv_row = None
    for line in lines:
        if "XEQT" in line and "100.50" in line:
            xeqt_row = line
        if "VFV" in line and "50.00" in line:
            vfv_row = line

    assert xeqt_row is not None, "Expected XEQT position row not found"
    assert vfv_row is not None, "Expected VFV position row not found"

    # Validate total row
    assert any("Total" in line and "5,675.00" in line for line in lines)


def test_print_assets_no_positions(mock_ws_client, capsys):
    """Test behavior when no positions exist."""
    mock_ws_client.get_identity_positions.return_value = []

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    assert "No positions found" in captured.out


def test_print_assets_single_account_filter(
    mock_ws_client, sample_position, sample_position_2, capsys
):
    """Test filtering by account ID."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,
        sample_position_2,
    ]

    print_assets(mock_ws_client, account_id="acc-123")

    captured = capsys.readouterr()
    assert "XEQT" in captured.out
    assert "VFV" not in captured.out  # Should be filtered out


def test_print_assets_by_account(
    mock_ws_client, sample_position, sample_position_2, sample_accounts, capsys
):
    """Test printing assets grouped by account."""
    mock_ws_client.get_accounts.return_value = sample_accounts
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,
        sample_position_2,
    ]

    print_assets(mock_ws_client, by_account=True)

    captured = capsys.readouterr()
    assert "My TFSA" in captured.out
    assert "My RRSP" in captured.out
    assert "XEQT" in captured.out
    assert "VFV" in captured.out
    assert "Grand Total" in captured.out
    assert "5,675.00" in captured.out


def test_print_assets_by_account_no_accounts(mock_ws_client, capsys):
    """Test by-account mode when no accounts exist."""
    mock_ws_client.get_accounts.return_value = []
    mock_ws_client.get_identity_positions.return_value = []

    print_assets(mock_ws_client, by_account=True)

    captured = capsys.readouterr()
    # When there are no accounts, no positions are found
    assert "No positions found" in captured.out


def test_print_assets_by_account_no_positions(mock_ws_client, sample_accounts, capsys):
    """Test by-account mode when no positions exist."""
    mock_ws_client.get_accounts.return_value = sample_accounts
    mock_ws_client.get_identity_positions.return_value = []

    print_assets(mock_ws_client, by_account=True)

    captured = capsys.readouterr()
    assert "No positions found" in captured.out


def test_print_assets_formats_currency(mock_ws_client, capsys):
    """Test that currency values are formatted correctly."""
    position = {
        "id": "pos-789",
        "quantity": "1000.00",
        "accounts": [{"id": "acc-123"}],
        "security": {"id": "sec-s-large"},
        "totalValue": {"amount": "123456.78", "currency": "CAD"},
    }
    mock_ws_client.get_identity_positions.return_value = [position]

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    # Check thousands separator formatting
    assert "123,456.78" in captured.out


def test_print_assets_handles_missing_data(mock_ws_client, capsys):
    """Test handling of positions with missing data."""
    position = {
        "id": "pos-incomplete",
        "quantity": "10",
        "accounts": [{"id": "acc-123"}],
        "security": {},  # Missing ID
        "totalValue": {},  # Missing amount
    }
    mock_ws_client.get_identity_positions.return_value = [position]

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    assert "N/A" in captured.out  # Symbol fallback


def test_print_assets_displays_pnl(mock_ws_client, sample_position, capsys):
    """Test that P&L (Profit/Loss) is displayed correctly."""
    # sample_position has totalValue=2525 and bookValue=2400
    # P&L should be +125.00 and +5.2%
    mock_ws_client.get_identity_positions.return_value = [sample_position]

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    assert "P&L" in captured.out  # Header should contain P&L column
    assert "+125.00" in captured.out  # P&L value (2525 - 2400 = 125)
    # P&L percentage: (125 / 2400) * 100 = 5.208...% ≈ 5.2%
    # Allow for rounding variance (5.2% or 5.21%)
    assert "+5.2%" in captured.out or "+5.21%" in captured.out


def test_print_assets_displays_total_pnl(
    mock_ws_client, sample_position, sample_position_2, capsys
):
    """Test that total P&L is calculated correctly."""
    # sample_position: totalValue=2525, bookValue=2400 -> P&L=125
    # sample_position_2: totalValue=3150, bookValue=3000 -> P&L=150
    # Total: totalValue=5675, bookValue=5400 -> P&L=275, pct=5.09%
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,
        sample_position_2,
    ]

    print_assets(mock_ws_client)

    captured = capsys.readouterr()
    assert "+275.00" in captured.out  # Total P&L
    assert "+5.1%" in captured.out  # Total P&L percentage (275/5400 = 5.09%)


def test_get_assets_data_zero_book_value(mock_ws_client):
    """Test P&L calculation when book value is zero."""
    position = {
        "id": "pos-1",
        "quantity": "100.00",
        "accounts": [{"id": "acc-123"}],
        "security": {"id": "sec-s-xeqt"},
        "totalValue": {"amount": "1000.00", "currency": "CAD"},
        "bookValue": {"amount": "0.00", "currency": "CAD"},  # Zero book value
    }
    mock_ws_client.get_identity_positions.return_value = [position]

    result = get_assets_data(mock_ws_client)

    assert len(result) == 1
    assert result[0].pnl == 1000.00  # market_value - book_value
    assert result[0].pnl_pct == 0.0  # Should be 0.0 when book_value is 0


# Tests for profit/loss filtering
def test_get_assets_data_filter_profits_only(
    mock_ws_client, sample_position, sample_position_2, sample_position_loss
):
    """Test filtering to show only positions with profit."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,  # P&L = +125
        sample_position_2,  # P&L = +150
        sample_position_loss,  # P&L = -200
    ]

    result = get_assets_data(mock_ws_client, pnl_filter="profit")

    assert len(result) == 2
    # Both profitable positions should be included
    symbols = [pos.symbol for pos in result]
    assert "XEQT" in symbols
    assert "VFV" in symbols
    assert "LARGE" not in symbols  # Loss position should be excluded
    # Verify all have positive P&L
    assert all(pos.pnl > 0 for pos in result)


def test_get_assets_data_filter_losses_only(
    mock_ws_client, sample_position, sample_position_2, sample_position_loss
):
    """Test filtering to show only positions with loss."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,  # P&L = +125
        sample_position_2,  # P&L = +150
        sample_position_loss,  # P&L = -200
    ]

    result = get_assets_data(mock_ws_client, pnl_filter="loss")

    assert len(result) == 1
    # Only loss position should be included
    assert result[0].symbol == "LARGE"
    assert result[0].pnl < 0


def test_get_assets_data_no_filter_shows_all(
    mock_ws_client, sample_position, sample_position_2, sample_position_loss
):
    """Test default behavior shows all positions (no filter)."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,  # P&L = +125
        sample_position_2,  # P&L = +150
        sample_position_loss,  # P&L = -200
    ]

    result = get_assets_data(mock_ws_client, pnl_filter=None)

    assert len(result) == 3
    symbols = [pos.symbol for pos in result]
    assert "XEQT" in symbols
    assert "VFV" in symbols
    assert "LARGE" in symbols


def test_get_assets_data_filter_profits_with_zero_pnl(mock_ws_client):
    """Test that positions with exactly zero P&L are excluded from profit filter."""
    position_profit = {
        "id": "pos-profit",
        "quantity": "100.00",
        "accounts": [{"id": "acc-123"}],
        "security": {"id": "sec-s-xeqt"},
        "totalValue": {"amount": "1000.00", "currency": "CAD"},
        "bookValue": {"amount": "900.00", "currency": "CAD"},  # P&L = +100
    }
    position_zero = {
        "id": "pos-zero",
        "quantity": "100.00",
        "accounts": [{"id": "acc-123"}],
        "security": {"id": "sec-s-vfv"},
        "totalValue": {"amount": "1000.00", "currency": "CAD"},
        "bookValue": {"amount": "1000.00", "currency": "CAD"},  # P&L = 0
    }
    mock_ws_client.get_identity_positions.return_value = [
        position_profit,
        position_zero,
    ]

    result = get_assets_data(mock_ws_client, pnl_filter="profit")

    assert len(result) == 1
    assert result[0].symbol == "XEQT"
    assert result[0].pnl > 0


def test_print_assets_filter_profits_only(
    mock_ws_client, sample_position, sample_position_loss, capsys
):
    """Test printing assets filtered to show only profits."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,  # P&L = +125
        sample_position_loss,  # P&L = -200
    ]

    print_assets(mock_ws_client, pnl_filter="profit")

    captured = capsys.readouterr()
    assert "XEQT" in captured.out
    assert "LARGE" not in captured.out  # Loss position should be filtered out


def test_print_assets_filter_losses_only(
    mock_ws_client, sample_position, sample_position_loss, capsys
):
    """Test printing assets filtered to show only losses."""
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,  # P&L = +125
        sample_position_loss,  # P&L = -200
    ]

    print_assets(mock_ws_client, pnl_filter="loss")

    captured = capsys.readouterr()
    assert "LARGE" in captured.out
    assert "XEQT" not in captured.out  # Profit position should be filtered out


def test_print_assets_filter_with_by_account(
    mock_ws_client, sample_position, sample_position_loss, sample_accounts, capsys
):
    """Test profit/loss filter works with by-account mode."""
    mock_ws_client.get_accounts.return_value = sample_accounts
    mock_ws_client.get_identity_positions.return_value = [
        sample_position,  # P&L = +125
        sample_position_loss,  # P&L = -200
    ]

    print_assets(mock_ws_client, by_account=True, pnl_filter="profit")

    captured = capsys.readouterr()
    assert "XEQT" in captured.out
    assert "LARGE" not in captured.out
    assert "My TFSA" in captured.out
