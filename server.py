from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

mcp = FastMCP("BuyMeaCoffee")

BASE_URL = "https://developers.buymeacoffee.com/api/v1"
DEFAULT_TOKEN = os.environ.get("BMC_ACCESS_TOKEN", "")


def get_token(access_token: str) -> str:
    """Return provided token or fall back to environment variable."""
    token = access_token.strip() if access_token else ""
    if not token:
        token = DEFAULT_TOKEN
    if not token:
        raise ValueError("No BMC access token provided. Set BMC_ACCESS_TOKEN env var or pass access_token parameter.")
    return token


@mcp.tool()
async def get_supporters(access_token: str, page: Optional[int] = None) -> dict:
    """Retrieves a paginated list of supporters from Buy Me a Coffee. Use this when the user wants to see who has supported them, get a list of all supporters, or browse through supporter pages."""
    token = get_token(access_token)
    params = {}
    if page is not None:
        params["page"] = page

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/supporters",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_supporter(access_token: str, id: int) -> dict:
    """Retrieves detailed information about a single supporter by their unique ID. Use this when the user wants to look up a specific supporter's details."""
    token = get_token(access_token)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/supporters/{id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_subscriptions(
    access_token: str,
    page: Optional[int] = None,
    status: Optional[str] = None,
) -> dict:
    """Retrieves a paginated list of subscriptions from Buy Me a Coffee, optionally filtered by status. Use this when the user wants to see their recurring subscribers, check active or inactive memberships, or browse all subscriptions."""
    token = get_token(access_token)
    params = {}
    if page is not None:
        params["page"] = page
    if status is not None:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_subscription(access_token: str, id: int) -> dict:
    """Retrieves detailed information about a single subscription by its unique ID. Use this when the user wants to look up the details of a specific subscription."""
    token = get_token(access_token)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/subscriptions/{id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_extras(access_token: str, page: Optional[int] = None) -> dict:
    """Retrieves a paginated list of extra purchases (shop items or extras) from Buy Me a Coffee. Use this when the user wants to see purchases of their extras or digital products."""
    token = get_token(access_token)
    params = {}
    if page is not None:
        params["page"] = page

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/extras",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_extra(access_token: str, id: int) -> dict:
    """Retrieves detailed information about a single extra purchase by its unique ID. Use this when the user wants to look up a specific extra or digital product purchase."""
    token = get_token(access_token)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/extras/{id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()




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
