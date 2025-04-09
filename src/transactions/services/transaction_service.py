from web3 import Web3


async def create_eth_transaction(
    endpoint_url: str, receiver: str, eth_value: float, gas_price: float
):
    """Создаёт транзакцию и возвращает её структуру"""
    try:
        w3 = Web3(Web3.HTTPProvider(endpoint_uri=endpoint_url))
        if not w3.is_connected():
            raise ConnectionError("RPC connection failed, try other URL for connection")

        wei_value = w3.to_wei(eth_value, "ether")

        tx = {
            "to": receiver,
            "value": wei_value,
            "gas": 21000,
            "gasPrice": w3.to_wei(gas_price, "gwei"),
            "chainId": w3.eth.chain_id,
        }

        return tx

    except Exception as e:
        return f"не удалось обработать транзакцию: {e}"
