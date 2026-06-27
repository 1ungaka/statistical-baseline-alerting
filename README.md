# Statistical Baseline Alerting

A Blue Team SOC tool that detects anomalous behaviour in authentication logs using **statistical methods** — no signature rules, no threat feeds. Pure maths.

## How it works

| Method | What it does |
|--------|-------------|
| **Z-score** | Flags hours where a metric (events, failures, unique IPs) is more than N standard deviations from the historical mean |
| **IQR fences** | Flags hours that fall outside Q1 − 1.5×IQR or Q3 + 1.5×IQR — robust against outliers |
| **Composite severity** | Combines both signals to label each hour as NORMAL / MEDIUM / HIGH / CRITICAL |

## Features

- 📊 Interactive timeline showing event volume with anomaly overlay
- 🔴 Alert queue with severity-rated detections
- 📈 Z-score distribution histogram
- 🌐 Unique source IP tracking with IQR upper fence
- ⚙️ Adjustable thresholds via sidebar sliders
- 📁 Upload your own CSV or generate synthetic data

## Stack

- Python 3.11+
- Streamlit (dashboard UI)
- Pandas + NumPy (detection engine)
- Plotly (charts)

## Getting started

```bash
git clone https://github.com/yourusername/statistical-baseline-alerting
cd statistical-baseline-alerting
pip install -r requirements.txt
streamlit run ui/app.py
```

## Project structure

```
statistical-baseline-alerting/
├── data/
│   └── generate_logs.py     # Synthetic log generator with injected anomalies
├── core/
│   └── detector.py          # Z-score + IQR detection engine
├── ui/
│   └── app.py               # Streamlit dashboard
└── requirements.txt
```

## CSV format (for your own logs)

```
timestamp,user,src_ip,event_type,bytes_transferred
2024-01-15 02:34:11,eve,45.12.88.3,login_failed,0
```

## Author

Lunga Ngaka — BSc Computer Science & Applied Mathematics, University of Fort Hare  
Blue Team | SOC Analyst | TryHackMe | Team DefendX
