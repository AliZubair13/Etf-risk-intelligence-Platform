import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal, create_tables
from app.models.etf import ETF
from app.models.security import Security
from app.models.holding import ETFHolding
from datetime import date

create_tables()
db = SessionLocal()

etfs = [
    ETF(ticker="SPY", name="SPDR S&P 500 ETF Trust", category="Broad Market", benchmark_ticker=None, issuer="State Street"),
    ETF(ticker="QQQ", name="Invesco QQQ Trust", category="Technology", benchmark_ticker="SPY", issuer="Invesco"),
    ETF(ticker="SMH", name="VanEck Semiconductor ETF", category="Semiconductors", benchmark_ticker="QQQ", issuer="VanEck"),
]

for etf in etfs:
    existing = db.query(ETF).filter(ETF.ticker == etf.ticker).first()
    if not existing:
        db.add(etf)
        print(f"Added ETF: {etf.ticker}")
    else:
        print(f"Already exists: {etf.ticker}")

db.commit()

holdings_data = {
    "SPY": [
        ("AAPL", "Apple Inc", "Technology", "Technology Hardware", 7.12),
        ("MSFT", "Microsoft Corp", "Technology", "Systems Software", 6.41),
        ("NVDA", "NVIDIA Corp", "Technology", "Semiconductors", 5.98),
        ("AMZN", "Amazon.com Inc", "Consumer Discretionary", "Broadline Retail", 3.89),
        ("META", "Meta Platforms Inc", "Communication Services", "Interactive Media", 2.71),
        ("GOOGL", "Alphabet Inc Class A", "Communication Services", "Interactive Media", 2.10),
        ("GOOG", "Alphabet Inc Class C", "Communication Services", "Interactive Media", 1.77),
        ("BRK-B", "Berkshire Hathaway Inc", "Financials", "Multi-line Insurance", 1.67),
        ("LLY", "Eli Lilly and Co", "Health Care", "Pharmaceuticals", 1.56),
        ("AVGO", "Broadcom Inc", "Technology", "Semiconductors", 1.54),
        ("JPM", "JPMorgan Chase and Co", "Financials", "Diversified Banks", 1.47),
        ("TSLA", "Tesla Inc", "Consumer Discretionary", "Automobile Manufacturers", 1.35),
        ("UNH", "UnitedHealth Group Inc", "Health Care", "Managed Health Care", 1.21),
        ("XOM", "Exxon Mobil Corp", "Energy", "Integrated Oil and Gas", 1.18),
        ("V", "Visa Inc", "Financials", "Transaction and Payment Processing", 1.05),
        ("MA", "Mastercard Inc", "Financials", "Transaction and Payment Processing", 0.93),
        ("COST", "Costco Wholesale Corp", "Consumer Staples", "Consumer Staples Merchandise Retail", 0.89),
        ("HD", "Home Depot Inc", "Consumer Discretionary", "Home Improvement Retail", 0.85),
        ("PG", "Procter and Gamble Co", "Consumer Staples", "Personal Care Products", 0.82),
        ("NFLX", "Netflix Inc", "Communication Services", "Movies and Entertainment", 0.79),
    ],
    "QQQ": [
        ("AAPL", "Apple Inc", "Technology", "Technology Hardware", 9.21),
        ("MSFT", "Microsoft Corp", "Technology", "Systems Software", 8.37),
        ("NVDA", "NVIDIA Corp", "Technology", "Semiconductors", 8.02),
        ("AMZN", "Amazon.com Inc", "Consumer Discretionary", "Broadline Retail", 5.24),
        ("META", "Meta Platforms Inc", "Communication Services", "Interactive Media", 4.89),
        ("AVGO", "Broadcom Inc", "Technology", "Semiconductors", 4.12),
        ("TSLA", "Tesla Inc", "Consumer Discretionary", "Automobile Manufacturers", 3.45),
        ("GOOGL", "Alphabet Inc Class A", "Communication Services", "Interactive Media", 2.98),
        ("GOOG", "Alphabet Inc Class C", "Communication Services", "Interactive Media", 2.71),
        ("COST", "Costco Wholesale Corp", "Consumer Staples", "Consumer Staples Merchandise Retail", 2.45),
        ("NFLX", "Netflix Inc", "Communication Services", "Movies and Entertainment", 2.31),
        ("AMD", "Advanced Micro Devices", "Technology", "Semiconductors", 1.98),
        ("ADBE", "Adobe Inc", "Technology", "Application Software", 1.67),
        ("QCOM", "Qualcomm Inc", "Technology", "Semiconductors", 1.54),
        ("INTC", "Intel Corp", "Technology", "Semiconductors", 1.23),
        ("TXN", "Texas Instruments Inc", "Technology", "Semiconductors", 1.18),
        ("INTU", "Intuit Inc", "Technology", "Application Software", 1.12),
        ("AMAT", "Applied Materials Inc", "Technology", "Semiconductor Equipment", 1.08),
        ("MU", "Micron Technology Inc", "Technology", "Semiconductors", 0.98),
        ("LRCX", "Lam Research Corp", "Technology", "Semiconductor Equipment", 0.91),
    ],
    "SMH": [
        ("NVDA", "NVIDIA Corp", "Technology", "Semiconductors", 20.12),
        ("TSM", "Taiwan Semiconductor ADR", "Technology", "Semiconductors", 14.23),
        ("AVGO", "Broadcom Inc", "Technology", "Semiconductors", 7.89),
        ("ASML", "ASML Holding ADR", "Technology", "Semiconductor Equipment", 5.67),
        ("AMD", "Advanced Micro Devices", "Technology", "Semiconductors", 5.34),
        ("QCOM", "Qualcomm Inc", "Technology", "Semiconductors", 4.98),
        ("AMAT", "Applied Materials Inc", "Technology", "Semiconductor Equipment", 4.45),
        ("TXN", "Texas Instruments Inc", "Technology", "Semiconductors", 4.12),
        ("LRCX", "Lam Research Corp", "Technology", "Semiconductor Equipment", 3.78),
        ("MU", "Micron Technology Inc", "Technology", "Semiconductors", 3.45),
        ("KLAC", "KLA Corp", "Technology", "Semiconductor Equipment", 3.21),
        ("INTC", "Intel Corp", "Technology", "Semiconductors", 2.98),
        ("MRVL", "Marvell Technology Inc", "Technology", "Semiconductors", 2.67),
        ("NXPI", "NXP Semiconductors", "Technology", "Semiconductors", 2.45),
        ("MPWR", "Monolithic Power Systems", "Technology", "Semiconductors", 2.12),
        ("MCHP", "Microchip Technology Inc", "Technology", "Semiconductors", 1.98),
        ("ON", "ON Semiconductor Corp", "Technology", "Semiconductors", 1.78),
        ("STM", "STMicroelectronics ADR", "Technology", "Semiconductors", 1.56),
        ("ENTG", "Entegris Inc", "Technology", "Semiconductor Equipment", 1.34),
        ("WOLF", "Wolfspeed Inc", "Technology", "Semiconductors", 1.12),
    ],
}

