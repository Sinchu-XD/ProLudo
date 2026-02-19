import hashlib
import hmac
import time
from urllib.parse import parse_qs
from config import BOT_TOKEN


# Max age of Telegram auth (in seconds)
MAX_AUTH_AGE = 86400  # 24 hours


def verify_telegram_init_data(init_data: str) -> bool:
    """
    Verifies Telegram Mini App initData securely.
    """

    try:
        parsed = dict(parse_qs(init_data))

        if "hash" not in parsed:
            return False

        received_hash = parsed.pop("hash")[0]

        # Build data check string
        data_check_string = "\n".join(
            f"{k}={v[0]}" for k, v in sorted(parsed.items())
        )

        # Generate secret key
        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

        # Calculate HMAC
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison (prevents timing attacks)
        if not hmac.compare_digest(calculated_hash, received_hash):
            return False

        # Optional: Validate auth_date to prevent replay attacks
        auth_date = int(parsed.get("auth_date", [0])[0])
        current_time = int(time.time())

        if current_time - auth_date > MAX_AUTH_AGE:
            return False

        return True

    except Exception:
        return False
