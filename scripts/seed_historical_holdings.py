"""
Seed historical holdings with effective_date = 2022-01-01
so that past investigation dates work.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal, create_tables
from app.models.security import Security
from app.models.holding import ETFHolding
from datetime import date

create_tables()
db = SessionLocal()

# Use same holdings data but with historical effective date
HISTORICAL_DATE = date(2022, 1, 1)

holdings_data = {
    "SPY": [
        ("AAPL", 7.12), ("MSFT", 6.41), ("NVDA", 5.98), ("AMZN", 3.89),
        ("META", 2.71), ("GOOGL", 2.10), ("GOOG", 1.77), ("BRK-B", 1.67),
        ("LLY", 1.56), ("AVGO", 1.54), ("JPM", 1.47), ("TSLA", 1.35),
        ("UNH", 1.21), ("XOM", 1.18), ("V", 1.05), ("MA", 0.93),
        ("COST", 0.89), ("HD", 0.85), ("PG", 0.82), ("NFLX", 0.79),
    ],
    "QQQ": [
        ("AAPL", 9.21), ("MSFT", 8.37), ("NVDA", 8.02), ("AMZN", 5.24),
        ("META", 4.89), ("AVGO", 4.12), ("TSLA", 3.45), ("GOOGL", 2.98),
        ("GOOG", 2.71), ("COST", 2.45), ("NFLX", 2.31), ("AMD", 1.98),
        ("ADBE", 1.67), ("QCOM", 1.54), ("INTC", 1.23), ("TXN", 1.18),
        ("INTU", 1.12), ("AMAT", 1.08), ("MU", 0.98), ("LRCX", 0.91),
    ],
    "SMH": [
        ("NVDA", 20.12), ("TSM", 14.23), ("AVGO", 7.89), ("ASML", 5.67),
        ("AMD", 5.34), ("QCOM", 4.98), ("AMAT", 4.45), ("TXN", 4.12),
        ("LRCX", 3.78), ("MU", 3.45), ("KLAC", 3.21), ("INTC", 2.98),
        ("MRVL", 2.67), ("NXPI", 2.45), ("MPWR", 2.12), ("MCHP", 1.98),
        ("ON", 1.78), ("STM", 1.56), ("ENTG", 1.34), ("WOLF", 1.12),
    ],
}

for etf_ticker, holdings in holdings_data.items():
    total_weight = sum(w for _, w in holdings)
    covered_weight = round(total_weight / 100, 6)

    for ticker, weight_pct in holdings:
        holding_id = f"{etf_ticker}|{ticker}|{HISTORICAL_DATE}"
        existing = db.query(ETFHolding).filter(ETFHolding.id == holding_id).first()
        if not existing:
            h = ETFHolding(
                id=holding_id,
                etf_ticker=etf_ticker,
                security_ticker=ticker,
                weight=round(weight_pct / 100, 6),
                effective_date=HISTORICAL_DATE,
                covered_weight=covered_weight,
                source="manual_seed_historical",
            )
            db.add(h)

    db.commit()
    print(f"{etf_ticker}: historical holdings seeded for {HISTORICAL_DATE}")

db.close()
print("Done.")
