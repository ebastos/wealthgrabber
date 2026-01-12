from unittest.mock import MagicMock

import pytest

from wealthgrabber.accounts import get_accounts_data, print_accounts
from wealthgrabber.models import AccountData


@pytest.fixture
def mock_ws_client():
    return MagicMock()


def test_get_accounts_data_empty(mock_ws_client):
    """Test get_accounts_data with no accounts."""
    mock_ws_client.get_accounts.return_value = []
    result = get_accounts_data(mock_ws_client)
    assert result == []


def test_get_accounts_data_valid(mock_ws_client):
    """Test get_accounts_data with valid accounts."""
    mock_ws_client.get_accounts.return_value = [
        {
            "description": "Test Account",
            "number": "123456",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "1000.50", "currency": "CAD"}
                }
            },
        }
    ]
    result = get_accounts_data(mock_ws_client)
    assert len(result) == 1
    assert isinstance(result[0], AccountData)
    assert result[0].description == "Test Account"
    assert result[0].number == "123456"
    assert result[0].value == 1000.50


def test_print_accounts_output(mock_ws_client, capsys):
    """Test print_accounts output generation."""
    mock_ws_client.get_accounts.return_value = [
        {
            "description": "My TFSA",
            "number": "TFSA-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "5000.00", "currency": "CAD"}
                }
            },
        }
    ]

    print_accounts(mock_ws_client)

    captured = capsys.readouterr()
    lines = captured.out.split("\n")

    # Validate table structure: header row
    assert any(
        "Account" in line and "Number" in line and "Value" in line for line in lines
    )

    # Validate separator lines
    assert any(line.strip() == "=" * 80 for line in lines)
    assert any(line.strip() == "-" * 80 for line in lines)

    # Find data row (contains all expected values)
    data_row = None
    for line in lines:
        if "My TFSA" in line and "TFSA-001" in line and "5,000.00" in line:
            data_row = line
            break

    assert data_row is not None, "Expected data row with account info not found"

    # Validate total row
    assert any("Total" in line and "5,000.00" in line for line in lines)


def test_get_accounts_data_zero_balance_filtering(mock_ws_client):
    """Test that zero balance accounts are filtered by default."""
    mock_ws_client.get_accounts.return_value = [
        {
            "description": "Zero Balance Account",
            "number": "ZERO-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "0.00", "currency": "CAD"}
                }
            },
        }
    ]

    # Default behavior: filter out zero balance
    result = get_accounts_data(mock_ws_client)
    assert len(result) == 0

    # Explicit behavior: show zero balance
    result = get_accounts_data(mock_ws_client, show_zero_balances=True)
    assert len(result) == 1
    assert result[0].description == "Zero Balance Account"


def test_print_accounts_json_format(mock_ws_client, capsys):
    """Test print_accounts with JSON format."""
    import json

    mock_ws_client.get_accounts.return_value = [
        {
            "description": "My Account",
            "number": "ACC-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "1000.00", "currency": "CAD"}
                }
            },
        }
    ]

    print_accounts(mock_ws_client, output_format="json")
    captured = capsys.readouterr()

    # Parse JSON and validate structure
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["description"] == "My Account"
    assert data[0]["number"] == "ACC-001"
    assert data[0]["value"] == 1000.00
    assert data[0]["currency"] == "CAD"


def _get_account_descriptions(accounts) -> set[str]:
    """Extract descriptions from account list."""
    return {acc.description for acc in accounts}


