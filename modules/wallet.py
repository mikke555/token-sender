import json
import random
import time

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from web3 import HTTPProvider, Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware

import settings
from data.const import ethereum
from models.network import Network
from modules.logger import logger
from modules.utils import truncate

with open("data/abi/erc20.json") as file:
    ERC20_ABI = json.load(file)


class Wallet:
    def __init__(
        self, private_key: str, counter: str = None, chain: Network = ethereum
    ):
        self.account: LocalAccount = Account.from_key(private_key)
        self.address = self.account.address
        self.label = f"{counter} {self.address} |"

        self.chain = chain
        self.w3 = Web3(HTTPProvider(chain.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def __str__(self):
        return f"Wallet(address={self.address})"

    def sign_message(self, message: str) -> str:
        message_encoded = encode_defunct(text=message)
        signed_message = self.account.sign_message(message_encoded)
        return "0x" + signed_message.signature.hex()

    def get_contract(self, address: str, abi: list[dict] = None) -> Contract:
        contract_address = self.w3.to_checksum_address(address)
        if not abi:
            abi = ERC20_ABI

        return self.w3.eth.contract(address=contract_address, abi=abi)

    def get_balance(self, token_addr: str = None) -> int:
        """
        Return the balance of ETH or a given token.
        """
        if token_addr is None:
            return self.w3.eth.get_balance(self.address)
        else:
            token = self.get_contract(token_addr)
            return token.functions.balanceOf(self.address).call()

    def get_token(self, token_addr: str, as_dict: bool = False):
        """
        Return token props: balance, decimals, symbol.
        """
        token = self.get_contract(token_addr)

        balance = token.functions.balanceOf(self.address).call()
        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()

        if as_dict:
            return {
                "balance": balance,
                "decimals": decimals,
                "symbol": symbol,
            }

        return balance, decimals, symbol

    def get_tx_data(self, value: int = 0, **kwargs):
        """
        Build a transaction dict.
        """
        return {
            "chainId": self.w3.eth.chain_id,
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "value": value,
            **kwargs,
        }

    def get_gas(self, tx: dict, gwei_multiplier: float = 1.2) -> dict:
        """
        Populate tx with either EIP-1559 or legacy gas parameters and estimate gas.
        """
        gas_price_legacy = self.w3.eth.gas_price

        max_priority_fee = self.w3.eth.max_priority_fee
        latest_block = self.w3.eth.get_block("latest")
        base_fee = int(
            max(gas_price_legacy, latest_block["baseFeePerGas"]) * gwei_multiplier
        )

        max_fee_per_gas = max_priority_fee + base_fee

        if self.chain.eip_1559:
            tx["maxFeePerGas"] = max_fee_per_gas
            tx["maxPriorityFeePerGas"] = max_priority_fee

        else:
            if self.chain.name == "bsc":
                tx["gasPrice"] = self.w3.to_wei(1, "gwei")
            else:
                tx["gasPrice"] = int(gas_price_legacy * gwei_multiplier)

        if not tx.get("gas"):
            tx["gas"] = self.w3.eth.estimate_gas(tx)

        return tx

    def sign_tx(self, tx: dict):
        return self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)

    def send_tx(
        self,
        tx: dict,
        tx_label: str = "",
        gwei_multiplier: float = 1.2,
        gwei_increment: float = 0.5,
        retry_count: int = 0,
        max_retry: int = 5,
        delay: float = 3,  # delay in seconds between retries
    ):
        while retry_count < max_retry:
            try:
                if not tx.get("gasPrice") or tx.get("maxFeePerGas"):
                    tx = self.get_gas(tx)

                # logger.debug(f"{tx_label} | Attempt {retry_count+1}: Using gas settings: {tx}")

                signed_tx = self.sign_tx(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                logger.info(f"{tx_label} | {self.chain.explorer}/tx/{tx_hash.hex()}")

                tx_receipt = self.w3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=60
                )

                if tx_receipt.status == 1:
                    logger.success(f"{tx_label} | Tx confirmed \n")
                    return True

            except Exception as err:
                logger.debug(f"{tx_label} | Error on attempt {retry_count+1}: {err}")

                # Terminate loop
                if retry_count >= max_retry - 1:
                    logger.error(f"{tx_label} | Reached max number of retries \n")
                    return False

                # Handle different type of errors
                error_str = str(err)

                if "already known" in error_str:
                    logger.info(f"{tx_label} | Tx is likely confirmed \n")
                    return True

                elif "nonce too low" in error_str:
                    logger.info(
                        f"{tx_label} | Tx likely in process, current nonce {self.w3.eth.get_transaction_count(self.address, 'pending')}"
                    )
                    return True

                elif "could not replace existing tx" in error_str:
                    logger.warning(
                        f"{tx_label} | Detected replace error, waiting before retrying"
                    )

                elif any(
                    error in error_str
                    for error in [
                        "replacement transaction underpriced",
                        "is not in the chain after",
                        "max fee per gas less than block base fee",
                        "fee cap less than block base fee",
                    ]
                ):
                    logger.warning(
                        f"{tx_label} | Underpriced or fee error, increasing gwei and retrying"
                    )

                elif "insufficient funds" in error_str:
                    logger.error(f"{tx_label} | Insufficient funds for transaction")
                    return False

                # Wait before retrying
                time.sleep(delay)
                gwei_multiplier += gwei_increment
                retry_count += 1

        logger.error(f"{tx_label} | All retry attempts failed.")
        return False

    def transfer_eth(self, value: str | int | list[float], to: str):
        balance = self.get_balance()

        if not balance:
            logger.warning(f"{self.label} no ETH balance")
            return

        tx = self.get_tx_data(to=to)
        tx = self.get_gas(tx)

        # Return transfer value in wei
        if isinstance(value, int):
            transfer_value = value
        elif isinstance(value, list):
            value_range_wei = [int(value * 10**18) for value in value]
            transfer_value = random.randint(*value_range_wei)
        elif value == "max":
            if self.chain.eip_1559:
                tx_cost = tx["maxFeePerGas"] * tx["gas"]
            else:
                tx_cost = tx["gasPrice"] * tx["gas"]

            transfer_value = balance - int(tx_cost * 1.5)
            # transfer_value = int(balance * 0.99)

        if transfer_value > balance:
            logger.warning(f"{self.label} Not enough balance")
            return

        tx["value"] = transfer_value

        amount_str = f"{self.w3.from_wei(transfer_value, 'ether'):.6f}"
        tx_label = f"{self.label} Send {amount_str} {self.chain.native_token} to {truncate(to)}"

        return self.send_tx(tx, tx_label=tx_label)

    def transfer_token(self, amount: str | int | list[float], to: str):
        token = self.get_contract(settings.TOKEN_ADDRESS)
        balance, decimals, symbol = self.get_token(token.address)

        if not balance:
            logger.warning(f"{self.label} no {symbol} balance")
            return

        # Return transfer value in wei
        if isinstance(amount, int):
            transfer_amount = amount
        elif isinstance(amount, list):
            amount_range_wei = [int(value * 10**decimals) for value in amount]
            transfer_amount = random.randint(*amount_range_wei)
        elif amount == "max":
            transfer_amount = balance

        if transfer_amount > balance:
            logger.warning(f"{self.label} Selected amount exceeds wallet balance")

        tx_data = self.get_tx_data()
        tx = token.functions.transfer(to, transfer_amount).build_transaction(tx_data)
        tx["gas"] = int(tx["gas"] * 1.2)  # to prevent txns from failing on ETH Mainnet

        amount_str = f"{transfer_amount / (10**decimals):.6f}"
        tx_label = f"{self.label} Transfer {amount_str} {symbol} to {truncate(to)}"

        return self.send_tx(tx, tx_label=tx_label)

    def transfer(self, token: str, amount: str | int | list[float], recipient: str):
        recipient = self.w3.to_checksum_address(recipient)

        if token == self.chain.native_token:
            return self.transfer_eth(value=amount, to=recipient)
        elif token == "ERC20":
            return self.transfer_token(amount=amount, to=recipient)
