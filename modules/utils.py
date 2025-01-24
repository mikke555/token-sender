import random
import time
from datetime import datetime

from tqdm import tqdm

import settings


def truncate(address: str) -> str:
    """
    Truncates an Ethereum address to the format 0x1234...abcd12.
    """
    return f"{address[:6]}...{address[-6:]}"


def random_sleep(max_time, min_time=1):
    if min_time > max_time:
        min_time, max_time = max_time, min_time

    duration = random.randint(min_time, max_time)
    time.sleep(duration)


def sleep(sleep_time, to_sleep=None, label="Sleep until next account"):
    if to_sleep is not None:
        x = random.randint(sleep_time, to_sleep)
    else:
        x = sleep_time

    desc = datetime.now().strftime("%H:%M:%S")

    for _ in tqdm(
        range(x), desc=desc, bar_format=f"{{desc}} | {label} {{n_fmt}}/{{total_fmt}}"
    ):
        time.sleep(1)

    print()


def divide_amounts_evenly(total_amount, N, variance=settings.VARIANCE):
    # Calculate the average amount per part
    average_amount = total_amount / N

    # Determine lower and upper boundaries based on the allowed variance
    lower_boundary = average_amount * (1 - variance)
    upper_boundary = average_amount * (1 + variance)

    # Generate num_parts random amounts within the specified boundaries
    random_values = [random.uniform(lower_boundary, upper_boundary) for _ in range(N)]

    # Calculate a scale factor to adjust the random values so their sum equals total_amount
    scale_factor = total_amount / sum(random_values)

    # Apply the scale factor and convert the amounts to integers
    amounts = [int(value * scale_factor) for value in random_values]

    # Adjust the amounts to ensure the total sum exactly equals total_amount
    difference = total_amount - sum(amounts)
    for i in range(abs(difference)):
        index = i % N
        # If the difference is positive, increment the amount; if negative, decrement
        amounts[index] += 1 if difference > 0 else -1

    return amounts
