"""TRX PRO - Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///trx_pro.db")
REDIS_URL = os.environ.get("REDIS_URL", "")
TRONGRID_API_KEY = os.environ.get("TRONGRID_API_KEY", "")
TRON_NETWORK = os.environ.get("TRON_NETWORK", "mainnet")
TRONGRID_BASE = "https://api.trongrid.io" if TRON_NETWORK == "mainnet" else "https://api.shasta.trongrid.io"
TONCENTER_API_KEY = os.environ.get("TONCENTER_API_KEY", "")
TON_NETWORK = os.environ.get("TON_NETWORK", "mainnet")
TONCENTER_BASE = "https://toncenter.com/api/v2/" if TON_NETWORK == "mainnet" else "https://testnet.toncenter.com/api/v2/"
PROJECT_WALLET_TRX = os.environ.get("PROJECT_WALLET_TRX", "")
PROJECT_WALLET_TON = os.environ.get("PROJECT_WALLET_TON", "")
PROJECT_WALLET_USDT = os.environ.get("PROJECT_WALLET_USDT", "")
TAP_BASE_REWARD = 0.1
TAP_DAILY_LIMIT = 1000
ENERGY_REGEN_RATE = 1
ENERGY_MAX_BASE = 100
LEVEL_UP_BASE_XP = 100
LEVEL_UP_MULTIPLIER = 1.5
PROJECT_FEE_PERCENT = 10
WITHDRAWAL_FEE_PERCENT = 5
MIN_WITHDRAWAL_TRX = 1000
MIN_WITHDRAWAL_TON = 100
MIN_WITHDRAWAL_USDT = 100
CRASH_HOUSE_EDGE = 0.04
CRASH_MAX_MULTIPLIER = 30.0
CRASH_ROUND_DELAY = 5
REFERRAL_BONUS_AMOUNT = 400
REFERRAL_BONUS_COOLDOWN_DAYS = 30
REFERRAL_COMMISSION_RATES = {
    1: 10.0, 2: 8.0, 3: 6.0, 4: 5.0, 5: 4.0,
    6: 3.0, 7: 3.0, 8: 3.0, 9: 3.0, 10: 3.0,
    11: 2.0, 12: 2.0, 13: 2.0, 14: 2.0, 15: 2.0,
    16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0,
}
ADMIN_TELEGRAM_IDS = set(
    x.strip() for x in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",") if x.strip()
)
# force rebuild 1783869590

FORCE_JOIN_CHAT_ID = os.environ.get("FORCE_JOIN_CHAT_ID", "@botgrups")
FORCE_JOIN_INVITE_LINK = os.environ.get("FORCE_JOIN_INVITE_LINK", "https://t.me/botgrups")

BINARY_MATCH_VOLUME = float(os.environ.get("BINARY_MATCH_VOLUME", "1000"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# ---- NFT Marketplace settings ----
NFT_MINT_FEE_USDT = float(os.environ.get("NFT_MINT_FEE_USDT", "10"))
NFT_MINT_FEE_TRX = float(os.environ.get("NFT_MINT_FEE_TRX", "111"))
NFT_MINT_FEE_TON = float(os.environ.get("NFT_MINT_FEE_TON", "2.05"))

NFT_MARKETPLACE_BUYER_FEE_PERCENT = float(os.environ.get("NFT_MARKETPLACE_BUYER_FEE_PERCENT", "5"))
NFT_MARKETPLACE_SELLER_FEE_PERCENT = float(os.environ.get("NFT_MARKETPLACE_SELLER_FEE_PERCENT", "5"))

NFT_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB limit for base64 image uploads

SPIN_WHEEL_SEGMENTS = [
    {"label": "0.5 TRX", "currency": "TRX", "amount": 0.5, "weight": 25, "type": "prize"},
    {"label": "1 TRX", "currency": "TRX", "amount": 1, "weight": 20, "type": "prize"},
    {"label": "0.05 TON", "currency": "TON", "amount": 0.05, "weight": 15, "type": "prize"},
    {"label": "0.05 USDT", "currency": "USDT", "amount": 0.05, "weight": 15, "type": "prize"},
    {"label": "Free Spin", "currency": None, "amount": 0, "weight": 10, "type": "free_spin"},
    {"label": "3 TRX", "currency": "TRX", "amount": 3, "weight": 7, "type": "prize"},
    {"label": "0.2 TON", "currency": "TON", "amount": 0.2, "weight": 4, "type": "prize"},
    {"label": "0.2 USDT", "currency": "USDT", "amount": 0.2, "weight": 2, "type": "prize"},
    {"label": "10 TRX", "currency": "TRX", "amount": 10, "weight": 1.5, "type": "prize"},
    {"label": "JACKPOT", "currency": "MULTI", "amount": 0, "weight": 0.5, "type": "jackpot"},
]

SPIN_JACKPOT_PRIZES = {"TON": 1, "USDT": 1, "TRX": 10}
