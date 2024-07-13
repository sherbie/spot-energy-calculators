# the ratepayer domain model

import datetime
import uuid
from datetime import datetime
from datetime import time
from decimal import Decimal
from decimal import getcontext
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

import moneyed
import pandas as pd
import pytz
from moneyed import EUR
from moneyed import Money
from pydantic import BaseModel as PydanticBaseModel


getcontext().prec = 6


class BaseModel(PydanticBaseModel):
    id: uuid.UUID = uuid.uuid4()

    class Config:
        arbitrary_types_allowed = True


class GridNetworkType(Enum):
    TN_C_S = "TN-C-S (PEN)"
    TN_S = "TN-S"
    TT = "TT"
    IT = "IT"


class DayType(Enum):
    WORKDAY = "workday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimeOfUse(Enum):
    WINTER_DAY = "winter_day"
    OTHER_TIME = "other_time"


class PricingPeriod(BaseModel):
    start_time: time
    end_time: time
    day_types: List[DayType]
    time_of_use: TimeOfUse


class SeasonalPricing(BaseModel):
    start_date: datetime
    end_date: datetime
    pricing_periods: List[PricingPeriod]
    prices: Dict[TimeOfUse, Money]


class ConnectionType(BaseModel):
    display_name: str
    breaker_size_amps: int
    fixed_cost: Money


class Distributor(BaseModel):
    display_name: str
    contract_name: str
    connection_type: ConnectionType
    seasonal_pricing: List[SeasonalPricing]
    grid_network_type: GridNetworkType


class PreciseAmount(BaseModel):
    id: uuid.UUID = uuid.uuid4()
    amount: Decimal
    currency: moneyed.Currency = EUR

    def __str__(self):
        return f"{self.amount:.5f} {self.currency}"

    def to_money(self):
        return Money(amount=self.amount.quantize(Decimal("0.00001")), currency=self.currency)

    def __mul__(self, other):
        if isinstance(other, (int, float, Decimal)):
            return PreciseAmount(amount=self.amount * Decimal(str(other)), currency=self.currency)
        raise TypeError(
            f"unsupported operand type(s) for *: 'PreciseAmount' and '{type(other).__name__}'"
        )

    def __rmul__(self, other):
        return self.__mul__(other)

    def __sub__(self, other):
        if isinstance(other, PreciseAmount):
            if self.currency != other.currency:
                raise ValueError("Cannot subtract amounts with different currencies")
            return PreciseAmount(amount=self.amount - other.amount, currency=self.currency)
        raise TypeError(
            f"unsupported operand type(s) for -: 'PreciseAmount' and '{type(other).__name__}'"
        )

    def __truediv__(self, other):
        if isinstance(other, (int, float, Decimal)):
            return PreciseAmount(amount=self.amount / Decimal(str(other)), currency=self.currency)
        raise TypeError(
            f"unsupported operand type(s) for /: 'PreciseAmount' and '{type(other).__name__}'"
        )


class DayAheadPricing(BaseModel):
    country_code: str
    zone_code: Optional[str]
    prices: pd.DataFrame
    last_updated: datetime = datetime.now(pytz.UTC)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_csv(cls, file_path: str, country_code: str, zone_code: Optional[str] = None):
        df = pd.read_csv(file_path, parse_dates=["Timestamp"], index_col="Timestamp")
        df["Price"] = df["Price"].apply(lambda x: PreciseAmount(amount=Decimal(str(x)) / 1000))
        return cls(country_code=country_code, zone_code=zone_code, prices=df)

    def get_price(self, dt: datetime) -> PreciseAmount:
        try:
            return self.prices.loc[dt, "Price"]
        except KeyError:
            raise ValueError(f"No price available for {dt}")

    def update_prices(self, new_prices: pd.DataFrame):
        new_prices["Price"] = new_prices["Price"].apply(
            lambda x: PreciseAmount(amount=Decimal(str(x)) / 1000)
        )
        self.prices = pd.concat([self.prices, new_prices]).sort_index().drop_duplicates()
        self.last_updated = datetime.now(pytz.UTC)


class Supplier(BaseModel):
    display_name: str
    contract_name: str
    day_ahead_pricing: DayAheadPricing
    fixed_cost: Money


class Rate(BaseModel):
    display_name: str
    distributor: Distributor
    supplier: Supplier
    vat_rate: Decimal


class PriceBreakdown(BaseModel):
    energy_cost: PreciseAmount
    supplier_fixed_cost: PreciseAmount
    distribution_cost: PreciseAmount
    distribution_fixed_cost: PreciseAmount
    total_energy_cost: PreciseAmount
    total_distribution_cost: PreciseAmount
    total_without_tax: PreciseAmount
    total_with_tax: PreciseAmount
    total_usage: Decimal
