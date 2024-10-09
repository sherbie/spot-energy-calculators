import datetime

import pytest

from saft.ratepayer_functions import get_day_type
from saft.ratepayer_old_model import DayType


@pytest.mark.parametrize(
    "date, expected",
    [
        (datetime.datetime(2024, 7, 20), DayType.SATURDAY),
        (datetime.datetime(2024, 7, 21), DayType.SUNDAY),
        (datetime.datetime(2024, 7, 22), DayType.WORKDAY),
    ],
)
def test_get_day_type(date: datetime, expected: DayType):
    assert get_day_type(date) == expected
