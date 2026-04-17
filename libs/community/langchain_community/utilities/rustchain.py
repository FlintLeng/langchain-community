"""RustChain API utility — connects any LangChain agent to RustChain."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

DEFAULT_NODE_URL = "https://50.28.86.131"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


class RustChainAPIWrapper:
    """Wrapper around the RustChain HTTP API for use as a LangChain tool.

    RustChain is a crypto-mining blockchain with an agent-native API:
    - No auth required
    - Wallet = any string
    - Same-day RTC payouts for bounty contributors

    Setup:
        .. code-block:: bash

            pip install langchain-community

    Usage:
        .. code-block:: python

            from langchain_community.utilities.rustchain import RustChainAPIWrapper
            from langchain_community.tools.rustchain import CheckBalance, ListBounties, GetNodeHealth

            api = RustChainAPIWrapper()
            tool = CheckBalance(api_wrapper=api)
            result = tool.invoke({"wallet": "alice"})
    """

    def __init__(
        self,
        node_url: str = DEFAULT_NODE_URL,
        timeout: int = 15,
    ) -> None:
        self.node_url = node_url.rstrip("/")
        self.timeout  = timeout

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.node_url}/{path.lstrip('/')}"
        if params:
            from urllib.parse import urlencode
            url += "?" + urlencode(params)
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "detail": e.read().decode(errors="replace")[:200]}
        except Exception as e:
            return {"error": str(e)}

    def _post(self, path: str, payload: Dict) -> Any:
        url  = f"{self.node_url}/{path.lstrip('/')}"
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "detail": e.read().decode(errors="replace")[:200]}
        except Exception as e:
            return {"error": str(e)}

    # ── Public API methods ────────────────────────────────────────────────────

    def check_balance(self, wallet: str) -> float:
        """Check the RTC balance of a wallet.

        Args:
            wallet: Wallet name or address (any string is valid).

        Returns:
            Balance as a float, or -1 if the wallet is not found.
        """
        result = self._get("/wallet/balance", {"wallet": wallet})
        if isinstance(result, dict) and "balance" in result:
            try:
                return float(result["balance"])
            except (ValueError, TypeError):
                pass
        # Fallback path
        result2 = self._get(f"/wallet/{wallet}/balance")
        if isinstance(result2, dict) and "balance" in result2:
            try:
                return float(result2["balance"])
            except (ValueError, TypeError):
                pass
        return -1.0

    def list_bounties(self, limit: int = 10, status: str = "open") -> List[Dict]:
        """List open bounties on RustChain.

        Args:
            limit: Maximum number of bounties to return (default: 10).
            status: Filter by status: "open", "closed", "all" (default: "open").

        Returns:
            List of bounty dicts with keys: number, title, reward, status.
        """
        result = self._get("/bounties", {"limit": str(limit), "status": status})
        if isinstance(result, list):
            return result[:limit]
        if isinstance(result, dict) and "bounties" in result:
            return result["bounties"][:limit]
        return [{"error": "Could not fetch bounties", "raw": str(result)[:200]}]

    def get_node_health(self) -> Dict:
        """Get RustChain node health and version info.

        Returns:
            Dict with keys: ok, version, uptime_s, db_rw.
        """
        result = self._get("/health")
        return result if isinstance(result, dict) else {"error": str(result)}

    def get_current_epoch(self) -> Dict:
        """Get the current epoch number."""
        result = self._get("/epoch/current")
        if isinstance(result, dict):
            return result
        return {"epoch": -1, "raw": str(result)[:100]}

    def send_rtc(self, from_wallet: str, to_wallet: str, amount: float,
                 admin_key: str) -> Dict:
        """Send RTC from one wallet to another (requires admin_key)."""
        return self._post("/wallet/send", {
            "from":      from_wallet,
            "to":        to_wallet,
            "amount":    int(amount),
            "admin_key": admin_key,
        })

    def run(self, query: str) -> str:
        """Run a natural-language query against the RustChain API.

        Parses the query to determine which method to call.
        Supports: "balance of <wallet>", "list bounties", "node health".
        """
        q = query.lower().strip()
        if "balance" in q:
            # Extract wallet name
            wallet = q.replace("balance", "").replace("of", "").strip()
            bal = self.check_balance(wallet)
            return f"Balance of {wallet}: {bal} RTC"
        elif "bounty" in q:
            bounties = self.list_bounties()
            return json.dumps(bounties, indent=2)
        elif "health" in q or "epoch" in q:
            health = self.get_node_health()
            epoch  = self.get_current_epoch()
            return json.dumps({"node": health, "epoch": epoch}, indent=2)
        else:
            health = self.get_node_health()
            return json.dumps(health, indent=2)
