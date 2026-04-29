"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            raise RuntimeError(
                "BOT_TOKEN belum diset. Isi file .env untuk lokal atau Variables di Railway."
            )

        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
        return cls(bot_token=bot_token, log_level=log_level)
