"""Output formatters for different data formats."""

import csv
import json
from dataclasses import asdict
from io import StringIO
from typing import Optional, Protocol, Sequence

from .models import AccountData, ActivityData, PositionData


def _calculate_position_totals(
    positions: Sequence[PositionData],
) -> tuple[float, float, float, float]:
    """Calculate total position values and P&L.

    Args:
        positions: Sequence of positions

    Returns:
        Tuple of (total_value, total_book, total_pnl, total_pnl_pct)
    """
    total_value = sum(p.market_value for p in positions)
    total_book = sum(p.book_value for p in positions)
    total_pnl = total_value - total_book
    total_pnl_pct = (total_pnl / total_book * 100) if total_book != 0 else 0.0
    return total_value, total_book, total_pnl, total_pnl_pct


class FormatterProtocol(Protocol):
    """Protocol for data formatters."""

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format account data."""
        ...

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activity data."""
        ...

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format position data."""
        ...


class TableFormatter:
    """Format data as aligned ASCII tables."""

    @staticmethod
    def _format_position_row(pos: PositionData) -> str:
        """Format a single position as a table row.

        Args:
            pos: Position data

        Returns:
            Formatted row string
        """
        pnl_str = f"{'+' if pos.pnl >= 0 else ''}{pos.pnl:,.2f}"
        pnl_pct_str = f"{'+' if pos.pnl_pct >= 0 else ''}{pos.pnl_pct:.1f}%"
        return (
            f"{pos.symbol:<10} {pos.name:<30} {pos.quantity:>10.2f} "
            f"{pos.market_value:>12,.2f} {pos.currency} {pnl_str:>13} {pnl_pct_str:>8}"
        )

    @staticmethod
    def _format_totals_row(
        total_value: float,
        total_pnl: float,
        total_pnl_pct: float,
        label: str,
        currency: str,
    ) -> str:
        """Format totals as a table row.

        Args:
            total_value: Total market value
            total_pnl: Total P&L
            total_pnl_pct: Total P&L percentage
            label: Row label
            currency: Currency code

        Returns:
            Formatted totals row
        """
        pnl_str = f"{'+' if total_pnl >= 0 else ''}{total_pnl:,.2f}"
        pnl_pct_str = f"{'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.1f}%"
        return f"{label:<51} {total_value:>13,.2f} {currency} {pnl_str:>13} {pnl_pct_str:>8}"

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format accounts as table with totals."""
        if not accounts:
            return "No accounts found."

        lines = []
        lines.append("\n" + "=" * 80)
        lines.append(f"{'Account':<40} {'Number':<20} {'Value':>18}")
        lines.append("-" * 80)

        total_value = 0.0
        for acc in accounts:
            lines.append(
                f"{acc.description:<40} {acc.number:<20} "
                f"{acc.value:>15,.2f} {acc.currency}"
            )
            total_value += acc.value

        lines.append("=" * 80)
        lines.append(f"{'Total':<61} {total_value:>15,.2f} CAD")
        lines.append("=" * 80)

        return "\n".join(lines)

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activities as table."""
        if not activities:
            return "No activities found."

        lines = []
        current_account = None

        for act in activities:
            # Print account header if account changes
            if act.account_label and act.account_label != current_account:
                if current_account is not None:
                    lines.append("=" * 80)
                lines.append("\n" + "=" * 80)
                lines.append(f"Account: {act.account_label}")
                lines.append("=" * 80)
                lines.append(
                    f"{'Date':<12} {'Type':<14} {'Description':<34} {'Amount':>18}"
                )
                lines.append("-" * 80)
                current_account = act.account_label
            elif current_account is None:
                # First activity, no account label
                lines.append("\n" + "=" * 80)
                lines.append(
                    f"{'Date':<12} {'Type':<14} {'Description':<34} {'Amount':>18}"
                )
                lines.append("-" * 80)
                current_account = ""

            lines.append(
                f"{act.date:<12} {act.activity_type:<14} {act.description:<34} "
                f"{act.sign}{act.amount:>14,.2f} {act.currency}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format positions as table with P&L."""
        if not positions:
            return "No positions found."

        lines = []

        # Header
        if group_label:
            lines.append("\n" + "=" * 94)
            lines.append(f"Account: {group_label}")
            lines.append("=" * 94)
        else:
            lines.append("\n" + "=" * 94)

        lines.append(
            f"{'Symbol':<10} {'Name':<30} {'Qty':>10} "
            f"{'Market Value':>16} {'P&L':>14} {'P&L %':>8}"
        )
        lines.append("-" * 94)

        # Position rows
        for pos in positions:
            lines.append(self._format_position_row(pos))

        # Totals
        if show_totals:
            total_value, total_book, total_pnl, total_pnl_pct = (
                _calculate_position_totals(positions)
            )
            label = "Account Total" if group_label else "Total"
            currency = positions[0].currency if positions else "CAD"

            lines.append("=" * 94)
            lines.append(
                self._format_totals_row(
                    total_value, total_pnl, total_pnl_pct, label, currency
                )
            )
            lines.append("=" * 94)

        return "\n".join(lines)


