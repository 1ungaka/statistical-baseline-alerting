import pandas as pd
import numpy as np


def compute_hourly_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate raw log events into hourly buckets with features
    that the anomaly detector will score against.
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_bucket"] = df["timestamp"].dt.floor("h")

    hourly = df.groupby("hour_bucket").agg(
        total_events=("event_type", "count"),
        failed_logins=("event_type", lambda x: (x == "login_failed").sum()),
        unique_users=("user", "nunique"),
        unique_ips=("src_ip", "nunique"),
        avg_bytes=("bytes_transferred", "mean"),
    ).reset_index()

    hourly["failure_rate"] = hourly["failed_logins"] / hourly["total_events"].replace(0, 1)
    hourly["hour_of_day"] = hourly["hour_bucket"].dt.hour
    hourly["date"] = hourly["hour_bucket"].dt.date

    return hourly


def zscore_anomaly(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """
    Z = (x - mean) / std
    Flag anything beyond `threshold` standard deviations from the mean.
    Returns absolute Z-scores.
    """
    mean = series.mean()
    std = series.std()
    if std == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return ((series - mean) / std).abs()


def iqr_anomaly(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """
    IQR fence method:
      lower = Q1 - multiplier * IQR
      upper = Q3 + multiplier * IQR
    Returns a boolean Series — True means anomalous.
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (series < lower) | (series > upper)


def detect_anomalies(
    hourly: pd.DataFrame,
    zscore_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
) -> pd.DataFrame:
    """
    Run both detectors over the hourly feature columns.
    Adds Z-score columns, IQR flag columns, and a composite severity score.
    """
    result = hourly.copy()

    features = ["total_events", "failed_logins", "unique_ips", "failure_rate"]

    for feat in features:
        z_col = f"z_{feat}"
        iqr_col = f"iqr_flag_{feat}"
        result[z_col] = zscore_anomaly(result[feat], zscore_threshold)
        result[iqr_col] = iqr_anomaly(result[feat], iqr_multiplier)

    # Composite severity: max Z-score across all features
    z_cols = [f"z_{f}" for f in features]
    result["max_zscore"] = result[z_cols].max(axis=1)

    # Count how many IQR flags fired
    iqr_cols = [f"iqr_flag_{f}" for f in features]
    result["iqr_flags_count"] = result[iqr_cols].sum(axis=1)

    # Severity label
    def severity(row):
        if row["max_zscore"] >= 5 or row["iqr_flags_count"] >= 3:
            return "CRITICAL"
        elif row["max_zscore"] >= 3 or row["iqr_flags_count"] >= 2:
            return "HIGH"
        elif row["max_zscore"] >= 2 or row["iqr_flags_count"] >= 1:
            return "MEDIUM"
        return "NORMAL"

    result["severity"] = result.apply(severity, axis=1)
    result["is_anomaly"] = result["severity"] != "NORMAL"

    return result


def get_baseline_stats(hourly: pd.DataFrame) -> dict:
    """Summary stats used for the dashboard metrics strip."""
    features = ["total_events", "failed_logins", "unique_ips", "failure_rate"]
    stats = {}
    for feat in features:
        stats[feat] = {
            "mean": hourly[feat].mean(),
            "std": hourly[feat].std(),
            "q1": hourly[feat].quantile(0.25),
            "q3": hourly[feat].quantile(0.75),
        }
    return stats
