import hashlib
import hmac
from urllib.parse import parse_qs
from config import BOT_TOKEN

def verify_telegram_init_data(init_data: str):
    parsed = dict(parse_qs(init_data))
    hash_value = parsed.pop("hash", [None])[0]

    data_check_string = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return calculated_hash == hash_value
  
