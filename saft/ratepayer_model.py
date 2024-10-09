import logging
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from typing import Dict
from typing import List
from typing import Optional

from saft.ratepayer_old_model import PreciseAmount


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class TimeRange:
    def __init__(self, *, start: time, end: time):
        self.start: time = start
        self.end: time = end


class UsagePattern:
    """Represents the offtaker's behavior as usage in KWh accross time-slots over a period"""

    def __init__(
        self,
        *,
        name: str,
        start_date: datetime,
        end_date: datetime,
        kwh: Decimal,
        time_range: Optional[TimeRange] = None,
        days_of_week: Optional[List[int]] = None,
        months: Optional[List[int]] = None,
    ):
        self.name: str = name
        self.start_date: datetime = start_date
        self.end_date: datetime = end_date
        self.time_range: Optional[TimeRange] = time_range
        self.days_of_week: Optional[List[int]] = days_of_week  # 0 = Monday, 6 = Sunday
        self.months: Optional[List[int]] = months
        self.kwh: Decimal = kwh


class UsageSchedule:
    def __init__(self):
        self.usage_patterns: List[UsagePattern] = []

    def add_usage_pattern(self, *, pattern: UsagePattern) -> None:
        self.usage_patterns.append(pattern)

    def get_usage(self, *, timestamp: datetime) -> Decimal:
        total_kwh = Decimal("0.0")

        for pattern in reversed(self.usage_patterns):
            if self._pattern_applies(pattern=pattern, timestamp=timestamp):
                total_kwh += pattern.kwh

        return total_kwh

    def _pattern_applies(self, *, pattern: UsagePattern, timestamp: datetime) -> bool:
        if not (pattern.start_date <= timestamp <= pattern.end_date):
            return False

        if pattern.months and timestamp.month not in pattern.months:
            return False

        if pattern.days_of_week and timestamp.weekday() not in pattern.days_of_week:
            return False

        if pattern.time_range:
            current_time = timestamp.time()
            if pattern.time_range.start <= pattern.time_range.end:
                if not (pattern.time_range.start <= current_time < pattern.time_range.end):
                    return False
            else:  # Handles ranges that cross midnight
                if not (
                    current_time >= pattern.time_range.start
                    or current_time < pattern.time_range.end
                ):
                    return False

        return True


class PricingPlan:
    """Represents a distribution of costs as properties that apply to hourly time slots over a date range

    If multiple variants of the same `plan_type` are used, the first one added will take priority!
    I.e. add a time-of-day plan before adding the other-time default plan
    """

    def __init__(
        self,
        *,
        name: str,
        start_date: datetime,
        end_date: datetime,
        price: PreciseAmount,
        plan_type: str,
        tax_multiplier: PreciseAmount = PreciseAmount(amount=Decimal("1.24")),
        time_range: Optional[TimeRange] = None,
        days_of_week: Optional[List[int]] = None,
        months: Optional[List[int]] = None,
        is_fixed_monthly: bool = False,
    ):
        self.name: str = name
        self.start_date: datetime = start_date
        self.end_date: datetime = end_date
        self.time_range: Optional[TimeRange] = time_range
        self.days_of_week: Optional[List[int]] = days_of_week  # 0 = Monday, 6 = Sunday
        self.months: Optional[List[int]] = months
        self.price: PreciseAmount = price
        self.plan_type: str = plan_type
        self.tax_multiplier: PreciseAmount = tax_multiplier
        self.is_fixed_monthly: bool = is_fixed_monthly


