import random
import unittest
from src import simulate
import pytest
from src import simulate
from unittest.mock import patch
from types import SimpleNamespace


@pytest.mark.parametrize(
    "hour, expected", [(0, False), (6, True), (9, True), (17, True), (20, True), (23, False)]
)
def test_is_peak(hour, expected):
    assert simulate.is_peak(hour) == expected


def test_constant_seed_constant_output():
    result1 = simulate.main(
        consumption_file="test/energy_model_test.json",
        market_file="test/market_model_test.json",
        seed=1,
        fixed_total=675.56,
        transfer_price=0.5,
    )
    result2 = simulate.main(
        consumption_file="test/energy_model_test.json",
        market_file="test/market_model_test.json",
        seed=1,
        fixed_total=675.56,
        transfer_price=0.5,
    )

    assert result1 == result2


@pytest.mark.parametrize(
    "market_data, num_hours, expected",
    [
        (
            [{"month": 1, "peak": {"min": 1, "max": 2}, "off-peak": {"min": 0, "max": 1}}],
            24,
            [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 1, 1, 1],
        ),
    ],
)
def test_simulate_spot_prices(market_data, num_hours, expected):

    def mock_random_uniform(min_value, max_value):
        return min_value + max_value

    with patch("random.uniform", mock_random_uniform):
        result = simulate.simulate_spot_prices_by_hour(market_data, num_hours)
        assert result == expected


def test_parse_time():
    assert simulate.parse_time("12:30:00") == 45000


def test_parse_cli():
    with patch("argparse.ArgumentParser"):
        simulate.parse_cli()


@pytest.mark.parametrize(
    "month_of_year, day_of_month, hourly_spot_prices, transfer_price, cpo, exp_total_variable_cost, exp_peak_prices, exp_off_peak_prices",
    [
        (
            1,
            0,
            [],
            1,
            {"start_time": "00:00:00", "stop_time": "01:00:0", "kw_draw": 1.0},
            0,
            [],
            [],
        ),
        (
            1,
            0,
            [1, 2, 3],
            1,
            {"start_time": "00:00:00", "stop_time": "01:00:0", "kw_draw": 1.0},
            9.0,
            [],
            [1, 2, 3],
        ),
        (
            1,
            0,
            [0, 0, 0, 0, 0, 0, 1, 2, 3],
            1,
            {"start_time": "00:00:00", "stop_time": "01:00:0", "kw_draw": 1.0},
            15.0,
            [1, 2, 3],
            [0, 0, 0, 0, 0, 0],
        ),
    ],
)
def test_get_variable_prices_of_day(
    month_of_year,
    day_of_month,
    hourly_spot_prices,
    transfer_price,
    cpo,
    exp_total_variable_cost,
    exp_peak_prices,
    exp_off_peak_prices,
):
    total_variable_cost, peak_prices, off_peak_prices = simulate.get_variable_prices_of_day(
        month_of_year, day_of_month, hourly_spot_prices, transfer_price, cpo
    )
    assert (total_variable_cost, peak_prices, off_peak_prices) == (
        exp_total_variable_cost,
        exp_peak_prices,
        exp_off_peak_prices,
    )


@pytest.mark.parametrize(
    "seed, transfer_price, fixed_total, consumption_data, expected",
    [
        (
            1,
            0.05,
            12.1,
            [
                {
                    "consumption_periods": [
                        {
                            "start_time": "00:00:00",
                            "stop_time": "01:00:0",
                            "kw_draw": 0.5,
                            "months": [1],
                        }
                    ]
                }
            ],
            {
                "total_cost_variable_price": 12.0,
                "highest_variable_price": 0.95,
                "lowest_variable_price": 0.95,
                "average_peak_price": 0.95,
                "average_off_peak_price": 0.95,
                "total_cost_fixed_rate": 12.1,
                "savings_with_spot_price": 0.10,
            },
        )
    ],
)
def test_calculate_costs(seed, transfer_price, fixed_total, consumption_data, expected):
    random.seed(seed)
    hourly_spot_prices = [0.95 for _ in range(24)]
    result = simulate.calculate_costs(
        consumption_data, hourly_spot_prices, transfer_price, fixed_total
    )
    for k, v in expected.items():
        if isinstance(v, float):
            unittest.TestCase().assertAlmostEqual(result[k], v, places=2, msg=k)
        else:
            assert result[k] == v, k
