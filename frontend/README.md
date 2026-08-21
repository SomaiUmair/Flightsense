# FlightSense frontend

A minimal, dependency-free starting point for the FlightSense UI — one
`index.html` with inline CSS and vanilla JavaScript. No framework and no build
step, so it's easy to read, run, and grow into whatever you like (React, Vue,
Svelte, …) later.

## Run it

The backend must be running first (from the repo root):

```bash
uvicorn backend.main:app --reload   # serves the API at http://localhost:8000
```

Then open the frontend. Because it calls the API with `fetch`, serve it over
HTTP rather than opening the file directly (avoids browser file:// CORS quirks):

```bash
# from the frontend/ folder
python -m http.server 5500
# then visit http://localhost:5500
```

If your backend runs somewhere else, change the **Backend API URL** box at the
bottom of the page — no code edit needed.

## What it does

Wraps the three backend endpoints:

| UI action              | Endpoint                                                        |
| ---------------------- | -------------------------------------------------------------- |
| "Should I book?"       | `GET /predict/{origin}/{destination}?departure_date=…`         |
| "Show price history"   | `GET /prices/{origin}/{destination}?departure_date=…`          |
| _(not wired up yet)_   | `GET /prices/{origin}/{destination}/cheapest?departure_date=…` |

## Where to continue

Everything is in `index.html`, split into clearly labelled sections:

- **`<style>`** — all styling (with light/dark support).
- **`api.*`** — one small function per endpoint. The `cheapest` one is stubbed
  in the comments; wiring a button to it is a good first task.
- **event wiring** (bottom of `<script>`) — form submit and button handlers.

Good next steps: add the "cheapest fare" button, chart the price history,
validate airport codes, or migrate to a framework once the shape feels right.
