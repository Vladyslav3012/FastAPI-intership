import enum
from app.config import settings


parsing_url = "https://www.coingecko.com/en/coins"

demo_coingecko_key = settings.DEMO_COINGECKO_KEY
coins = "bitcoin,ethereum,tether,ripple,solana"
api_crypto_url = (f"https://api.coingecko.com/api/v3/simple/"
                  f"price?vs_currencies=usd&ids={coins}&"
                  f"x_cg_demo_api_key={demo_coingecko_key}")


class EnumNameCoin(enum.Enum):
    btc = 'bitcoin'
    eth = 'ethereum'
    usdt = 'tether'
    ripple = 'ripple'
    solana = 'solana'


def formated_to_display_price(price: float) -> str:
    return f"${price:,.2f}"