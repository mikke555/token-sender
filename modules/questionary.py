import questionary
from questionary import Style
from tabulate import tabulate

import settings
from data.const import CHAIN_MAPPING, KEYS, RECIPIENTS
from models.network import Network
from modules.logger import logger
from modules.utils import truncate
from modules.wallet import Wallet

"""
This module provides an interactive CLI using 
`questionary` for user prompts &
`tabulate` for summary table.
"""

# ANSI color codes
BRIGHT_GREEN = "\033[92m"  # Bright green
RESET = "\033[0m"  # Reset color

style = Style(
    [
        ("qmark", "fg:#2196f3 bold"),
        ("question", "bold"),
        ("answer", "fg:#2196f3 bold"),
        ("pointer", "fg:#673ab7 bold"),
        ("highlighted", "fg:#673ab7 bold"),
        ("selected", "fg:#cc5454"),
        ("instruction", "fg:#8c8c8c italic"),
    ]
)


def get_exact_amount():
    while True:
        try:
            min_amount = float(questionary.text("Enter min amount: ").ask())
            max_amount = float(questionary.text("Enter max amount: ").ask())
            if max_amount < min_amount:
                logger.warning(
                    f"Min amount {min_amount:.6f} cannot exceed max {max_amount:.6f}"
                )
                continue
            return [min_amount, max_amount]
        except ValueError:
            logger.warning(f"Input must be a numeric value")


def build_confirmation_message(
    action: str, amount: str | list[float], chain: Network, dispensor: str, symbol: str
):
    """
    Builds a user-friendly table with the transfer data using tabulate.
    """
    collector = truncate(str(RECIPIENTS[0]))
    dispensor = truncate(dispensor)

    # Convert 'amount' into a readable string
    if isinstance(amount, list):
        amount_str = f"{amount[0]:.6f}-{amount[1]:.6f}"
    else:
        amount_str = amount.upper()

    if action == "collect":
        sender = f"{str(len(KEYS)) + ' accounts'}"
        recipient = collector
    elif action == "dispense":
        sender = dispensor
        recipient = (
            truncate(RECIPIENTS[0])
            if len(RECIPIENTS) == 1
            else f"{len(RECIPIENTS)} recipients"
        )
    elif action == "one-to-one":
        sender = f"{str(len(KEYS)) + ' accounts'}"
        recipient = f"{str(len(RECIPIENTS)) + ' recipients'}"

    table_data = [
        ["Mode", action],
        ["Amount", amount_str],
        ["Token", f"{BRIGHT_GREEN}{symbol}{RESET}"],
        ["From", sender],
        ["To", recipient],
        ["Chain", f"{BRIGHT_GREEN}{chain.name.upper()}{RESET}"],
    ]

    confirmation_table = tabulate(table_data, tablefmt="double_grid")
    return confirmation_table


def get_user_input() -> dict:
    chain = CHAIN_MAPPING.get(settings.CHAIN)
    ETH = chain.native_token  # ETH | BNB | POL etc.
    wallet = Wallet(KEYS[0], chain=chain)

    if settings.TOKEN_ADDRESS:
        symbol = wallet.get_token(settings.TOKEN_ADDRESS, as_dict=True)["symbol"]

    # Q1: Get action
    action = questionary.select(
        f"Select action:",
        choices=["collect", "dispense", "one-to-one"],
        style=style,
    ).ask()

    if action == "collect" and len(RECIPIENTS) > 1:
        logger.warning("Only one recipient (evm address) allowed for collector mode")
        exit(0)

    if action == "dispense" and len(KEYS) > 1:
        logger.warning("Only one sender (private key) allowed for dispensor mode")
        exit(0)

    if action == "one-to-one" and len(KEYS) != len(RECIPIENTS):
        logger.warning(
            "Number of keys & recipients should be the same for one-to-one transfer"
        )
        exit(0)

    if not action:
        exit(0)

    # Q2: Get token
    token_list = [ETH]
    if settings.TOKEN_ADDRESS:
        token_list.append(
            questionary.Choice(
                value="ERC20",
                title=f"{symbol} (ERC20)",
            ),
        )

    token = questionary.select(
        f"Select token {'to transfer' if action == 'one-to-one' else 'to ' + action }:",
        choices=token_list,
        style=style,
    ).ask()

    if not token:
        exit(0)

    # Q3: Get amount
    if action == "collect":
        amount = "max"

    if action == "dispense":
        amount = questionary.select(
            f"Select amount to {action}:",
            choices=["even", "exact"],
            style=style,
        ).ask()

    if action == "one-to-one":
        amount = questionary.select(
            f"Select amount to transfer:",
            choices=["max", "exact"],
            style=style,
        ).ask()

    if amount == "exact":
        amount = get_exact_amount()

    # Final check If anything came back None
    if any(x is None for x in [action, token, amount]):

        exit(0)

    # Summorize transfer and prompt for final confrimation
    msg_params = [action, amount, wallet.chain, wallet.address]
    msg_params.append(ETH) if token == ETH else msg_params.append(symbol)

    print()  # line break
    print(build_confirmation_message(*msg_params))

    confirmation = questionary.confirm(
        "Proceed with the transfer? \n", style=style
    ).ask()

    if not confirmation:
        exit(0)

    return {
        "token": token,
        "action": action,
        "amount": amount,
        "chain": chain,
    }