def test_get_accounts_data_liquid_only_filtering(mock_ws_client):
    """Test that non-liquid accounts are filtered when liquid_only is True."""
    accounts_data = [
        ("My TFSA", "TFSA-001", "5000.00"),
        ("My RRSP Account", "RRSP-001", "10000.00"),
        ("LIRA Fund", "LIRA-001", "8000.00"),
        ("Private Equity Investment", "PE-001", "15000.00"),
        ("Private Credit Fund", "PC-001", "12000.00"),
        ("Margin Account", "MAR-001", "20000.00"),
    ]

    def create_account(description, number, amount):
        return {
            "description": description,
            "number": number,
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": amount, "currency": "CAD"}
                }
            },
        }

    mock_ws_client.get_accounts.return_value = [
        create_account(desc, num, amt) for desc, num, amt in accounts_data
    ]

    # Default behavior: show all accounts
    result = get_accounts_data(mock_ws_client, show_zero_balances=True)
    descriptions = _get_account_descriptions(result)
    assert len(result) == 6
    assert descriptions == {desc for desc, _, _ in accounts_data}

    # Liquid-only behavior: filter out RRSP, LIRA, Private Equity, Private Credit
    result = get_accounts_data(
        mock_ws_client, show_zero_balances=True, liquid_only=True
    )
    descriptions = _get_account_descriptions(result)
    assert len(result) == 2
    assert descriptions == {"My TFSA", "Margin Account"}

    # Verify non-liquid accounts are excluded
    non_liquid = {
        "My RRSP Account",
        "LIRA Fund",
        "Private Equity Investment",
        "Private Credit Fund",
    }
    assert not descriptions.intersection(non_liquid)


def test_get_accounts_data_liquid_only_case_insensitive(mock_ws_client):
    """Test that liquid_only filtering is case-insensitive."""
    mock_ws_client.get_accounts.return_value = [
        {
            "description": "my rrsp account",
            "number": "RRSP-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "10000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "LIRA fund",
            "number": "LIRA-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "8000.00", "currency": "CAD"}
                }
            },
        },
    ]

    # These should be filtered out even with different casing
    result = get_accounts_data(
        mock_ws_client, show_zero_balances=True, liquid_only=True
    )
    assert len(result) == 0


def test_get_accounts_data_filter_combinations(mock_ws_client):
    """Test combinations of filters work correctly together."""
    mock_ws_client.get_accounts.return_value = [
        {
            "description": "My TFSA",
            "number": "TFSA-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "5000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "My RRSP Account",
            "number": "RRSP-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "0.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "Margin Account",
            "number": "MAR-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "20000.00", "currency": "CAD"}
                }
            },
        },
    ]

    # Test: liquid_only=True + show_zero_balances=False
    result = get_accounts_data(
        mock_ws_client, liquid_only=True, show_zero_balances=False
    )
    descriptions = {acc.description for acc in result}
    expected = {
        "My TFSA",
        "Margin Account",
    }  # TFSA and Margin (not RRSP with zero balance)
    assert descriptions == expected

    # Test: not_liquid=True + show_zero_balances=True
    result = get_accounts_data(mock_ws_client, not_liquid=True, show_zero_balances=True)
    descriptions = {acc.description for acc in result}
    expected = {"My RRSP Account"}  # Only RRSP (non-liquid, zero balance included)
    assert descriptions == expected


def test_get_accounts_data_not_liquid_filtering(mock_ws_client):
    """Test that liquid accounts are filtered when not_liquid is True."""
    mock_ws_client.get_accounts.return_value = [
        {
            "description": "My TFSA",
            "number": "TFSA-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "5000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "My RRSP Account",
            "number": "RRSP-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "10000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "LIRA Fund",
            "number": "LIRA-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "8000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "Private Equity Investment",
            "number": "PE-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "15000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "Private Credit Fund",
            "number": "PC-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "12000.00", "currency": "CAD"}
                }
            },
        },
        {
            "description": "Margin Account",
            "number": "MAR-001",
            "financials": {
                "currentCombined": {
                    "netLiquidationValue": {"amount": "20000.00", "currency": "CAD"}
                }
            },
        },
    ]

    # not_liquid=True: show only non-liquid accounts
    result = get_accounts_data(mock_ws_client, show_zero_balances=True, not_liquid=True)
    assert len(result) == 4
    descriptions = {acc.description for acc in result}
    expected = {
        "My RRSP Account",
        "LIRA Fund",
        "Private Equity Investment",
        "Private Credit Fund",
    }
    assert descriptions == expected