today = date.today()

for etf_ticker, holdings in holdings_data.items():
    total_weight = sum(w for _, _, _, _, w in holdings)
    covered_weight = round(total_weight / 100, 6)
    print(f"\n{etf_ticker} covered_weight: {covered_weight:.4f} ({total_weight:.2f}%)")

    for ticker, name, sector, industry, weight_pct in holdings:
        sec = db.query(Security).filter(Security.ticker == ticker).first()
        if not sec:
            sec = Security(id=ticker, ticker=ticker, company_name=name, sector=sector, industry=industry)
            db.add(sec)
            db.flush()

        holding_id = f"{etf_ticker}|{ticker}|{today}"
        existing_h = db.query(ETFHolding).filter(ETFHolding.id == holding_id).first()
        if not existing_h:
            h = ETFHolding(
                id=holding_id,
                etf_ticker=etf_ticker,
                security_ticker=ticker,
                weight=round(weight_pct / 100, 6),
                effective_date=today,
                covered_weight=covered_weight,
                source="manual_seed_issuer_websites",
            )
            db.add(h)

    db.commit()
    print(f"{etf_ticker} seeded.")

print("\nValidating...")

for etf_ticker in ["SPY", "QQQ", "SMH"]:
    rows = db.query(ETFHolding).filter(
        ETFHolding.etf_ticker == etf_ticker,
        ETFHolding.effective_date == today
    ).all()
    total = sum(float(r.weight) for r in rows)
    print(f"{etf_ticker}: {len(rows)} holdings, total weight: {total*100:.2f}%")
    for r in rows:
        assert 0 < float(r.weight) < 1, f"Bad weight: {r.security_ticker}"
    print(f"  Validation passed.")

db.close()
print("\nPhase 2 complete.")
