# FixWise

Know what's worth fixing — before you pay for it.

A consumer decision-support web app: you describe a laptop problem and what a technician
quoted you, and FixWise tells you the likely issue, a fair price range, and whether repairing
or replacing makes more sense — before you've paid anyone.

This matches the project plan's tech stack and architecture:

| Layer | Technology | Used for |
|---|---|---|
| Frontend | HTML + CSS (Jinja templates) | Form, results, history pages |
| Backend | Python + Flask | Routes and application logic |
| Database | SQLite | Repair-cost dataset and saved reports |
| AI | Anthropic API (Claude), with a keyword fallback | Reads the free-text problem and picks a category |
| Decision logic | Plain Python | Quote check and repair-vs-replace rules |
| Testing | pytest | Covers the decision engine |

## Setup

```bash
cd fixwise
python -m venv venv
source venv/bin/activate        # on Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py               # creates data/fixwise.db and loads the cost dataset
python app.py                   # runs at http://127.0.0.1:5000
```

## Setting up real AI (recommended)

Without an API key, the app still runs end-to-end using a simple keyword matcher in
`ai_layer.py` — good for grading the architecture, but it won't understand descriptions
that don't contain an obvious keyword. To get real language understanding:

1. Get an API key from https://console.anthropic.com
2. Copy `.env.example` to a new file named `.env` in the `fixwise` folder
3. Open `.env` and replace `your-key-here` with your real key:
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
   ```
4. Restart `python app.py` — it loads the key automatically on startup

`.env` is already listed in `.gitignore` so the key never accidentally gets committed
or shared. If you'd rather set it as an environment variable instead of a `.env` file:

```powershell
# Windows PowerShell (only lasts for the current terminal session)
$env:ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxxxx"
```

```bash
# Mac/Linux
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

## Run the tests

```bash
pytest
```

## How a request flows through the app

```
User → Flask route (/analyze) → AI layer picks a category
     → decision_engine looks up the cost range for that category (SQLite)
     → decision_engine checks the quote and decides repair / replace / inspect
     → result.html renders the full report
     → the report is saved to the reports table for the Repair Passport page
```

## The one rule the whole design follows

**The AI is only allowed to classify the problem. It never sets or influences a price.**
All pricing and the repair-vs-replace call come from `decision_engine.py` and the
`repair_costs` table — plain, readable rules anyone can check. This matters because it's
what makes the tool trustworthy: if the AI could quietly shift a number, there'd be no way
to tell whether it was reasoning or just producing something plausible-sounding.

## Known limitations (stated honestly, not hidden)

- The repair-cost dataset (`data/repair_costs.csv`) is a small starting set of eight
  categories, not real collected repair data. A production version needs an actual dataset
  built from real repair outcomes.
- The AI layer, without an API key, falls back to basic keyword matching — good enough to
  demo the architecture, not good enough to trust for real classification.
- `replacement_value` currently defaults to a flat ₹35,000 if the user doesn't provide one;
  a real version would look this up by laptop brand/model instead of guessing.

## Ethics and safety rules built into the logic

- Every diagnosis carries an explicit confidence level — never a false claim of certainty.
- `liquid_damage` and `motherboard_power` categories, and any `Low`-confidence result, are
  always routed to "get a professional inspection" rather than a final repair/replace answer.
- If technicians ever pay for leads through a future version of this platform, that payment
  must never be allowed to influence the diagnosis or the quote check — the two need to stay
  structurally separate, or the product loses the only reason anyone would trust it.
- Prices are always shown as ranges, never as guarantees.

## Suggested team split (from the project plan)

| Role | Work |
|---|---|
| Backend | Flask routes, database, decision engine |
| Frontend | Templates, styling, responsive layout |
| AI/Data | Prompt design, category list, repair-cost dataset and validation |
| Testing/Research | Test cases, real price research, documentation |

## Future expansion

Phones, washing machines, ACs and other repairable products, using the same architecture —
only the `repair_costs` dataset and category list need to grow, since the AI layer and
decision engine are already written to be category-driven rather than laptop-specific.
