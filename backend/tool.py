from langchain_core.tools import tool


@tool
def calculate_return(
    start_price: float,
    end_price: float,
) -> float:
    """
    Calculate the percentage return between a starting
    stock price and an ending stock price.
    """

    if start_price == 0:
        raise ValueError("Starting price cannot be zero.")

    return ((end_price - start_price) / start_price) * 100


@tool
def calculate_volatility(
    prices: list[float],
) -> float:
    """
    Calculate the standard deviation of percentage
    price changes in a series of stock prices.
    """

    if len(prices) < 2:
        raise ValueError(
            "At least two prices are required to calculate volatility."
        )

    returns = []

    for i in range(1, len(prices)):
        previous_price = prices[i - 1]
        current_price = prices[i]

        if previous_price == 0:
            continue

        daily_return = (
            (current_price - previous_price)
            / previous_price
        )

        returns.append(daily_return)

    if not returns:
        raise ValueError("Could not calculate returns from the provided prices.")

    mean_return = sum(returns) / len(returns)

    variance = sum(
        (r - mean_return) ** 2
        for r in returns
    ) / len(returns)

    volatility = variance ** 0.5

    return volatility * 100


@tool
def find_largest_drop(
    prices: list[float],
) -> float:
    """
    Find the largest percentage drop between consecutive
    stock prices.
    """

    if len(prices) < 2:
        raise ValueError(
            "At least two prices are required."
        )

    largest_drop = 0.0

    for i in range(1, len(prices)):
        previous_price = prices[i - 1]
        current_price = prices[i]

        if previous_price == 0:
            continue

        change = (
            (current_price - previous_price)
            / previous_price
        ) * 100

        if change < largest_drop:
            largest_drop = change

    return largest_drop


@tool
def compare_stocks(
    stock_1_return: float,
    stock_2_return: float,
) -> str:
    """
    Compare the percentage returns of two stocks and
    report the return difference.
    """

    difference = stock_1_return - stock_2_return

    return (
        f"Stock 1 return: {stock_1_return:.2f}%. "
        f"Stock 2 return: {stock_2_return:.2f}%. "
        f"Return difference: {difference:.2f} percentage points."
    )