class JsonFormatter:
    """Format data as JSON."""

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format accounts as JSON array."""
        return json.dumps([asdict(acc) for acc in accounts], indent=2)

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activities as JSON array."""
        return json.dumps([asdict(act) for act in activities], indent=2)

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format positions as JSON with optional totals."""
        data = [asdict(pos) for pos in positions]

        if show_totals and positions:
            total_value = sum(p.market_value for p in positions)
            total_book = sum(p.book_value for p in positions)
            total_pnl = total_value - total_book
            total_pnl_pct = (total_pnl / total_book * 100) if total_book != 0 else 0.0

            result = {
                "positions": data,
                "totals": {
                    "market_value": total_value,
                    "book_value": total_book,
                    "pnl": total_pnl,
                    "pnl_pct": total_pnl_pct,
                    "currency": positions[0].currency if positions else "CAD",
                },
            }
            if group_label:
                result["group"] = group_label
            return json.dumps(result, indent=2)

        return json.dumps(data, indent=2)


class CsvFormatter:
    """Format data as CSV."""

    def format_accounts(self, accounts: Sequence[AccountData]) -> str:
        """Format accounts as CSV."""
        if not accounts:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["description", "number", "value", "currency"])

        # Write data
        for acc in accounts:
            writer.writerow([acc.description, acc.number, acc.value, acc.currency])

        return output.getvalue()

    def format_activities(self, activities: Sequence[ActivityData]) -> str:
        """Format activities as CSV."""
        if not activities:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "date",
                "activity_type",
                "description",
                "amount",
                "currency",
                "sign",
                "account_label",
            ]
        )

        # Write data
        for act in activities:
            writer.writerow(
                [
                    act.date,
                    act.activity_type,
                    act.description,
                    act.amount,
                    act.currency,
                    act.sign,
                    act.account_label or "",
                ]
            )

        return output.getvalue()

    def format_positions(
        self,
        positions: Sequence[PositionData],
        show_totals: bool = True,
        group_label: Optional[str] = None,
    ) -> str:
        """Format positions as CSV."""
        if not positions:
            return ""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "symbol",
                "name",
                "quantity",
                "market_value",
                "book_value",
                "currency",
                "pnl",
                "pnl_pct",
                "account_label",
            ]
        )

        # Write data
        for pos in positions:
            writer.writerow(
                [
                    pos.symbol,
                    pos.name,
                    pos.quantity,
                    pos.market_value,
                    pos.book_value,
                    pos.currency,
                    pos.pnl,
                    pos.pnl_pct,
                    pos.account_label or "",
                ]
            )

        # Optionally add totals row
        if show_totals and positions:
            total_value, total_book, total_pnl, total_pnl_pct = (
                _calculate_position_totals(positions)
            )
            currency = positions[0].currency if positions else "CAD"

            writer.writerow(
                [
                    "TOTAL",
                    "",
                    sum(p.quantity for p in positions),
                    total_value,
                    total_book,
                    currency,
                    total_pnl,
                    total_pnl_pct,
                    group_label or "",
                ]
            )

        return output.getvalue()


def get_formatter(format_type: str) -> FormatterProtocol:
    """Get formatter instance by type.

    Args:
        format_type: One of 'table', 'json', or 'csv'

    Returns:
        Formatter instance. Defaults to TableFormatter for unknown types.
    """
    formatters = {
        "table": TableFormatter(),
        "json": JsonFormatter(),
        "csv": CsvFormatter(),
    }
    return formatters.get(format_type.lower(), TableFormatter())
