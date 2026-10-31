import datetime as dt
import pytest
from etal.dates import PartialDate

@pytest.mark.parametrize("raw,expected", [
    ("2024-01-05", "2024-01-05"), ("2026-07", "2026-07"), ("2016", "2016"),
    (2016, "2016"), (dt.date(2024, 1, 5), "2024-01-05"),
    (dt.datetime(2024, 1, 5, 10, 0), "2024-01-05"),
])
def test_parse_and_str(raw, expected):
    assert str(PartialDate.parse(raw)) == expected

def test_precision_and_day_recorded():
    assert PartialDate.parse("2026-07").precision == "month"
    assert PartialDate.parse("2026-07").day_recorded is False
    assert PartialDate.parse("2026-07-12").day_recorded is True

def test_month_only_sorts_before_days_in_month():
    assert PartialDate.parse("2026-07") < PartialDate.parse("2026-07-01")

def test_first_and_last_day():
    assert PartialDate.parse("2026-07").first_day() == dt.date(2026, 7, 1)
    assert PartialDate.parse("2026-07").last_day() == dt.date(2026, 7, 31)
    assert PartialDate.parse("2016").last_day() == dt.date(2016, 12, 31)

@pytest.mark.parametrize("bad", ["July 2026", "2026-13", "", None, 3.5])
def test_rejects(bad):
    with pytest.raises(ValueError):
        PartialDate.parse(bad)
