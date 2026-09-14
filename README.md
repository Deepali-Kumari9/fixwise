# FixWise

### Know what your repair is really worth.

FixWise is an AI-powered consumer repair decision platform that helps people make better repair decisions before paying a technician.

Instead of simply finding a repair shop, FixWise gives the consumer an independent starting point:

- Likely problem category
- Estimated repair cost range
- Repairability score
- Repair vs replace recommendation
- Technician questions to ask
- Technician quote analysis
- Safety/inspection warnings for uncertain or risky cases

## The Problem

Repair decisions are often based on incomplete information.

Consumers may not know:

- What is actually wrong with their device
- Whether a quoted price is reasonable
- Whether repairing is better than replacing
- What questions to ask a technician
- Whether the issue requires physical inspection

This creates an information gap between consumers and repair providers.

## The Solution

FixWise acts as a consumer-side decision layer before repair.

The user provides:

1. Device type
2. Brand and model
3. Device age
4. Problem description
5. Optional photo
6. Optional technician quote
7. Optional replacement-device price

FixWise then produces an explainable repair report.

## How It Works

```text
User Input
    ↓
AI Problem Classification
    ↓
Structured Repair-Cost Dataset
    ↓
Transparent Decision Engine
    ↓
Repair / Replace / Inspect Recommendation
    ↓
FixWise Report
```

The AI does not decide the repair price.

The AI classifies the problem into a known category. Repair-cost estimates come from a separate structured dataset, while repair-vs-replace decisions use transparent rules.

## Technology

- Python
- Flask
- SQLite
- Gemini API
- Anthropic API (optional fallback)
- REST API requests
- HTML / CSS
- Jinja Templates
- Pytest

## AI Layer

FixWise currently tries Gemini first for problem classification.

If Gemini is unavailable or fails, the system can use Anthropic when configured. If no AI API is available, FixWise falls back to keyword-based classification so the application can still run.

The AI layer returns:

- Problem category
- Confidence level
- Safety flag
- Short explanation

Supported categories include:

- Battery
- Overheating
- Screen
- Motherboard / Power
- Keyboard
- Storage / RAM
- Liquid Damage
- Charging
- Power
- Other

## Explainability

FixWise intentionally separates AI interpretation from financial decision-making.

- **AI** → Interprets the user's description
- **Repair-cost dataset** → Provides the estimated cost range
- **Decision engine** → Evaluates quote and repair-vs-replace logic

This makes the system easier to understand, test and improve.

## Safety

FixWise does not claim to provide a definitive physical diagnosis.

Low-confidence, liquid-damage, motherboard/power and potentially hazardous cases can be directed toward physical inspection.

The application is intended as a decision-support tool, not a replacement for a qualified technician.

## Project Structure

```text
fixwise/
├── ai_layer.py
├── app.py
├── decision_engine.py
├── init_db.py
├── requirements.txt
├── data/
│   └── repair_costs.csv
├── static/
│   └── style.css
├── templates/
│   ├── base.html
│   ├── history.html
│   ├── index.html
│   └── result.html
└── tests/
    └── test_decision_engine.py
```

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-anthropic-key
```

API keys are intentionally excluded from Git using `.gitignore`.

An example configuration is available in `.env.example`.

### 4. Initialize the database

```bash
python init_db.py
```

### 5. Run the application

```bash
python app.py
```

Then open:

http://127.0.0.1:5000


## Testing

Run:

```bash
pytest -q
```

The decision engine currently has automated tests covering:

- Repair-cost lookup
- Unknown-category fallback
- Missing quotes
- High and low quotes
- Fair quotes
- Safety-based inspection
- Repair decisions
- Replacement decisions

## Current Scope

The MVP currently supports:

- Laptops
- Phones
- Tablets
- TVs
- Monitors

The repair-cost dataset is an initial structured dataset for the prototype and should be expanded and validated with real repair-market data before production use.

## Future Development

- Model-specific repair pricing
- Larger repair-case dataset
- Improved image understanding
- More device categories
- Verified technician ecosystem
- Warranty and spare-part information
- Predictive maintenance
- Refurbishment and resale support
- Repair Passport expansion

## Vision

People should not have to blindly trust a repair quote because they lack the information to question it.

FixWise aims to give consumers that missing decision layer.