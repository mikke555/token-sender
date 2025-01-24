from dataclasses import dataclass

from models.network import Network


@dataclass
class Transfer:
    action: str
    token: str
    amount: str | list
    chain: Network
