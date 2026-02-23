import enum


parsing_url = "https://www.coingecko.com/en/coins"

class EnumShortName(enum.Enum):
    btc = 'bitcoin'
    eth = 'ethereum'
    usdt = 'tether'
    xrp = 'xrp'
    solana = 'solana'


def formated_to_display_price(price: float) -> str:
    return f"${price:,.2f}"