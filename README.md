# Meal Tracker MCP Server

MCP server to track meals for Shreyansh, Pankaj, and Aviral. Deploy on Render and connect to ChatGPT.

## Setup

```bash
pip install -r requirements.txt
python seed_data.py
```

## Run locally (stdio)

```bash
python server.py
```

## Run locally (HTTP)

```bash
python server.py --http
```

Server runs at `http://localhost:8000/mcp`

## Deploy to Render

1. Push to GitHub
2. Connect repo on Render (it auto-detects `render.yaml`)
3. Render generates `MCP_API_TOKEN` automatically
4. Copy the service URL (e.g. `https://meal-tracker-mcp.onrender.com/mcp`)

## Connect to ChatGPT

1. Go to ChatGPT > Settings > Connectors (or Apps)
2. Add a custom connector:
   - URL: `https://meal-tracker-mcp.onrender.com/mcp`
   - Auth: Bearer token (use the `MCP_API_TOKEN` from Render dashboard)

## Tools

| Tool | Description |
|------|-------------|
| `add_meal` | Add meals for a person (date, person, lunch/dinner, count) |
| `delete_meal` | Remove a meal entry |
| `get_meals` | Fetch meals for a date or range |
| `get_day_totals` | Totals for a specific day |
| `get_summary` | Per-person summary with costs |

## Cost

₹80 per meal. Totals auto-calculated.
