import logging
import numpy as np
import pandas as pd
from datetime import date
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest
from app.models.price import DailyPrice
from app.models.etf import ETF

logger = logging.getLogger(__name__)

ZSCORE_THRESHOLD = 2.0
BENCHMARK_THRESHOLDS = {"SPY": 0.015, "QQQ": 0.020, "SMH": 0.025}
ROLLING_WINDOW = 60
MIN_OBSERVATIONS = 40


def to_float(val):
    """Convert numpy float to Python float safely."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return float(val)


def to_bool(val):
    """Convert numpy bool to Python bool."""
    return bool(val)


def get_price_series(ticker: str, db: Session) -> pd.DataFrame:
    prices = (
        db.query(DailyPrice)
        .filter(DailyPrice.ticker == ticker)
        .order_by(DailyPrice.trade_date.asc())
        .all()
    )
    if not prices:
        return pd.DataFrame()
    df = pd.DataFrame([{
        "date": p.trade_date,
        "daily_return": float(p.daily_return) if p.daily_return else None,
        "volume": float(p.volume) if p.volume else None,
    } for p in prices])
    df = df.dropna(subset=["daily_return"])
    df = df.set_index("date").sort_index()
    return df


def compute_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rolling_mean"] = df["daily_return"].rolling(window=ROLLING_WINDOW, min_periods=MIN_OBSERVATIONS).mean()
    df["rolling_std"] = df["daily_return"].rolling(window=ROLLING_WINDOW, min_periods=MIN_OBSERVATIONS).std()
    df["rolling_volatility"] = df["rolling_std"]
    df["z_score"] = (df["daily_return"] - df["rolling_mean"]) / df["rolling_std"]
    df["ewma_volatility"] = df["daily_return"].ewm(span=20).std()
    return df


def detect_anomaly_statistical(etf_ticker: str, target_date: date, db: Session) -> dict:
    etf_ticker = etf_ticker.upper()
    df = get_price_series(etf_ticker, db)
    if df.empty or target_date not in df.index:
        return {"error": f"No data for {etf_ticker} on {target_date}"}

    etf_record = db.query(ETF).filter(ETF.ticker == etf_ticker).first()
    benchmark_ticker = etf_record.benchmark_ticker if etf_record else None
    df = compute_rolling_stats(df)
    row = df.loc[target_date]

    daily_return = float(row["daily_return"])
    z_score = float(row["z_score"]) if not np.isnan(row["z_score"]) else None
    rolling_mean = to_float(row["rolling_mean"])
    rolling_volatility = to_float(row["rolling_volatility"])

    condition_a = bool(z_score is not None and abs(z_score) >= ZSCORE_THRESHOLD)
    threshold = BENCHMARK_THRESHOLDS.get(etf_ticker, 0.025)

    abnormal_return = daily_return
    benchmark_return = None
    if benchmark_ticker:
        bm_df = get_price_series(benchmark_ticker, db)
        if not bm_df.empty and target_date in bm_df.index:
            benchmark_return = float(bm_df.loc[target_date, "daily_return"])
            abnormal_return = daily_return - benchmark_return

    condition_b = bool(abs(abnormal_return) >= threshold)
    is_anomaly = bool(condition_a or condition_b)

    triggered = []
    if condition_a:
        triggered.append("z_score")
    if condition_b:
        triggered.append("benchmark_adjusted")

    return {
        "etf_ticker": etf_ticker,
        "date": str(target_date),
        "daily_return_pct": round(daily_return * 100, 4),
        "z_score": round(z_score, 4) if z_score is not None else None,
        "rolling_mean": round(rolling_mean, 6) if rolling_mean is not None else None,
        "rolling_volatility": round(rolling_volatility, 6) if rolling_volatility is not None else None,
        "benchmark_ticker": benchmark_ticker,
        "benchmark_return": round(benchmark_return, 6) if benchmark_return is not None else None,
        "abnormal_return_pct": round(abnormal_return * 100, 4),
        "threshold_used": threshold,
        "condition_a_zscore": condition_a,
        "condition_b_benchmark": condition_b,
        "is_anomaly": is_anomaly,
        "triggered_by": triggered,
        "method": "statistical",
    }


def detect_anomaly_isolation_forest(etf_ticker: str, target_date: date, db: Session, contamination: float = 0.05) -> dict:
    etf_ticker = etf_ticker.upper()
    df = get_price_series(etf_ticker, db)
    if df.empty:
        return {"error": f"No data for {etf_ticker}"}

    df = compute_rolling_stats(df)
    df["volume_change"] = df["volume"].pct_change()
    df["return_squared"] = df["daily_return"] ** 2

    etf_record = db.query(ETF).filter(ETF.ticker == etf_ticker).first()
    benchmark_ticker = etf_record.benchmark_ticker if etf_record else None
    if benchmark_ticker:
        bm_df = get_price_series(benchmark_ticker, db)
        if not bm_df.empty:
            df["abnormal_return"] = df["daily_return"] - bm_df["daily_return"]
        else:
            df["abnormal_return"] = df["daily_return"]
    else:
        df["abnormal_return"] = df["daily_return"]

    features = ["daily_return", "abnormal_return", "z_score",
                "rolling_volatility", "volume_change", "return_squared"]
    df_model = df[features].dropna()

    if len(df_model) < MIN_OBSERVATIONS:
        return {"error": "Not enough data for Isolation Forest"}

    clf = IsolationForest(n_estimators=100, contamination=contamination, random_state=42)
    clf.fit(df_model)
    scores = clf.score_samples(df_model)
    predictions = clf.predict(df_model)
    df_model = df_model.copy()
    df_model["anomaly_score"] = scores
    df_model["is_anomaly_if"] = predictions == -1

    if target_date not in df_model.index:
        return {"error": f"Target date {target_date} not available after feature engineering"}

    row = df_model.loc[target_date]
    return {
        "etf_ticker": etf_ticker,
        "date": str(target_date),
        "daily_return_pct": round(float(df.loc[target_date, "daily_return"]) * 100, 4),
        "anomaly_score": round(float(row["anomaly_score"]), 6),
        "is_anomaly": bool(row["is_anomaly_if"]),
        "contamination": contamination,
        "features_used": features,
        "method": "isolation_forest",
    }


def compare_methods(etf_ticker: str, target_date: date, db: Session) -> dict:
    statistical = detect_anomaly_statistical(etf_ticker, target_date, db)
    isolation_forest = detect_anomaly_isolation_forest(etf_ticker, target_date, db)
    stat_anomaly = bool(statistical.get("is_anomaly", False))
    if_anomaly = bool(isolation_forest.get("is_anomaly", False))
    both_flag = bool(stat_anomaly and if_anomaly)
    only_stat = bool(stat_anomaly and not if_anomaly)
    only_if = bool(if_anomaly and not stat_anomaly)
    neither = bool(not stat_anomaly and not if_anomaly)

    return {
        "etf_ticker": etf_ticker.upper(),
        "date": str(target_date),
        "statistical": statistical,
        "isolation_forest": isolation_forest,
        "comparison": {
            "agreement": bool(stat_anomaly == if_anomaly),
            "both_flag_anomaly": both_flag,
            "only_statistical_flags": only_stat,
            "only_isolation_forest_flags": only_if,
            "neither_flags": neither,
            "recommended": "investigate" if both_flag else (
                "review" if (only_stat or only_if) else "normal"
            ),
        },
    }


def scan_anomalies(etf_ticker: str, db: Session,
                   start_date: date = None, end_date: date = None) -> list:
    etf_ticker = etf_ticker.upper()
    df = get_price_series(etf_ticker, db)
    if df.empty:
        return []

    df = compute_rolling_stats(df)
    etf_record = db.query(ETF).filter(ETF.ticker == etf_ticker).first()
    benchmark_ticker = etf_record.benchmark_ticker if etf_record else None
    threshold = BENCHMARK_THRESHOLDS.get(etf_ticker, 0.025)

    if benchmark_ticker:
        bm_df = get_price_series(benchmark_ticker, db)
        if not bm_df.empty:
            df["abnormal_return"] = df["daily_return"] - bm_df["daily_return"]
        else:
            df["abnormal_return"] = df["daily_return"]
    else:
        df["abnormal_return"] = df["daily_return"]

    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    df["condition_a"] = df["z_score"].abs() >= ZSCORE_THRESHOLD
    df["condition_b"] = df["abnormal_return"].abs() >= threshold
    df["is_anomaly"] = df["condition_a"] | df["condition_b"]

    anomalies = df[df["is_anomaly"]].copy()
    anomalies = anomalies.sort_values("z_score", key=abs, ascending=False)

    results = []
    for idx, row in anomalies.iterrows():
        z = float(row["z_score"]) if not np.isnan(row["z_score"]) else None
        ca = bool(row["condition_a"])
        cb = bool(row["condition_b"])
        results.append({
            "date": str(idx),
            "daily_return_pct": round(float(row["daily_return"]) * 100, 4),
            "z_score": round(z, 4) if z is not None else None,
            "abnormal_return_pct": round(float(row["abnormal_return"]) * 100, 4),
            "triggered_by": (
                "both" if ca and cb else
                "z_score" if ca else "benchmark_adjusted"
            ),
        })
    return results
