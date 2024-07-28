import calendar
from datetime import datetime
from datetime import time
from decimal import Decimal
from decimal import getcontext

import pytest

from saft.ratepayer_model import ElectricityPriceCalendar
from saft.ratepayer_model import ElectricityUsageAnalyzer
from saft.ratepayer_model import PricingPlan
from saft.ratepayer_model import TimeRange
from saft.ratepayer_model import UsagePattern
from saft.ratepayer_model import UsageSchedule
from saft.ratepayer_old_model import PreciseAmount


getcontext().prec = 8


def decimal_eq(a: Decimal, b: Decimal, tolerance: Decimal = Decimal("0.00001")) -> bool:
    return abs(a - b) <= tolerance


@pytest.fixture
def base_usage_schedule():
    usage_schedule = UsageSchedule()
    base_usage = UsagePattern(
        name="Base Usage",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        kwh=Decimal("1"),
    )
    usage_schedule.add_usage_pattern(pattern=base_usage)
    return usage_schedule


@pytest.fixture
def simple_price_calendar():
    # Note: Ordering matters and the first plan of the same plan_type will have priority for a time-slot
    price_calendar = ElectricityPriceCalendar()
    fixed_monthly_plan = PricingPlan(
        name="Fixed Monthly Cost",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        price=PreciseAmount(amount=Decimal("39.90")),
        plan_type="fixed_monthly",
        is_fixed_monthly=True,
    )
    daily_rate_plan = PricingPlan(
        name="Daily Rate",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        price=PreciseAmount(amount=Decimal("0.10")),
        plan_type="daily_rate",
    )
    price_calendar.add_pricing_plan(plan=fixed_monthly_plan)
    price_calendar.add_pricing_plan(plan=daily_rate_plan)
    return price_calendar


@pytest.fixture
def sophisticated_price_calendar():
    price_calendar = ElectricityPriceCalendar()
    winter_daytime = PricingPlan(
        name="Winter Daytime",
        start_date=datetime(2023, 1, 1, 0, 0, 0),
        end_date=datetime(2023, 12, 31),
        time_range=TimeRange(start=time(7), end=time(21)),
        days_of_week=[0, 1, 2, 3, 4],  # Monday to Friday
        months=[11, 12, 1, 2, 3],  # November to March
        price=PreciseAmount(amount=Decimal("0.15")),
        plan_type="distribution",
        tax_multiplier=PreciseAmount(amount=Decimal("1.24")),
    )
    other_time = PricingPlan(
        name="Other Time",
        start_date=datetime(2023, 1, 1, 0, 0, 0),
        end_date=datetime(2023, 12, 31),
        price=PreciseAmount(amount=Decimal("0.10")),
        plan_type="distribution",
        tax_multiplier=PreciseAmount(amount=Decimal("1.24")),
    )
    supplier_plan = PricingPlan(
        name="Fixed Supplier Rate",
        start_date=datetime(2023, 1, 1, 0, 0, 0),
        end_date=datetime(2023, 12, 31),
        price=PreciseAmount(amount=Decimal("0.08")),
        plan_type="supply",
        tax_multiplier=PreciseAmount(amount=Decimal("1.24")),
    )
    price_calendar.add_pricing_plan(plan=winter_daytime)
    price_calendar.add_pricing_plan(plan=other_time)
    price_calendar.add_pricing_plan(plan=supplier_plan)
    return price_calendar


def test_simple_pricing(base_usage_schedule, simple_price_calendar):
    analyzer = ElectricityUsageAnalyzer(simple_price_calendar, base_usage_schedule)
    start_date = datetime(2023, 1, 1, 0, 0, 0)
    end_date = datetime(2023, 2, 1, 0, 0, 0)
    analysis = analyzer.analyze_period(start_date, end_date)
    summary = analyzer.summarize_analysis(analysis)

    expected_fixed_monthly = Decimal("39.90") * Decimal("1.24")
    expected_daily_rate = Decimal("0.10") * Decimal("1") * 24 * 31 * Decimal("1.24")
    expected_total_cost = expected_fixed_monthly + expected_daily_rate

    assert decimal_eq(summary["cost_by_type"]["fixed_monthly"], expected_fixed_monthly)
    assert decimal_eq(summary["cost_by_type"]["daily_rate"], expected_daily_rate)
    assert decimal_eq(summary["total_cost"].amount, expected_total_cost)


from datetime import timedelta


def test_sophisticated_pricing(base_usage_schedule, sophisticated_price_calendar):
    analyzer = ElectricityUsageAnalyzer(sophisticated_price_calendar, base_usage_schedule)
    start_date = datetime(2023, 1, 1, 0, 0, 0)
    end_date = datetime(2023, 2, 1, 0, 0, 0)
    analysis = analyzer.analyze_period(start_date, end_date)
    summary = analyzer.summarize_analysis(analysis)

    _, days_in_january = calendar.monthrange(2023, 1)
    total_hours = days_in_january * 24

    expected_distribution_cost = Decimal("0")
    winter_daytime_hours = 0
    other_hours = 0

    for hour in range(total_hours):
        current_date = start_date + timedelta(hours=hour)
        is_weekday = current_date.weekday() < 5
        is_daytime = 7 <= current_date.hour < 21
        is_winter_month = current_date.month in [11, 12, 1, 2, 3]

        if is_weekday and is_daytime and is_winter_month:
            expected_distribution_cost += Decimal("0.15") * Decimal("1.24")
            winter_daytime_hours += 1
        else:
            expected_distribution_cost += Decimal("0.10") * Decimal("1.24")
            other_hours += 1

    expected_supply_cost = Decimal("0.08") * total_hours * Decimal("1.24")
    expected_total_cost = expected_distribution_cost + expected_supply_cost

    # Compare hourly costs
    for i, hour_data in enumerate(analysis):
        current_date = start_date + timedelta(hours=i)
        is_weekday = current_date.weekday() < 5
        is_daytime = 7 <= current_date.hour < 21
        is_winter_month = current_date.month in [11, 12, 1, 2, 3]

        if is_weekday and is_daytime and is_winter_month:
            expected_distribution = Decimal("0.15") * Decimal("1.24")
            expected_rate = "Winter Daytime"
        else:
            expected_distribution = Decimal("0.10") * Decimal("1.24")
            expected_rate = "Other"

        actual_distribution = hour_data["cost"]["distribution"]
        actual_rate = "Winter Daytime" if actual_distribution == Decimal("0.1860") else "Other"

        if i < 48 or not decimal_eq(actual_distribution, expected_distribution):
            print(
                f"Hour {i} ({current_date}): Actual {actual_distribution} ({actual_rate}), Expected {expected_distribution} ({expected_rate})"
            )

    assert decimal_eq(summary["cost_by_type"]["distribution"], expected_distribution_cost)
    assert decimal_eq(summary["cost_by_type"]["supply"], expected_supply_cost)
    assert decimal_eq(summary["total_cost"].amount, expected_total_cost)

    # Additional checks
    assert summary["peak_usage_hour"] is not None
    assert summary["peak_cost_hour"] is not None
    assert Decimal("0") < summary["average_price_per_kwh"].amount < Decimal("1")
