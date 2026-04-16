from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional
import asyncio

mcp = FastMCP("BuyMeaCoffee")

BASE_URL = "https://developers.buymeacoffee.com/api/v1"
DEFAULT_TOKEN = os.environ.get("BMC_ACCESS_TOKEN", "")


def get_token(access_token: str) -> str:
    """Return the provided token or fall back to the environment variable."""
    if access_token and access_token.strip():
        return access_token.strip()
    if DEFAULT_TOKEN:
        return DEFAULT_TOKEN
    raise ValueError("No BMC access token provided. Set BMC_ACCESS_TOKEN env var or pass access_token parameter.")


async def bmc_get(path: str, token: str, params: Optional[dict] = None) -> dict:
    """Perform an authenticated GET request against the BMC API."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_supporters(access_token: str = "", page: int = 1) -> dict:
    """Retrieves a paginated list of supporters from Buy Me a Coffee. Use this when the user wants to see who has supported them, browse all supporters, or get supporter counts. Supports pagination via page number."""
    token = get_token(access_token)
    params = {"page": page}
    return await bmc_get("supporters", token, params)


@mcp.tool()
async def get_supporter(id: int, access_token: str = "") -> dict:
    """Retrieves detailed information about a single specific supporter by their unique ID. Use this when the user wants to look up a particular supporter's details such as name, email, amount, or message."""
    token = get_token(access_token)
    return await bmc_get(f"supporters/{id}", token)


@mcp.tool()
async def get_subscriptions(access_token: str = "", page: int = 1, status: str = "all") -> dict:
    """Retrieves a paginated list of subscriptions from Buy Me a Coffee, optionally filtered by status. Use this when the user wants to view their recurring supporters/members, check active or inactive subscriptions, or get an overview of their membership revenue. Status values: 'active', 'inactive', or 'all'."""
    token = get_token(access_token)
    params: dict = {"page": page}
    if status and status != "all":
        params["status"] = status
    return await bmc_get("subscriptions", token, params)


@mcp.tool()
async def get_subscription(id: int, access_token: str = "") -> dict:
    """Retrieves detailed information about a single specific subscription by its unique ID. Use this when the user needs to inspect a particular subscription's billing details, status, or subscriber information."""
    token = get_token(access_token)
    return await bmc_get(f"subscriptions/{id}", token)


@mcp.tool()
async def get_extras(access_token: str = "", page: int = 1) -> dict:
    """Retrieves a paginated list of extra purchases (shop items / digital products sold via Buy Me a Coffee extras). Use this when the user wants to see what extras have been purchased, review extra sales, or audit product purchases."""
    token = get_token(access_token)
    params = {"page": page}
    return await bmc_get("extras", token, params)


@mcp.tool()
async def get_extra(id: int, access_token: str = "") -> dict:
    """Retrieves detailed information about a single specific extra purchase by its unique ID. Use this to look up a particular digital product or shop item purchase, including buyer info and purchase details."""
    token = get_token(access_token)
    return await bmc_get(f"extras/{id}", token)


@mcp.tool()
async def summarize_account(access_token: str = "") -> dict:
    """Fetches and aggregates a high-level summary of the Buy Me a Coffee account by pulling the first page of supporters, active subscriptions, and extras simultaneously. Use this when the user asks for an overview, dashboard summary, or general account stats without specifying a specific resource."""
    token = get_token(access_token)

    supporters_task = bmc_get("supporters", token, {"page": 1})
    subscriptions_task = bmc_get("subscriptions", token, {"page": 1, "status": "active"})
    extras_task = bmc_get("extras", token, {"page": 1})

    results = await asyncio.gather(
        supporters_task,
        subscriptions_task,
        extras_task,
        return_exceptions=True,
    )

    supporters_result, subscriptions_result, extras_result = results

    def safe_result(result):
        if isinstance(result, Exception):
            return {"error": str(result)}
        return result

    supporters_data = safe_result(supporters_result)
    subscriptions_data = safe_result(subscriptions_result)
    extras_data = safe_result(extras_result)

    summary = {
        "supporters": {
            "data": supporters_data,
            "total": supporters_data.get("total") if isinstance(supporters_data, dict) else None,
            "current_page": supporters_data.get("current_page") if isinstance(supporters_data, dict) else None,
            "last_page": supporters_data.get("last_page") if isinstance(supporters_data, dict) else None,
        },
        "active_subscriptions": {
            "data": subscriptions_data,
            "total": subscriptions_data.get("total") if isinstance(subscriptions_data, dict) else None,
            "current_page": subscriptions_data.get("current_page") if isinstance(subscriptions_data, dict) else None,
            "last_page": subscriptions_data.get("last_page") if isinstance(subscriptions_data, dict) else None,
        },
        "extras": {
            "data": extras_data,
            "total": extras_data.get("total") if isinstance(extras_data, dict) else None,
            "current_page": extras_data.get("current_page") if isinstance(extras_data, dict) else None,
            "last_page": extras_data.get("last_page") if isinstance(extras_data, dict) else None,
        },
    }

    return summary




_SERVER_SLUG = "warengonzaga-buymeacoffee-js"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

sse_app = mcp.http_app(transport="sse")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", sse_app),
    ],
    lifespan=sse_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
