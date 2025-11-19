"""Contract validation between CEX and DEX venues."""
from __future__ import annotations

from typing import Optional, Tuple


def validate_contracts(cex_contract: Optional[str], dex_contract: Optional[str]) -> Tuple[bool, Optional[str]]:
    if cex_contract and dex_contract:
        if cex_contract.lower() != dex_contract.lower():
            return False, "contract mismatch"
        return True, "contract verified"
    return True, None

