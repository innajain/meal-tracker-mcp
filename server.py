import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from auth import SimpleOAuthProvider

AUTH_PROVIDER = SimpleOAuthProvider()

mcp = FastMCP(
    "meal-tracker",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
    ),
    auth_server_provider=AUTH_PROVIDER,
    auth=AuthSettings(
        issuer_url="https://meal-tracker-mcp.onrender.com",
        resource_server_url="https://meal-tracker-mcp.onrender.com",
    ),
)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
MEALS_FILE = DATA_DIR / "meals.json"

PEOPLE = ["shreyansh", "pankaj", "aviral"]
MEAL_TYPES = ["lunch", "dinner"]
COST_PER_MEAL = 80  # ₹80 per meal


def load_meals() -> dict:
    if MEALS_FILE.exists():
        with open(MEALS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_meals(data: dict):
    with open(MEALS_FILE, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def parse_date(date_str: str) -> str:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or DD/MM/YYYY")


@mcp.tool()
def add_meal(
    date_str: str,
    person: str,
    meal_type: str,
    count: int = 1,
) -> str:
    """Add meal(s) for a person on a given date.

    Args:
        date_str: Date in YYYY-MM-DD or DD/MM/YYYY format
        person: Name - 'shreyansh', 'pankaj', or 'aviral'
        meal_type: 'lunch' or 'dinner'
        count: Number of meals (default 1)
    """
    person = person.lower().strip()
    meal_type = meal_type.lower().strip()

    if person not in PEOPLE:
        return f"Invalid person. Choose from: {', '.join(PEOPLE)}"
    if meal_type not in MEAL_TYPES:
        return f"Invalid meal type. Choose from: {', '.join(MEAL_TYPES)}"
    if count < 0:
        return "Count cannot be negative"

    date_key = parse_date(date_str)
    meals = load_meals()
    if date_key not in meals:
        meals[date_key] = {}
    meals[date_key][f"{meal_type}_{person}"] = count
    save_meals(meals)
    return f"Set {meal_type} for {person} on {date_key} to {count} meal(s)"


@mcp.tool()
def get_meals(
    date_str: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Get meal data. Provide a single date, or a date range, or leave all blank for all data.

    Args:
        date_str: Single date (YYYY-MM-DD or DD/MM/YYYY)
        start_date: Range start
        end_date: Range end
    """
    meals = load_meals()
    if not meals:
        return "No meal data found."

    if date_str:
        dk = parse_date(date_str)
        if dk in meals:
            return _format_day(dk, meals[dk])
        return f"No meals recorded for {dk}"

    if start_date and end_date:
        sd = parse_date(start_date)
        ed = parse_date(end_date)
        filtered = {k: v for k, v in meals.items() if sd <= k <= ed}
    else:
        filtered = meals

    if not filtered:
        return "No meals found in the given range."

    lines = []
    for dk in sorted(filtered.keys()):
        lines.append(_format_day(dk, filtered[dk]))
    return "\n\n".join(lines)


@mcp.tool()
def delete_meal(date_str: str, person: str, meal_type: str) -> str:
    """Delete a meal entry for a person on a given date.

    Args:
        date_str: Date in YYYY-MM-DD or DD/MM/YYYY format
        person: Name - 'shreyansh', 'pankaj', or 'aviral'
        meal_type: 'lunch' or 'dinner'
    """
    person = person.lower().strip()
    meal_type = meal_type.lower().strip()
    date_key = parse_date(date_str)
    meals = load_meals()

    key = f"{meal_type}_{person}"
    if date_key in meals and key in meals[date_key]:
        del meals[date_key][key]
        if not meals[date_key]:
            del meals[date_key]
        save_meals(meals)
        return f"Deleted {meal_type} for {person} on {date_key}"
    return f"No entry found for {meal_type} {person} on {date_key}"


@mcp.tool()
def get_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Get a summary of meals and costs per person for a date range (or all time).

    Args:
        start_date: Range start (optional)
        end_date: Range end (optional)
    """
    meals = load_meals()
    if not meals:
        return "No meal data found."

    if start_date and end_date:
        sd = parse_date(start_date)
        ed = parse_date(end_date)
        filtered = {k: v for k, v in meals.items() if sd <= k <= ed}
    else:
        filtered = meals
        sd = min(meals.keys()) if meals else ""
        ed = max(meals.keys()) if meals else ""

    totals = {p: 0 for p in PEOPLE}
    lunch_totals = {p: 0 for p in PEOPLE}
    dinner_totals = {p: 0 for p in PEOPLE}

    for day_data in filtered.values():
        for p in PEOPLE:
            l = day_data.get(f"lunch_{p}", 0)
            d = day_data.get(f"dinner_{p}", 0)
            lunch_totals[p] += l
            dinner_totals[p] += d
            totals[p] += l + d

    grand_total = sum(totals.values())
    grand_cost = grand_total * COST_PER_MEAL

    lines = [f"Meal Summary ({sd} to {ed})"]
    lines.append(f"{'Person':<15} {'Lunch':>6} {'Dinner':>7} {'Total':>6} {'Cost':>10}")
    lines.append("-" * 50)
    for p in PEOPLE:
        cost = totals[p] * COST_PER_MEAL
        lines.append(
            f"{p.title():<15} {lunch_totals[p]:>6} {dinner_totals[p]:>7} {totals[p]:>6} ₹{cost:>8,.0f}"
        )
    lines.append("-" * 50)
    lines.append(f"{'TOTAL':<15} {sum(lunch_totals.values()):>6} {sum(dinner_totals.values()):>7} {grand_total:>6} ₹{grand_cost:>8,.0f}")

    return "\n".join(lines)


@mcp.tool()
def get_day_totals(date_str: str) -> str:
    """Get totals for a specific day.

    Args:
        date_str: Date in YYYY-MM-DD or DD/MM/YYYY format
    """
    meals = load_meals()
    dk = parse_date(date_str)
    if dk not in meals:
        return f"No meals recorded for {dk}"

    day = meals[dk]
    total = sum(day.values())
    cost = total * COST_PER_MEAL
    lines = [f"Meals on {dk} (total: {total}, cost: ₹{cost})"]
    for p in PEOPLE:
        l = day.get(f"lunch_{p}", 0)
        d = day.get(f"dinner_{p}", 0)
        lines.append(f"  {p.title():<15} lunch={l} dinner={d} total={l+d}")
    return "\n".join(lines)


def _format_day(date_key: str, day_data: dict) -> str:
    total = sum(day_data.values())
    cost = total * COST_PER_MEAL
    lines = [f"{date_key} (total: {total}, cost: ₹{cost})"]
    for p in PEOPLE:
        l = day_data.get(f"lunch_{p}", 0)
        d = day_data.get(f"dinner_{p}", 0)
        if l or d:
            lines.append(f"  {p.title():<15} lunch={l} dinner={d}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from starlette.responses import JSONResponse
    from starlette.types import ASGIApp, Receive, Scope, Send

    class OAuthDiscoveryMiddleware:
        """Adds /.well-known/oauth-authorization-server/mcp for ChatGPT."""
        def __init__(self, app: ASGIApp):
            self.app = app
            self.metadata = {
                "issuer": "https://meal-tracker-mcp.onrender.com",
                "authorization_endpoint": "https://meal-tracker-mcp.onrender.com/authorize",
                "token_endpoint": "https://meal-tracker-mcp.onrender.com/token",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
                "code_challenge_methods_supported": ["S256"],
            }

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] == "http" and scope["path"] == "/.well-known/oauth-authorization-server/mcp":
                response = JSONResponse(self.metadata)
                await response(scope, receive, send)
            else:
                await self.app(scope, receive, send)

    transport = "stdio"
    if "--http" in sys.argv:
        transport = "streamable-http"

    if transport == "streamable-http":
        starlette_app = mcp.streamable_http_app()
        wrapped = OAuthDiscoveryMiddleware(starlette_app)
        import uvicorn
        uvicorn.run(
            wrapped,
            host=mcp.settings.host,
            port=mcp.settings.port,
        )
    else:
        mcp.run(transport="stdio")
