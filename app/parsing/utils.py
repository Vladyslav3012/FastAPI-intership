import enum


class EnumNameCoin(enum.Enum):
    btc = 'bitcoin'
    eth = 'ethereum'
    usdt = 'tether'
    ripple = 'ripple'
    solana = 'solana'


parsing_url = "https://www.coingecko.com/en/coins"
