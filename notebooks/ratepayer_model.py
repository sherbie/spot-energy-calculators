from datetime import datetime
from datetime import time
from decimal import Decimal
from typing import Dict
from typing import List
from typing import Optional

from ratepayer_old_model import PreciseAmount


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
        months: Optional[List[int]] = None
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
    """Represents a distribution of costs as properties that apply to hourly time slots over a date range"""

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
        months: Optional[List[int]] = None
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


class ElectricityPriceCalendar:
    def __init__(self):
        self.pricing_plans: Dict[str, List[PricingPlan]] = {}

    def add_pricing_plan(self, *, plan: PricingPlan) -> None:
        if plan.plan_type not in self.pricing_plans:
            self.pricing_plans[plan.plan_type] = []
        self.pricing_plans[plan.plan_type].append(plan)

    def get_price(self, *, timestamp: datetime) -> Dict[str, Dict[str, Decimal]]:
        prices_without_tax = {}
        prices_with_tax = {}

        for plan_type, plans in self.pricing_plans.items():
            for plan in reversed(plans):
                if self._plan_applies(plan=plan, timestamp=timestamp):
                    if plan_type not in prices_without_tax:
                        prices_without_tax[plan_type] = plan.price.amount
                        prices_with_tax[plan_type] = plan.price.amount * plan.tax_multiplier.amount
                    break  # Use the first applicable plan for each type

        total_without_tax = sum(prices_without_tax.values())
        total_with_tax = sum(prices_with_tax.values())

        prices_without_tax["total"] = total_without_tax
        prices_with_tax["total"] = total_with_tax

        return {"without_tax": prices_without_tax, "with_tax": prices_with_tax}

    def _plan_applies(self, *, plan: PricingPlan, timestamp: datetime) -> bool:
        if not (plan.start_date <= timestamp <= plan.end_date):
            return False

        if plan.months and timestamp.month not in plan.months:
            return False

        if plan.days_of_week and timestamp.weekday() not in plan.days_of_week:
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
