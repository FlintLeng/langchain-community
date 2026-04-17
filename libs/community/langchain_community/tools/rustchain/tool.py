"""RustChain tools for LangChain agents."""

from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from langchain_community.utilities.rustchain import RustChainAPIWrapper


# ── Input schemas ──────────────────────────────────────────────────────────────

class CheckBalanceInput(BaseModel):
    """Input for CheckBalance tool."""
    wallet: str = Field(
        description="The wallet name or address to check the balance of. "
                    "Any string is valid as a RustChain wallet."
    )


class ListBountiesInput(BaseModel):
    """Input for ListBounties tool."""
    limit: int = Field(
        default=10,
        description="Maximum number of bounties to return (default: 10)."
    )
    status: str = Field(
        default="open",
        description="Filter by bounty status: 'open', 'closed', or 'all' (default: open)."
    )


class GetNodeHealthInput(BaseModel):
    """Input for GetNodeHealth tool (no parameters needed)."""
    pass


class GetCurrentEpochInput(BaseModel):
    """Input for GetCurrentEpoch tool (no parameters needed)."""
    pass


# ── Tools ──────────────────────────────────────────────────────────────────────

class CheckBalance(BaseTool):
    """Check the RTC balance of any wallet on RustChain.

    RustChain wallet = any string (no account creation required).
    This tool queries the RustChain node to get the real-time balance.

    Setup:
        .. code-block:: bash

            pip install langchain-community

        No API key required — RustChain has no auth.

    Instantiation:
        .. code-block:: python

            from langchain_community.tools.rustchain import CheckBalance
            from langchain_community.utilities.rustchain import RustChainAPIWrapper

            api = RustChainAPIWrapper()
            tool = CheckBalance(api_wrapper=api)

    Invocation:
        .. code-block:: python

            tool.invoke({"wallet": "alice"})
            # → "Balance of alice: 42.5 RTC"
    """

    name: str = "check_rustchain_balance"
    description: str = (
        "Check the RTC token balance of a wallet on RustChain. "
        "Use this when you need to know how many RTC tokens a wallet holds. "
        "Input is the wallet name (any string is valid — no account needed)."
    )
    args_schema: Type[BaseModel] = CheckBalanceInput
    api_wrapper: RustChainAPIWrapper

    def _run(
        self,
        wallet: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        balance = self.api_wrapper.check_balance(wallet)
        if balance < 0:
            return f"Wallet '{wallet}' not found or has 0 balance."
        return f"Balance of {wallet}: {balance} RTC"


class ListBounties(BaseTool):
    """List open bounties on RustChain.

    RustChain runs a bounty program where contributors earn RTC for:
    - Filing bug reports
    - Writing documentation
    - Creating content
    - Building integrations

    Use this tool to discover what bounties are currently available.

    Setup:
        .. code-block:: bash

            pip install langchain-community

    Instantiation:
        .. code-block:: python

            from langchain_community.tools.rustchain import ListBounties
            from langchain_community.utilities.rustchain import RustChainAPIWrapper

            api = RustChainAPIWrapper()
            tool = ListBounties(api_wrapper=api)

    Invocation:
        .. code-block:: python

            tool.invoke({"limit": 5, "status": "open"})
            # → JSON list of bounty dicts
    """

    name: str = "list_rustchain_bounties"
    description: str = (
        "List bounties available on RustChain for contributors to earn RTC tokens. "
        "Use this to discover open bounties in categories: "
        "docs, code, content, integrations, security, and more. "
        "Input is optional: limit (default 10) and status ('open'/'closed'/'all')."
    )
    args_schema: Type[BaseModel] = ListBountiesInput
    api_wrapper: RustChainAPIWrapper

    def _run(
        self,
        limit: int = 10,
        status: str = "open",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        import json
        bounties = self.api_wrapper.list_bounties(limit=limit, status=status)
        return json.dumps(bounties, indent=2)


class GetNodeHealth(BaseTool):
    """Check if the RustChain node is healthy and online.

    Use this tool to verify the RustChain node is reachable before
    performing other operations, or to get node metadata (version, uptime).

    Instantiation:
        .. code-block:: python

            from langchain_community.tools.rustchain import GetNodeHealth
            from langchain_community.utilities.rustchain import RustChainAPIWrapper

            api = RustChainAPIWrapper()
            tool = GetNodeHealth(api_wrapper=api)

    Invocation:
        .. code-block:: python

            tool.invoke({})
            # → {"ok": true, "version": "2.2.1-rip200", "uptime_s": 15358, ...}
    """

    name: str = "get_rustchain_node_health"
    description: str = (
        "Check if the RustChain blockchain node is healthy and online. "
        "Returns node version, uptime, and health status. "
        "Use this to verify the node is reachable before other operations. "
        "No input required."
    )
    args_schema: Type[BaseModel] = GetNodeHealthInput
    api_wrapper: RustChainAPIWrapper

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        import json
        result = self.api_wrapper.get_node_health()
        return json.dumps(result, indent=2)


class RustChainRun(BaseTool):
    """Run a natural-language query against RustChain.

    This is a convenience tool that parses natural language and dispatches
    to the right RustChain API method.

    Supports queries like:
    - "balance of alice"
    - "list bounties"
    - "node health"

    Instantiation:
        .. code-block:: python

            from langchain_community.tools.rustchain import RustChainRun
            from langchain_community.utilities.rustchain import RustChainAPIWrapper

            api = RustChainAPIWrapper()
            tool = RustChainRun(api_wrapper=api)

    Invocation:
        .. code-block:: python

            tool.invoke("what is the node health?")
    """

    name: str = "rustchain"
    description: str = (
        "Run a natural-language query against RustChain. "
        "Supports: checking wallet balance, listing bounties, "
        "checking node health, and sending RTC. "
        "Example: 'balance of alice', 'list bounties', 'node health'."
    )
    api_wrapper: RustChainAPIWrapper

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return self.api_wrapper.run(query)
