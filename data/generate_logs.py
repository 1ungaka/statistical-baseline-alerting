import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_logs(days=14, seed=42):
    np.random.seed(seed)
    random.seed(seed)

    records = []
    start = datetime.now() - timedelta(days=days)

    users = ["alice", "bob", "carol", "dave", "eve", "frank"]
    ips = [f"192.168.1.{i}" for i in range(10, 30)]
    external_ips = [f"45.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(5)]

    for day_offset in range(days):
        current_day = start + timedelta(days=day_offset)
        is_anomaly_day = day_offset in [10, 11, 13]

        for hour in range(24):
            ts = current_day + timedelta(hours=hour)

            # Normal pattern: business hours 8-18 have more logins
            if 8 <= hour <= 18:
                base_count = np.random.poisson(lam=12)
            elif 19 <= hour <= 22:
                base_count = np.random.poisson(lam=4)
            else:
                base_count = np.random.poisson(lam=1)

            # Inject anomalies: brute-force spike
            if is_anomaly_day and hour in [2, 3]:
                base_count += np.random.randint(40, 80)

            for _ in range(base_count):
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                event_ts = ts + timedelta(minutes=minute, seconds=second)

                is_failed = random.random() < (0.6 if is_anomaly_day and hour in [2, 3] else 0.08)
                user = random.choice(users) if not (is_anomaly_day and hour in [2, 3]) else "eve"
                src_ip = random.choice(external_ips if is_anomaly_day and hour in [2, 3] else ips)

                records.append({
                    "timestamp": event_ts,
                    "user": user,
                    "src_ip": src_ip,
                    "event_type": "login_failed" if is_failed else "login_success",
                    "bytes_transferred": np.random.randint(200, 1500) if not is_failed else 0,
                    "hour": hour,
                    "day": event_ts.strftime("%Y-%m-%d"),
                })

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = generate_logs()
    df.to_csv("logs.csv", index=False)
    print(f"Generated {len(df)} log entries across {df['day'].nunique()} days.")
    print(df.head())
