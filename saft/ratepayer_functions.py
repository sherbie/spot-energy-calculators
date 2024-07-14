# the ratepayer domain model

import datetime
from datetime import date
from datetime import datetime
from decimal import Decimal

import pandas as pd
from ratepayer_old_model import *


def get_day_type(date: datetime) -> DayType:
    weekday = date.weekday()
    if weekday < 5:  # Monday to Friday
        return DayType.WORKDAY
    elif weekday == 5:  # Saturday
        return DayType.SATURDAY
    else:  # Sunday
        return DayType.SUNDAY


def get_distribution_price(distributor: Distributor, dt: datetime) -> PreciseAmount:
    for season in distributor.seasonal_pricing:
        if season.start_date <= dt <= season.end_date:
            for period in season.pricing_periods:
                if (
                    period.start_time <= dt.time() <= period.end_time
                    and get_day_type(dt) in period.day_types
                ):
                    return season.prices[period.time_of_use]

    # If no specific period is found, return the OTHER_TIME price
    return distributor.seasonal_pricing[0].prices[TimeOfUse.OTHER_TIME]


def calculate_total_cost(
    rate: Rate, start_date: datetime, end_date: datetime, hourly_usage: Decimal
) -> PriceBreakdown:
    energy_cost = PreciseAmount(amount=Decimal("0"))
    distribution_cost = PreciseAmount(amount=Decimal("0"))

    date_range = pd.date_range(start=start_date, end=end_date, freq="h", tz="Europe/Helsinki")

    for dt in date_range:
        try:
            energy_price = rate.supplier.day_ahead_pricing.get_price(dt)
            distribution_price = get_distribution_price(rate.distributor, dt)

            energy_cost.amount += energy_price.amount * hourly_usage
            distribution_cost.amount += distribution_price.amount * hourly_usage
        except ValueError:
            print(f"Warning: Price not available for {dt}")

    supplier_fixed_cost = rate.supplier.fixed_cost.amount
    distributor_fixed_cost = rate.distributor.connection_type.fixed_cost.amount

    total_energy_cost = energy_cost.amount + supplier_fixed_cost
    total_distribution_cost = distribution_cost.amount + distributor_fixed_cost

    total_without_tax = total_energy_cost + total_distribution_cost
    total_with_tax = total_without_tax * (1 + rate.vat_rate)

    return PriceBreakdown(
        energy_cost=PreciseAmount(amount=energy_cost.amount),
        supplier_fixed_cost=PreciseAmount(amount=supplier_fixed_cost),
        distribution_cost=PreciseAmount(amount=distribution_cost.amount),
        distribution_fixed_cost=PreciseAmount(amount=distributor_fixed_cost),
        total_energy_cost=PreciseAmount(amount=total_energy_cost),
        total_distribution_cost=PreciseAmount(amount=total_distribution_cost),
        total_without_tax=PreciseAmount(amount=total_without_tax),
        total_with_tax=PreciseAmount(amount=total_with_tax),
        total_usage=hourly_usage * len(date_range),
    )
