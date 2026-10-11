"""Date helper that anchors the seed story to the calendar.

The story starts on the 1st of the month two months before ``today`` and runs
forward. Events are addressed as ``(month_offset, day_of_month)``, so the same
story shifts with the calendar. Dates that would fall after ``today`` are
clamped to ``today`` so the seed never produces future transactions.
"""

from __future__ import annotations

import calendar
from datetime import date


def anchor_for(today: date) -> date:
    """Returns the first day of the month two months before ``today``."""
    month_index = today.year * 12 + (today.month - 1) - 2
    return date(month_index // 12, month_index % 12 + 1, 1)


class Timeline:
    """Resolves story dates relative to an anchor, never beyond ``today``."""

    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()
        self.anchor = anchor_for(self.today)

    def on(self, month: int, day: int) -> date:
        """Date ``day`` of the month ``month`` months after the anchor month.

        Days past the end of the month are clamped to the month's last day,
        and the result is clamped to ``today``.
        """
        month_index = self.anchor.year * 12 + (self.anchor.month - 1) + month
        year, mon = month_index // 12, month_index % 12 + 1
        last_day = calendar.monthrange(year, mon)[1]
        return min(date(year, mon, min(day, last_day)), self.today)

    def next_day_of_month(self, day: int) -> date:
        """Next upcoming occurrence of ``day`` (strictly after today); for due dates."""
        year, mon = self.today.year, self.today.month
        candidate = date(year, mon, min(day, calendar.monthrange(year, mon)[1]))
        if candidate <= self.today:
            mon += 1
            if mon == 13:
                year, mon = year + 1, 1
            candidate = date(year, mon, min(day, calendar.monthrange(year, mon)[1]))
        return candidate
