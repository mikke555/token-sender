from models.network import Network

with open("keys.txt") as file:
    KEYS = [row.strip() for row in file]

with open("recipients.txt") as file:
    RECIPIENTS = [row.strip() for row in file]

ethereum = Network(
    name="ethereum",
    rpc_url="https://rpc.ankr.com/eth",
    explorer="https://etherscan.io",
    eip_1559=True,
    native_token="ETH",
)

sepolia = Network(
    name="sepolia",
    rpc_url="https://rpc.ankr.com/eth_sepolia",
    explorer="https://sepolia.etherscan.io/",
    eip_1559=True,
    native_token="ETH",
)

linea = Network(
    name="linea",
    rpc_url="https://rpc.linea.build",
    explorer="https://lineascan.build",
    eip_1559=True,
    native_token="ETH",
)

arbitrum = Network(
    name="arbitrum",
    rpc_url="https://rpc.ankr.com/arbitrum",
    explorer="https://arbiscan.io",
    eip_1559=True,
    native_token="ETH",
)

optimism = Network(
    name="optimism",
    rpc_url="https://rpc.ankr.com/optimism",
    explorer="https://optimistic.etherscan.io",
    eip_1559=True,
    native_token="ETH",
)

base = Network(
    name="base",
    rpc_url="https://mainnet.base.org",
    explorer="https://basescan.org",
    eip_1559=True,
    native_token="ETH",
)

bsc = Network(
    name="bsc",
    rpc_url="https://rpc.ankr.com/bsc",
    explorer="https://bscscan.com",
    eip_1559=False,
    native_token="BNB",
)

opbnb = Network(
    name="opbnb",
    rpc_url="https://opbnb-mainnet-rpc.bnbchain.org",
    explorer="https://opbnbscan.com",
    eip_1559=False,
    native_token="BNB",
)

CHAIN_MAPPING = {
    "ethereum": ethereum,
    "sepolia": sepolia,
    "linea": linea,
    "arbitrum": arbitrum,
    "optimism": optimism,
    "base": base,
    "bsc": bsc,
    "opbnb": opbnb,
}
