# StockPut Analyzer

StockPut Analyzer is a beginner-focused cash-secured put calculator. It includes the existing command-line analyzer and a Streamlit browser interface for manual trade analysis.

The application is educational. It does not select trades, execute orders, connect to a brokerage, or provide a guarantee or recommendation.

## Windows Setup

Open PowerShell in this folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in the same PowerShell window, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Launch The Browser App

With the virtual environment active, run:

```powershell
streamlit run app.py
```

Streamlit will print a local URL. Open that URL in a browser.

The Phase 1 browser interface uses manual trade inputs and can optionally retrieve market data for the ticker. If retrieval fails, enter the manual market values and analyze the trade without live data.

## Run The Command-Line Calculator

```powershell
py put_calculator.py
```

The command-line workflow remains available and uses the existing market-data, option-chain, fallback, scoring, assignment, sizing, guardrail, and expiration-analysis behavior.

## Run Tests

```powershell
py -m unittest discover
```

The repository also includes `pytest` in `requirements.txt` for future test tooling, but the current regression suite uses Python's built-in `unittest` runner.
