import random
import unittest
from src import simulate
import pytest
from src import simulate
from unittest.mock import patch
import argparse
from types import SimpleNamespace


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
        result = simulate.simulate_spot_prices(market_data, num_hours)
        assert result == expected


def test_parse_time():
    assert simulate.parse_time("12:30:00") == 45000


def test_parse_cli():
    with patch("argparse.ArgumentParser"):
        simulate.parse_cli()

    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
        mock_parse_args.return_value = SimpleNamespace(fixed_rate=None, fixed_total=None)
        with pytest.raises(ValueError):
            simulate.parse_cli()


@pytest.mark.parametrize(
    "seed, fixed_rate, transfer_price, fixed_total, consumption_data, expected",
    [
        (
            1,
            None,
            0.05,
            1.23,
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
                "total_cost_variable_price": 0.126,
                "highest_variable_price": 1,
                "lowest_variable_price": 1,
                "average_peak_price": 1.0,
                "average_off_peak_price": 1.0,
                "total_cost_fixed_rate": 1.23,
                "savings_with_spot_price": 1.10,
            },
        )
    ],
)
def test_calculate_costs(seed, fixed_rate, transfer_price, fixed_total, consumption_data, expected):
    random.seed(seed)
    spot_prices = [1 for _ in range(24)]
    result = simulate.calculate_costs(
        consumption_data, spot_prices, fixed_rate, transfer_price, fixed_total
    )
    for k, v in expected.items():
        if isinstance(v, float):
            unittest.TestCase().assertAlmostEqual(result[k], v, places=2, msg=k)
        else:
            assert result[k] == v, k
