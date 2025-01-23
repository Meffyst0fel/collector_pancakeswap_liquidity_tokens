import asyncio
import json
from asyncio import sleep
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import requests
from web3 import AsyncWeb3


@dataclass
class TokenData:
    token_name_0: str
    token_address_0: str
    token_symbol_0: str

    token_name_1: str
    token_symbol_1: str
    token_address_1: str

    tx_hash: str

    token_price0: Decimal | None = None
    token_price1: Decimal | None = None


class TokenInfoPrinter:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

    def display(self, tokens: list[TokenData]) -> None:
        for token in tokens:
            
            print(
                f"{self.YELLOW}[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}][Token] New Token Detected: {self.CYAN}{token.token_name_0} ({token.token_symbol_0}) /{self.CYAN}{token.token_name_1} ({token.token_symbol_1}): {self.MAGENTA}{token.token_address_0} / {token.token_address_1} https://bscscan.com/tx/{token.tx_hash}{self.RESET} Price: Token0={str(token.token_price0)}, Token1={str(token.token_price1)}"
            )

import aiohttp
from decimal import Decimal
from typing import Optional
class TokenPriceFetcher:
    def __init__(self, api_key: str, max_requests_per_minute: int = 60):
        self._api_key = api_key
        self._semaphore = asyncio.Semaphore(max_requests_per_minute // 30)  # 2 geisiad yr eiliad / 2 запити на секунду 

    async def get_token_price(self, token_address: str) -> Optional[Decimal]:
        url = f"https://public-api.birdeye.so/defi/price?address={token_address}"
        headers = {
            "accept": "application/json",
            "x-chain": "bsc",
            "X-API-KEY": self._api_key,
        }

        async with self._semaphore:  # Cyfyngu nifer y ceisiadau cyfochrog / Обмеження кількості паралельних запитів
            await asyncio.sleep(2)  # Oediad o 2 eiliad rhwng ceisiadau / Затримка у 2 секунди між запитами  
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 429:  # Too Many Requests
                            retry_after = int(response.headers.get("Retry-After", 1))
                            print(f"Rate limit reached. Retrying after {retry_after} seconds.")
                            await asyncio.sleep(retry_after)
                            return await self.get_token_price(token_address)
                        elif response.status != 200:
                            print(f"Error: {response.status}, {await response.text()}")
                            return None

                        data = await response.json()
                        if data.get("success") and "data" in data and "value" in data["data"]:
                            return Decimal(str(data["data"]["value"])).quantize(Decimal("1e-18"))
                except Exception as e:
                    print(f"Exception while fetching token price: {e}")
        return None
class TokenPriceCollector:

    def __init__(
        self,
        token_info_printer: TokenInfoPrinter,
        price_fetcher: TokenPriceFetcher,
    ):
        self._tokens_to_check: list[TokenData] = []
        self._token_info_printer = token_info_printer
        self._price_fetcher = price_fetcher

    async def run(self) -> None:
        while True:
            pending_tokens = []
            checked_tokens = []

            for i, token in enumerate(self._tokens_to_check):

                if i > 29:
                    break

                token_price0 = await self._price_fetcher.get_token_price(token.token_address_0)
                token_price1 = await self._price_fetcher.get_token_price(token.token_address_1)
                if not (token_price0 and token_price1):
                    pending_tokens.append(token)
                    continue
                token.token_price0 = token_price0
                token.token_price1 = token_price1
                checked_tokens.append(token)

            self._tokens_to_check = pending_tokens
            self._token_info_printer.display(
                tokens=checked_tokens
            )

            await asyncio.sleep(3 * 60)

    def add_to_queue(
        self,
        token_data: TokenData,
    ) -> None:
        self._tokens_to_check.append(token_data)
class TokensCollector:

    def __init__(
        self,
        token_price_collector: TokenPriceCollector,
        liquidity_pair_address: str = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
    ):
        self._web_client = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("https://bsc-dataseed2.binance.org/"))
        self._token_price_collector = token_price_collector
        self._liquidity_pair_address = liquidity_pair_address

        self._contract = self._web_client.eth.contract(  # noqa
            address='0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',  # Testnet #0x6725F303b657a9451d8BA641348b6761A6CC7a17
            abi=json.loads(
                '[{"inputs":[{"internalType":"address","name":"_feeToSetter","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"address","name":"pair","type":"address"},{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"PairCreated","type":"event"},{"constant":true,"inputs":[],"name":"INIT_CODE_PAIR_HASH","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"allPairs","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"allPairsLength","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"}],"name":"createPair","outputs":[{"internalType":"address","name":"pair","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"feeTo","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"feeToSetter","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_feeTo","type":"address"}],"name":"setFeeTo","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_feeToSetter","type":"address"}],"name":"setFeeToSetter","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]'
            ),
        )
        self._token_name_abi = json.loads(
            '[ { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "owner", "type": "address" }, { "indexed": true, "internalType": "address", "name": "spender", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "value", "type": "uint256" } ], "name": "Approval", "type": "event" }, { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "from", "type": "address" }, { "indexed": true, "internalType": "address", "name": "to", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "value", "type": "uint256" } ], "name": "Transfer", "type": "event" }, { "constant": true, "inputs": [ { "internalType": "address", "name": "_owner", "type": "address" }, { "internalType": "address", "name": "spender", "type": "address" } ], "name": "allowance", "outputs": [ { "internalType": "uint256", "name": "", "type": "uint256" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": false, "inputs": [ { "internalType": "address", "name": "spender", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "approve", "outputs": [ { "internalType": "bool", "name": "", "type": "bool" } ], "payable": false, "stateMutability": "nonpayable", "type": "function" }, { "constant": true, "inputs": [ { "internalType": "address", "name": "account", "type": "address" } ], "name": "balanceOf", "outputs": [ { "internalType": "uint256", "name": "", "type": "uint256" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": true, "inputs": [], "name": "decimals", "outputs": [ { "internalType": "uint256", "name": "", "type": "uint256" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": true, "inputs": [], "name": "getOwner", "outputs": [ { "internalType": "address", "name": "", "type": "address" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": true, "inputs": [], "name": "name", "outputs": [ { "internalType": "string", "name": "", "type": "string" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": true, "inputs": [], "name": "symbol", "outputs": [ { "internalType": "string", "name": "", "type": "string" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": true, "inputs": [], "name": "totalSupply", "outputs": [ { "internalType": "uint256", "name": "", "type": "uint256" } ], "payable": false, "stateMutability": "view", "type": "function" }, { "constant": false, "inputs": [ { "internalType": "address", "name": "recipient", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "transfer", "outputs": [ { "internalType": "bool", "name": "", "type": "bool" } ], "payable": false, "stateMutability": "nonpayable", "type": "function" }, { "constant": false, "inputs": [ { "internalType": "address", "name": "sender", "type": "address" }, { "internalType": "address", "name": "recipient", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "transferFrom", "outputs": [ { "internalType": "bool", "name": "", "type": "bool" } ], "payable": false, "stateMutability": "nonpayable", "type": "function" } ]'
        )

    async def run(self) -> None:
        event_filter = await self._contract.events.PairCreated.create_filter(from_block="latest")
        while True:
            for event in (await event_filter.get_new_entries()):
                if (
                    event['args']['token1'] == self._liquidity_pair_address or
                    event['args']['token0'] == self._liquidity_pair_address
                ):
                    token_address_0 = event['args']['token0']
                    get_token_name0 = self._web_client.eth.contract(
                        address=token_address_0,
                        abi=self._token_name_abi,
                    )

                    token_address_1 = event['args']['token1']
                    get_token_name_1 = self._web_client.eth.contract(
                        address=token_address_1,
                        abi=self._token_name_abi,
                    )

                    print("Added new token.")
                    self._token_price_collector.add_to_queue(
                        token_data=TokenData(
                            token_name_0=await get_token_name0.functions.name().call(),
                            token_symbol_0=await get_token_name0.functions.symbol().call(),
                            token_address_0=token_address_0,
                            token_name_1=await get_token_name_1.functions.name().call(),
                            token_symbol_1=await get_token_name_1.functions.symbol().call(),
                            token_address_1=token_address_1,
                            tx_hash=self._web_client.to_hex(event['transactionHash']),
                        )
                    )
            await asyncio.sleep(1)


async def main():
    token_price_fetcher = TokenPriceFetcher(api_key='cc25e77d6bac43f4bb778244324a5838') #BIRDEYE_API_KEY
    token_price_collector = TokenPriceCollector(
        token_info_printer=TokenInfoPrinter(),
        price_fetcher=token_price_fetcher,
    )
    token_collector = TokensCollector(
        token_price_collector=token_price_collector,
    )

    await asyncio.gather(token_collector.run(), token_price_collector.run())

asyncio.run(main())