class ElectricityPriceCalendar:
    def __init__(self):
        self.pricing_plans: Dict[str, List[PricingPlan]] = {}
        self.last_fixed_charge_date: Dict[str, datetime] = {}

    def add_pricing_plan(self, *, plan: PricingPlan) -> None:
        if plan.plan_type not in self.pricing_plans:
            self.pricing_plans[plan.plan_type] = []
        self.pricing_plans[plan.plan_type].append(plan)

    def get_price(self, *, timestamp: datetime) -> Dict[str, Dict[str, Decimal]]:
        prices_without_tax = {}
        prices_with_tax = {}

        for plan_type, plans in self.pricing_plans.items():
            for plan in plans:
                if self._plan_applies(plan=plan, timestamp=timestamp):
                    if plan.is_fixed_monthly:
                        fixed_charge = self._get_fixed_monthly_charge(plan, timestamp)
                        prices_without_tax[plan_type] = fixed_charge
                        prices_with_tax[plan_type] = fixed_charge * plan.tax_multiplier.amount
                    else:
                        prices_without_tax[plan_type] = plan.price.amount
                        prices_with_tax[plan_type] = plan.price.amount * plan.tax_multiplier.amount
                    break  # Use the first applicable plan for each plan_type

        total_without_tax = sum(prices_without_tax.values())
        total_with_tax = sum(prices_with_tax.values())

        prices_without_tax["total"] = total_without_tax
        prices_with_tax["total"] = total_with_tax

        return {"without_tax": prices_without_tax, "with_tax": prices_with_tax}

    def _get_fixed_monthly_charge(self, plan: PricingPlan, timestamp: datetime) -> Decimal:
        if (
            plan.plan_type not in self.last_fixed_charge_date
            or self.last_fixed_charge_date[plan.plan_type].month != timestamp.month
        ):
            self.last_fixed_charge_date[plan.plan_type] = timestamp
            return plan.price.amount
        return Decimal("0")

    def _plan_applies(self, *, plan: PricingPlan, timestamp: datetime) -> bool:
        if not (plan.start_date <= timestamp <= plan.end_date):
            return False

        if plan.months and timestamp.month not in plan.months:
            return False

        if plan.days_of_week is not None and timestamp.weekday() not in plan.days_of_week:
            return False

        if plan.time_range:
            current_time = timestamp.time()
            if plan.time_range.start <= plan.time_range.end:
                if not (plan.time_range.start <= current_time < plan.time_range.end):
                    return False
            else:  # Handles ranges that cross midnight
                if not (
                    current_time >= plan.time_range.start or current_time < plan.time_range.end
                ):
                    return False

        return True


class ElectricityUsageAnalyzer:
    def __init__(self, price_calendar: ElectricityPriceCalendar, usage_schedule: UsageSchedule):
        self.price_calendar = price_calendar
        self.usage_schedule = usage_schedule

    def analyze_period(self, start: datetime, end: datetime) -> List[Dict]:
        current = start
        results = []

        log.debug(f"Starting analysis from {start} to {end}")

        while current < end:
            usage = self.usage_schedule.get_usage(timestamp=current)
            prices = self.price_calendar.get_price(timestamp=current)

            # log.debug(f"Analyzing {current}: usage={usage}, prices={prices}")

            hour_data = {
                "timestamp": current,
                "usage_kwh": usage,
                "prices": prices["with_tax"],
                "cost": {k: v * usage for k, v in prices["with_tax"].items()},
            }

            results.append(hour_data)
            current += timedelta(hours=1)

        log.debug(f"Analysis completed, {len(results)} hours analyzed")

        return results

    def summarize_analysis(self, analysis: List[Dict]) -> Dict:
        summary = {
            "total_usage_kwh": Decimal("0"),
            "total_cost": PreciseAmount(amount=Decimal("0")),
            "cost_by_type": {},
            "average_price_per_kwh": PreciseAmount(amount=Decimal("0")),
            "peak_usage_hour": None,
            "peak_cost_hour": None,
        }

        log.debug(f"Summarizing {len(analysis)} hours of data")

        for hour_data in analysis:
            summary["total_usage_kwh"] += hour_data["usage_kwh"]
            summary["total_cost"].amount += hour_data["cost"]["total"]

            for cost_type, cost in hour_data["cost"].items():
                if cost_type != "total":
                    summary["cost_by_type"][cost_type] = (
                        summary["cost_by_type"].get(cost_type, Decimal("0")) + cost
                    )

            if (
                summary["peak_usage_hour"] is None
                or hour_data["usage_kwh"] > analysis[summary["peak_usage_hour"]]["usage_kwh"]
            ):
                summary["peak_usage_hour"] = analysis.index(hour_data)

            if (
                summary["peak_cost_hour"] is None
                or hour_data["cost"]["total"] > analysis[summary["peak_cost_hour"]]["cost"]["total"]
            ):
                summary["peak_cost_hour"] = analysis.index(hour_data)

        if summary["total_usage_kwh"] > 0:
            summary["average_price_per_kwh"] = PreciseAmount(
                amount=(summary["total_cost"].amount / summary["total_usage_kwh"])
            )

        log.debug(f"Summary completed. Total usage: {summary['total_usage_kwh']} kWh")
        log.debug(f"Total cost: {summary['total_cost'].amount}")
        log.debug(f"Cost by type: {summary['cost_by_type']}")

        return summary
