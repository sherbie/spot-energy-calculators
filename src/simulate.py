import json
import random
import argparse


def is_peak(hour):
    return 6 <= (hour % 24) <= 9 or 17 <= (hour % 24) <= 20


def simulate_spot_prices_by_hour(market_data, num_hours=8760):
    hourly_spot_prices = []
    for hour in range(num_hours):
        month = (hour // 730) % 12 + 1  # Rough estimation of month based on hour
        month_data = [m for m in market_data if m["month"] == month][0]
        if is_peak(hour):
            hourly_spot_prices.append(
                random.uniform(month_data["peak"]["min"], month_data["peak"]["max"])
            )
        else:
            hourly_spot_prices.append(
                random.uniform(month_data["off-peak"]["min"], month_data["off-peak"]["max"])
            )
    return hourly_spot_prices


def load_data(filename):
    with open(filename, "r") as file:
        return json.load(file)


def parse_time(time_str):
    h, m, s = map(int, time_str.split(":"))
    return h * 3600 + m * 60 + s


def get_variable_prices_of_day(
    month_of_year, day_of_month, hourly_spot_prices, transfer_price, cpo
):
    kw_draw = cpo["kw_draw"]
    start = parse_time(cpo["start_time"])
    stop = parse_time(cpo["stop_time"])
    peak_prices = []
    off_peak_prices = []
    total_variable_cost = 0.0

    for hour in range(24):
        hour_idx = (month_of_year - 1) * 730 + day_of_month * 24 + hour
        if hour_idx >= len(hourly_spot_prices):
            break
        current_hour = start // 3600 + hour
        if (
            start <= current_hour < stop
            or stop < start
            and (current_hour < stop or current_hour >= start)
        ):
            spot_price = hourly_spot_prices[hour_idx]
            if is_peak(current_hour):
                peak_prices.append(spot_price)
            else:
                off_peak_prices.append(spot_price)
            total_variable_cost += (spot_price + transfer_price) * kw_draw

    return total_variable_cost, peak_prices, off_peak_prices


def calculate_costs(consumption_data, hourly_spot_prices, transfer_price, fixed_total):
    total_variable_cost = 0.0
    peak_prices = []
    off_peak_prices = []

    for co in consumption_data:
        for cpo in co["consumption_periods"]:
            months = cpo["months"]
            for month in months:
                for day in range(30):  # Approximation: 30 days per month
                    total, _peak_prices, _off_peak_prices = get_variable_prices_of_day(
                        month, day, hourly_spot_prices, transfer_price, cpo
                    )
                    total_variable_cost += total
                    peak_prices.extend(_peak_prices)
                    off_peak_prices.extend(_off_peak_prices)

    highest_variable_price = max(hourly_spot_prices)
    lowest_variable_price = min(hourly_spot_prices)
    average_peak_price = sum(peak_prices) / len(peak_prices) if peak_prices else 0
    average_off_peak_price = sum(off_peak_prices) / len(off_peak_prices) if off_peak_prices else 0
    total_variable_cost_euros = total_variable_cost / 100

    return {
        "total_cost_variable_price": total_variable_cost_euros,
        "highest_variable_price": highest_variable_price,
        "lowest_variable_price": lowest_variable_price,
        "average_peak_price": average_peak_price,
        "average_off_peak_price": average_off_peak_price,
        "total_cost_fixed_rate": fixed_total,
        "savings_with_spot_price": fixed_total - total_variable_cost_euros,
    }


def parse_cli():
    parser = argparse.ArgumentParser(description="Simulate annual electricity cost.")
    parser.add_argument("--seed", type=int, required=True, help="Seed for RNG")
    parser.add_argument(
        "--fixed_total", type=float, required=False, help="Fixed annual total in euros"
    )
    parser.add_argument(
        "--transfer_price",
        type=float,
        required=True,
        help="Base transfer price in euro cents per kwh",
    )
    parser.add_argument(
        "--consumption_file", type=str, required=True, help="JSON file with consumption data"
    )
    parser.add_argument(
        "--market-file", type=str, required=True, help="JSON file with spot market data"
    )

    args = parser.parse_args()

    if not args.fixed_rate and not args.fixed_total:
        raise ValueError("Either fixed_rate or fixed_total must be provided")

    return args


def main(
    seed: int,
    transfer_price: float,
    consumption_file: str,
    market_file: str,
    fixed_total: float = None,
):
    random.seed(seed)
    market_data = load_data(market_file)
    hourly_spot_prices = simulate_spot_prices_by_hour(market_data)
    consumption_data = load_data(consumption_file)

    result = calculate_costs(
        consumption_data=consumption_data,
        hourly_spot_prices=hourly_spot_prices,
        transfer_price=transfer_price,
        fixed_total=fixed_total,
    )
    print(json.dumps(result, indent=4))
    return result


if __name__ == "__main__":
    args = parse_cli()
    main(
        seed=args.seed,
        fixed_total=args.fixed_total,
        transfer_price=args.transfer_price,
        consumption_file=args.consumption_file,
        market_file=args.market_file,
    )
