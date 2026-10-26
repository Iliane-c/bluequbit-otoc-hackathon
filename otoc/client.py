"""BlueQubit client initialisation."""

from __future__ import annotations

import os

import bluequbit
from dotenv import load_dotenv

TOKEN_ENV_VAR = "BLUEQUBIT_API_TOKEN"


def connect() -> bluequbit.BQClient:
    """Load ``.env`` and return an authenticated BlueQubit client.

    Raises:
        RuntimeError: if the API token is missing.
    """
    load_dotenv()
    token = os.getenv(TOKEN_ENV_VAR)
    if not token or token.startswith("your_"):
        raise RuntimeError(
            f"{TOKEN_ENV_VAR} is not set. Copy .env.example to .env and paste "
            "your token (BlueQubit dashboard -> See API token)."
        )
    return bluequbit.init(api_token=token)
