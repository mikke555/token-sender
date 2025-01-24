import settings
from data.const import KEYS, RECIPIENTS
from models.transfer import *
from modules.logger import logger
from modules.questionary import get_user_input
from modules.utils import divide_amounts_evenly, sleep
from modules.wallet import Wallet


def process_wallets(params: dict):
    transfer = Transfer(**params)  # config object holding transfer params

    # PART 1: build a list of (sender, recipient) pairs
    if transfer.action == "collect":
        # Multiple senders -> one recipient
        pairs = [(key, RECIPIENTS[0]) for key in KEYS]
        total = len(KEYS)
    elif transfer.action == "dispense":
        # One sender -> multiple recipients
        pairs = [(KEYS[0], recipient) for recipient in RECIPIENTS]
        total = len(RECIPIENTS)
        # Equal number of senders & recipients
    elif transfer.action == "one-to-one":
        pairs = [(key, recipient) for key, recipient in zip(KEYS, RECIPIENTS)]
        total = len(KEYS)

    # PART 2: build a list of values for even amounts
    chunked_amounts = []
    if transfer.action == "dispense" and transfer.amount == "even":
        dispensor = Wallet(KEYS[0], "[0/1]", transfer.chain)

        balance = (
            dispensor.get_balance()
            if transfer.token == "ETH"
            else dispensor.get_balance(settings.TOKEN_ADDRESS)
        )

        chunked_amounts = divide_amounts_evenly(balance, total + 1)

    # PART 3: execute the main loop
    for index, (sender, recipient) in enumerate(pairs, start=1):
        counter = f"[{index}/{total}]"
        wallet = Wallet(sender, counter, transfer.chain)

        #  Determine the actual amount for each iteration
        if transfer.action == "dispense" and transfer.amount == "even":
            actual_amount = chunked_amounts[index - 1]
        else:
            actual_amount = transfer.amount

        tx_status = wallet.transfer(transfer.token, actual_amount, recipient)

        if tx_status and index < total:
            sleep(*settings.SLEEP_BETWEEN_ACTIONS)


def main():
    transfer_params = get_user_input()
    process_wallets(transfer_params)


if __name__ == "__main__":
    try:
        main()
        logger.success("All done! 🎉")
    except KeyboardInterrupt:
        logger.warning("Cancelled by the user")
        exit(0)
