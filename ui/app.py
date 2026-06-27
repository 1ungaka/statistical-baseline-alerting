import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data.generate_logs import generate_logs
from core.detector import compute_hourly_features, detect_anomalies, get_baseline_stats

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Statistical Baseline Alerting",
    page_icon="🛡️",
    layout="wide",
)

# ── Minimal styling ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  .metric-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
  }
  .metric-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin: 0; }
  .metric-value { font-size: 26px; font-weight: 600; color: #f1f5f9; margin: 4px 0 0; }
  .badge-critical { background:#7f1d1d; color:#fca5a5; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .badge-high     { background:#78350f; color:#fcd34d; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .badge-medium   { background:#1e3a5f; color:#93c5fd; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  .badge-normal   { background:#14532d; color:#86efac; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
  [data-testid="stSidebar"] { background: #0f172a; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ SBA Config")
    st.markdown("---")

    data_source = st.radio("Data source", ["Generate synthetic logs", "Upload CSV"])
    days = st.slider("Days of log history", 7, 30, 14)
    zscore_thresh = st.slider("Z-score threshold", 1.5, 5.0, 3.0, step=0.5)
    iqr_mult = st.slider("IQR multiplier", 1.0, 3.0, 1.5, step=0.5)

    st.markdown("---")
    st.markdown("**What is this?**")
    st.markdown(
        "Flags anomalous hours using Z-score (standard deviations from the mean) "
        "and IQR fences (statistical outlier bounds). No signatures — pure maths."
    )

# ── Load data ─────────────────────────────────────────────────────────────────
if data_source == "Upload CSV":
    uploaded = st.file_uploader("Upload log CSV", type="csv")
    if not uploaded:
        st.info("Upload a CSV with columns: timestamp, user, src_ip, event_type, bytes_transferred")
        st.stop()
    raw_df = pd.read_csv(uploaded)
else:
    raw_df = generate_logs(days=days)

hourly = compute_hourly_features(raw_df)
result = detect_anomalies(hourly, zscore_threshold=zscore_thresh, iqr_multiplier=iqr_mult)
stats = get_baseline_stats(hourly)

anomalies = result[result["is_anomaly"]]
critical = result[result["severity"] == "CRITICAL"]
high = result[result["severity"] == "HIGH"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🛡️ Statistical Baseline Alerting")
st.markdown("*Anomaly detection using Z-score and IQR — no signatures, no rules, just maths.*")
st.markdown("---")

# ── Metric strip ─────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Total log entries", f"{len(raw_df):,}")
with c2:
    st.metric("Hours analysed", f"{len(result):,}")
with c3:
    st.metric("Anomalies detected", f"{len(anomalies):,}", delta=f"{len(anomalies)/len(result)*100:.1f}% of hours", delta_color="inverse")
with c4:
    st.metric("Critical alerts", f"{len(critical):,}", delta_color="inverse")
with c5:
    failure_pct = (raw_df["event_type"] == "login_failed").mean() * 100
    st.metric("Overall failure rate", f"{failure_pct:.1f}%")

st.markdown("---")

# ── Main chart: events per hour with anomaly overlay ─────────────────────────
st.markdown("### Event volume timeline")
st.markdown("*Highlighted points exceeded the Z-score or IQR threshold.*")

fig = go.Figure()

# Normal hours
normal = result[~result["is_anomaly"]]
fig.add_trace(go.Scatter(
    x=normal["hour_bucket"], y=normal["total_events"],
    mode="lines+markers",
    name="Normal",
    line=dict(color="#334155", width=1.5),
    marker=dict(size=4, color="#475569"),
))

# Anomalies by severity
colors = {"MEDIUM": "#3b82f6", "HIGH": "#f59e0b", "CRITICAL": "#ef4444"}
for sev, color in colors.items():
    subset = result[result["severity"] == sev]
    if len(subset):
        fig.add_trace(go.Scatter(
            x=subset["hour_bucket"], y=subset["total_events"],
            mode="markers",
            name=sev,
            marker=dict(size=10, color=color, symbol="circle", line=dict(width=1.5, color="white")),
        ))

# Mean baseline
mean_val = stats["total_events"]["mean"]
fig.add_hline(y=mean_val, line_dash="dot", line_color="#64748b",
              annotation_text=f"Baseline mean: {mean_val:.1f}", annotation_position="top left")

fig.update_layout(
    paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
    font=dict(color="#94a3b8", size=12),
    xaxis=dict(gridcolor="#1e293b", title=""),
    yaxis=dict(gridcolor="#1e293b", title="Events per hour"),
    legend=dict(bgcolor="#1e293b", bordercolor="#334155", borderwidth=1),
    height=380, margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(fig, use_container_width=True)

# ── Two charts: failure rate + unique IPs ─────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Failed login rate per hour")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=result["hour_bucket"], y=result["failure_rate"],
        marker_color=[colors.get(s, "#334155") for s in result["severity"]],
        name="Failure rate",
    ))
    fig2.update_layout(
        paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8"),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b", title="Failure rate", tickformat=".0%"),
        height=280, margin=dict(l=20, r=20, t=10, b=20), showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.markdown("### Unique source IPs per hour")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=result["hour_bucket"], y=result["unique_ips"],
        fill="tozeroy", line=dict(color="#818cf8", width=1.5),
        fillcolor="rgba(129,140,248,0.1)", name="Unique IPs",
    ))
    q3_ips = stats["unique_ips"]["q3"]
    iqr_fence = q3_ips + iqr_mult * (stats["unique_ips"]["q3"] - stats["unique_ips"]["q1"])
    fig3.add_hline(y=iqr_fence, line_dash="dash", line_color="#f59e0b",
                   annotation_text=f"IQR upper fence: {iqr_fence:.1f}")
    fig3.update_layout(
        paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8"),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b", title="Unique IPs"),
        height=280, margin=dict(l=20, r=20, t=10, b=20), showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Alert table ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🚨 Alert queue")

if len(anomalies) == 0:
    st.success("No anomalies detected with current thresholds.")
else:
    severity_filter = st.multiselect(
        "Filter by severity",
        ["CRITICAL", "HIGH", "MEDIUM"],
        default=["CRITICAL", "HIGH", "MEDIUM"],
    )

    filtered = anomalies[anomalies["severity"].isin(severity_filter)].copy()
    filtered = filtered.sort_values("max_zscore", ascending=False)

    display_cols = {
        "hour_bucket": "Time",
        "severity": "Severity",
        "total_events": "Events",
        "failed_logins": "Failures",
        "unique_ips": "Unique IPs",
        "failure_rate": "Failure rate",
        "max_zscore": "Max Z-score",
        "iqr_flags_count": "IQR flags",
    }

    display_df = filtered[list(display_cols.keys())].rename(columns=display_cols)
    display_df["Failure rate"] = display_df["Failure rate"].map("{:.1%}".format)
    display_df["Max Z-score"] = display_df["Max Z-score"].map("{:.2f}".format)
    display_df["Time"] = display_df["Time"].astype(str)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Z-score distribution ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Z-score distribution across all hours")
st.markdown("*Hours beyond the dashed line are flagged as anomalous.*")

fig4 = px.histogram(
    result, x="max_zscore", nbins=40,
    color_discrete_sequence=["#6366f1"],
)
fig4.add_vline(x=zscore_thresh, line_dash="dash", line_color="#ef4444",
               annotation_text=f"Threshold: {zscore_thresh}", annotation_position="top right")
fig4.update_layout(
    paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
    font=dict(color="#94a3b8"),
    xaxis=dict(gridcolor="#1e293b", title="Max Z-score"),
    yaxis=dict(gridcolor="#1e293b", title="Number of hours"),
    height=280, margin=dict(l=20, r=20, t=10, b=20), showlegend=False,
)
st.plotly_chart(fig4, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Statistical Baseline Alerting · Built by Lunga Ngaka · Blue Team SOC Portfolio Project")
