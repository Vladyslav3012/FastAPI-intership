from app.config import settings


demo_coingecko_key = settings.DEMO_COINGECKO_KEY

coins = "bitcoin,ethereum,tether,ripple,solana"

api_crypto_url = (f"https://api.coingecko.com/api/v3/simple/"
                  f"price?vs_currencies=usd&ids={coins}&"
                  f"x_cg_demo_api_key={demo_coingecko_key}")


def formated_to_display_price(price: float) -> str:
    return f"${price:,.2f}"
