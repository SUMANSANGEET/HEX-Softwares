"""
╔══════════════════════════════════════════════════════════════════╗
║         🎬  YouTube Data Dashboard  —  Streamlit App            ║
║                                                                  ║
║  Run:  streamlit run youtube_dashboard.py                        ║
║                                                                  ║
║  Mode A (Real API):  Set YOUTUBE_API_KEY in your environment     ║
║                      or enter it in the sidebar at runtime.      ║
║  Mode B (Demo):      Leave API key blank → rich simulated data   ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ── Standard Library ─────────────────────────────────────────────
import os, math, random, warnings
from   datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ── Third-party ──────────────────────────────────────────────────
import numpy             as np
import pandas            as pd
import streamlit         as st
import plotly.express    as px
import plotly.graph_objects as go
from   plotly.subplots   import make_subplots

# ── Optional: real YouTube API ───────────────────────────────────
try:
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# ════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title  = "YouTube Analytics Dashboard",
    page_icon   = "🎬",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global Background ─────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,#0f0f0f 0%,#1a1a2e 50%,#16213e 100%);
    color: #e0e0e0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#1a1a2e,#16213e);
    border-right: 1px solid #ff0000aa;
}

/* ── KPI Cards ─────────────────────────────────────── */
.kpi-card {
    background: linear-gradient(135deg,#1e1e3a,#2d2d5e);
    border: 1px solid #3a3a6e;
    border-radius: 16px;
    padding: 22px 20px 16px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(255,0,0,0.15);
    transition: transform .2s;
    margin-bottom: 8px;
}
.kpi-card:hover { transform: translateY(-4px); }
.kpi-icon  { font-size: 2rem; margin-bottom: 4px; }
.kpi-label { font-size: 0.78rem; color:#aaa; text-transform:uppercase;
             letter-spacing:1px; margin-bottom:4px; }
.kpi-value { font-size: 1.9rem; font-weight:800; color:#fff; line-height:1.1; }
.kpi-delta { font-size: 0.80rem; margin-top:6px; }
.kpi-pos   { color:#00e676; }
.kpi-neg   { color:#ff5252; }

/* ── Section Headers ───────────────────────────────── */
.section-title {
    font-size: 1.25rem; font-weight:700; color:#ff4444;
    border-left: 4px solid #ff4444;
    padding-left: 12px; margin: 24px 0 12px;
}

/* ── Streamlit overrides ───────────────────────────── */
h1,h2,h3 { color:#ffffff !important; }
.stMetric label { color:#aaa !important; }
div[data-testid="metric-container"] {
    background: #1e1e3a; border-radius:12px;
    padding:12px; border:1px solid #3a3a6e;
}
.stDataFrame { background:#1e1e3a; border-radius:12px; }
.stSelectbox label, .stMultiSelect label,
.stSlider label, .stDateInput label { color:#ccc !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════
def fmt_number(n: float) -> str:
    if   n >= 1_000_000_000: return f"{n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:     return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:         return f"{n/1_000:.1f}K"
    return str(int(n))

def kpi_card(icon, label, value, delta=None, delta_pos=True):
    delta_html = ""
    if delta is not None:
        cls  = "kpi-pos" if delta_pos else "kpi-neg"
        arr  = "▲" if delta_pos else "▼"
        delta_html = f'<div class="kpi-delta {cls}">{arr} {delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>"""

PLOTLY_THEME = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(20,20,40,0.7)",
    font          = dict(color="#e0e0e0", family="Arial"),
    title_font    = dict(color="#ffffff", size=15),
    legend        = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#ccc")),
    xaxis         = dict(gridcolor="#2a2a4a", color="#aaa"),
    yaxis         = dict(gridcolor="#2a2a4a", color="#aaa"),
    colorway      = ["#ff4444","#ff9800","#ffeb3b","#4caf50",
                     "#2196f3","#9c27b0","#00bcd4","#e91e63"],
)

def styled_fig(fig, title=""):
    fig.update_layout(**PLOTLY_THEME)
    if title: fig.update_layout(title=dict(text=title, x=0.02))
    return fig

# ════════════════════════════════════════════════════════════════
#  SIMULATED DATA GENERATOR
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def generate_demo_data(channel_name: str = "TechVision"):
    rng   = np.random.default_rng(42)
    TODAY = datetime.today()

    # ── Channel info ─────────────────────────────────────────
    channel = {
        "name"        : channel_name,
        "handle"      : f"@{channel_name.lower().replace(' ','')}",
        "subscribers" : 2_480_000,
        "total_views" : 345_000_000,
        "total_videos": 312,
        "joined"      : "Jan 15, 2017",
        "country"     : "United States",
        "category"    : "Science & Technology",
        "description" : f"{channel_name} — Making tech simple & fun!",
    }

    # ── Videos (last 3 years) ────────────────────────────────
    CATEGORIES = ["Tutorial","Review","News","Vlog","Short","Live","Interview"]
    video_records = []
    for i in range(150):
        days_ago   = rng.integers(1, 1095)
        pub_date   = TODAY - timedelta(days=int(days_ago))
        dur_sec    = int(rng.choice([60,300], p=[0.25,0.75]) *
                        rng.uniform(0.5, 8))
        cat        = rng.choice(CATEGORIES, p=[0.30,0.20,0.15,0.10,
                                               0.10,0.10,0.05])
        views      = int(rng.lognormal(10.5, 1.8))
        likes      = int(views * rng.uniform(0.03, 0.12))
        comments   = int(views * rng.uniform(0.002, 0.025))
        dislikes   = int(likes * rng.uniform(0.01, 0.08))
        shares     = int(views * rng.uniform(0.001, 0.015))
        watch_pct  = round(rng.uniform(30, 75), 1)
        imp_ctr    = round(rng.uniform(3, 12), 2)
        rev_per_1k = round(rng.uniform(0.80, 6.50), 2)
        revenue    = round(views / 1000 * rev_per_1k, 2)
        video_records.append({
            "video_id"     : f"vid_{i:03d}",
            "title"        : f"{cat} Video #{i+1}: {rng.choice(['Deep Dive','Quick Guide','Best Of','vs','Review','Tutorial'])}..",
            "category"     : cat,
            "published_at" : pub_date,
            "duration_sec" : dur_sec,
            "views"        : views,
            "likes"        : likes,
            "dislikes"     : dislikes,
            "comments"     : comments,
            "shares"       : shares,
            "watch_pct"    : watch_pct,
            "imp_ctr_pct"  : imp_ctr,
            "revenue_usd"  : revenue,
            "thumbnail_url": f"https://picsum.photos/seed/{i+10}/320/180",
        })

    videos = pd.DataFrame(video_records).sort_values(
        "published_at", ascending=False).reset_index(drop=True)
    videos["engagement_rate"] = (
        (videos["likes"] + videos["comments"]) / videos["views"] * 100
    ).round(2)
    videos["duration_min"] = (videos["duration_sec"] / 60).round(1)
    videos["watch_hours"]  = (
        videos["views"] * videos["watch_pct"] / 100
        * videos["duration_sec"] / 3600
    ).round(0).astype(int)

    # ── Daily time-series (last 365 days) ────────────────────
    days       = pd.date_range(TODAY - timedelta(days=364), TODAY, freq="D")
    n          = len(days)
    t          = np.linspace(0, 1, n)

    trend      = np.linspace(4000, 12000, n)
    seasonal   = 2500 * np.sin(2 * np.pi * t * 3)
    spikes     = np.zeros(n)
    for sp in rng.choice(n, 8, replace=False):
        spikes[sp] = rng.uniform(8000, 30000)
    noise      = rng.normal(0, 800, n)
    daily_views = np.clip(trend + seasonal + spikes + noise, 500, None).astype(int)

    subs_gain  = np.clip(daily_views / 120 + rng.normal(0, 8, n), 0, None).astype(int)
    subs_loss  = np.clip(rng.poisson(12, n), 0, None)
    net_subs   = subs_gain - subs_loss
    subs_cum   = 2_100_000 + np.cumsum(net_subs)

    watch_hrs  = (daily_views * rng.uniform(3, 7, n)).astype(int)
    revenue_d  = (daily_views / 1000 * rng.uniform(1.5, 4.5, n)).round(2)

    ts = pd.DataFrame({
        "date"          : days,
        "views"         : daily_views,
        "watch_hours"   : watch_hrs,
        "subs_gained"   : subs_gain,
        "subs_lost"     : subs_loss,
        "net_subs"      : net_subs,
        "subscribers"   : subs_cum,
        "revenue_usd"   : revenue_d,
        "impressions"   : (daily_views * rng.uniform(5, 15, n)).astype(int),
    })
    ts["ctr_pct"]     = (ts["views"] / ts["impressions"] * 100).round(2)
    ts["avg_view_dur"] = rng.uniform(180, 420, n).round(0)

    # ── Audience demographics ─────────────────────────────────
    age_groups = ["13-17","18-24","25-34","35-44","45-54","55-64","65+"]
    age_vals   = [4, 22, 31, 20, 13, 7, 3]

    gender = {"Male": 62, "Female": 35, "Other": 3}

    top_countries = pd.DataFrame({
        "country": ["United States","India","United Kingdom",
                    "Canada","Australia","Germany","Brazil",
                    "France","Japan","Mexico"],
        "pct_views": [38, 18, 9, 7, 5, 4, 4, 3, 3, 2],
        "pct_watch_time": [40, 15, 10, 7, 5, 5, 4, 3, 3, 2],
    })

    traffic_sources = pd.DataFrame({
        "source": ["YouTube Search","Suggested Videos","External",
                   "Browse Features","Channel Pages","Playlists","Other"],
        "pct":    [32, 28, 15, 10, 7, 5, 3],
    })

    devices = pd.DataFrame({
        "device": ["Mobile","Desktop","TV","Tablet"],
        "pct":    [62, 22, 11, 5],
    })

    return channel, videos, ts, {
        "age_groups"      : (age_groups, age_vals),
        "gender"          : gender,
        "top_countries"   : top_countries,
        "traffic_sources" : traffic_sources,
        "devices"         : devices,
    }


# ════════════════════════════════════════════════════════════════
#  REAL YOUTUBE API FETCHER (requires google-api-python-client)
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=1800)
def fetch_youtube_data(api_key: str, channel_id: str):
    """
    Fetch real channel + video data from YouTube Data API v3.
    Returns same structure as generate_demo_data() for compatibility.
    """
    if not GOOGLE_API_AVAILABLE:
        st.error("Install `google-api-python-client` to use real API.")
        return None

    youtube = build("youtube", "v3", developerKey=api_key)

    # ── Channel stats ─────────────────────────────────────────
    ch_resp = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    ).execute()

    if not ch_resp.get("items"):
        st.error("Channel not found. Check your Channel ID.")
        return None

    ch        = ch_resp["items"][0]
    ch_snip   = ch["snippet"]
    ch_stats  = ch["statistics"]
    uploads_pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    channel = {
        "name"        : ch_snip["title"],
        "handle"      : ch_snip.get("customUrl",""),
        "subscribers" : int(ch_stats.get("subscriberCount",0)),
        "total_views" : int(ch_stats.get("viewCount",0)),
        "total_videos": int(ch_stats.get("videoCount",0)),
        "joined"      : ch_snip["publishedAt"][:10],
        "country"     : ch_snip.get("country","N/A"),
        "description" : ch_snip.get("description",""),
        "category"    : "YouTube Channel",
    }

    # ── Video list (up to 50 most recent) ─────────────────────
    pl_resp = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads_pl,
        maxResults=50
    ).execute()
    video_ids = [i["contentDetails"]["videoId"]
                 for i in pl_resp.get("items",[])]

    vid_resp  = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    rows = []
    for item in vid_resp.get("items",[]):
        sn  = item["snippet"]
        st_ = item["statistics"]
        cd  = item["contentDetails"]
        rows.append({
            "video_id"    : item["id"],
            "title"       : sn["title"],
            "category"    : sn.get("categoryId","N/A"),
            "published_at": pd.to_datetime(sn["publishedAt"]),
            "duration_sec": 0,  # parse ISO 8601 if needed
            "views"       : int(st_.get("viewCount",0)),
            "likes"       : int(st_.get("likeCount",0)),
            "dislikes"    : 0,
            "comments"    : int(st_.get("commentCount",0)),
            "shares"      : 0,
            "watch_pct"   : 50.0,
            "imp_ctr_pct" : 0.0,
            "revenue_usd" : 0.0,
            "thumbnail_url": sn["thumbnails"]["medium"]["url"],
        })

    videos = pd.DataFrame(rows)
    if not videos.empty:
        videos["engagement_rate"] = (
            (videos["likes"] + videos["comments"]) /
            videos["views"].replace(0,1) * 100
        ).round(2)
        videos["duration_min"] = 0
        videos["watch_hours"]  = 0

    # NOTE: Analytics API (watch time, revenue) requires OAuth 2.0
    # and cannot be accessed with a simple API key. The time-series
    # and demographics returned here are stubs.
    ts   = pd.DataFrame()
    demo = {}
    return channel, videos, ts, demo


# ════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:12px 0 8px'>
        <span style='font-size:2.8rem'>🎬</span><br>
        <span style='font-size:1.2rem;font-weight:700;color:#ff4444'>
        YouTube Analytics</span><br>
        <span style='color:#aaa;font-size:0.75rem'>
        Data Dashboard v2.0</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Data source ───────────────────────────────────────────
    st.markdown("### ⚙️ Data Source")
    mode = st.radio("Mode", ["📊 Demo Data", "🔑 Real YouTube API"],
                    help="Demo mode uses rich simulated data. "
                         "Real API requires a YouTube Data API v3 key.")

    api_key    = ""
    channel_id = ""

    if mode == "🔑 Real YouTube API":
        st.info("Real Analytics (watch time, revenue) requires OAuth 2.0. "
                "Basic stats only via API key.", icon="ℹ️")
        api_key    = st.text_input("YouTube API Key",
                                   type="password",
                                   placeholder="AIza...")
        channel_id = st.text_input("Channel ID",
                                   placeholder="UCxxxxxxxxxxxxxxxxxxxxxx")
        if not api_key or not channel_id:
            st.warning("Enter both API key and Channel ID to fetch data.")
            mode = "📊 Demo Data"

    channel_name = st.text_input("Channel Name (Demo)",
                                  value="TechVision",
                                  disabled=(mode != "📊 Demo Data"))

    st.divider()

    # ── Date range ────────────────────────────────────────────
    st.markdown("### 📅 Date Range")
    TODAY    = datetime.today()
    date_end = st.date_input("End Date",   value=TODAY)
    date_opt = st.selectbox("Quick Range",
                            ["Last 7 days","Last 28 days",
                             "Last 90 days","Last 365 days","Custom"])
    offset_map = {"Last 7 days":7,"Last 28 days":28,
                  "Last 90 days":90,"Last 365 days":365}
    if date_opt != "Custom":
        date_start = date_end - timedelta(days=offset_map[date_opt])
    else:
        date_start = st.date_input("Start Date",
                                   value=TODAY - timedelta(days=90))

    st.divider()

    # ── Filters ───────────────────────────────────────────────
    st.markdown("### 🔍 Filters")
    CATEGORIES = ["All","Tutorial","Review","News","Vlog",
                  "Short","Live","Interview"]
    cat_filter = st.selectbox("Category", CATEGORIES)

    top_n = st.slider("Top N Videos", 5, 50, 10)

    metric_opt = st.selectbox("Primary Metric",
                              ["views","likes","comments",
                               "watch_hours","revenue_usd",
                               "engagement_rate"])
    st.divider()

    # ── Export ────────────────────────────────────────────────
    st.markdown("### 📥 Export")
    export_btn = st.button("⬇️ Download CSV Report", use_container_width=True)


# ════════════════════════════════════════════════════════════════
#  LOAD DATA
# ════════════════════════════════════════════════════════════════
with st.spinner("🔄 Loading data..."):
    if mode == "🔑 Real YouTube API" and api_key and channel_id:
        result = fetch_youtube_data(api_key, channel_id)
        if result is None:
            st.stop()
        channel, videos, ts, demo = result
    else:
        channel, videos, ts, demo = generate_demo_data(channel_name)

# ── Apply filters ─────────────────────────────────────────────
ts_filtered = ts[
    (ts["date"].dt.date >= date_start) &
    (ts["date"].dt.date <= date_end)
].copy()

vids_filtered = videos.copy()
if cat_filter != "All":
    vids_filtered = vids_filtered[vids_filtered["category"] == cat_filter]

# ════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style='background:linear-gradient(90deg,#ff000022,#0000);
            border-left:5px solid #ff4444;
            padding:18px 24px; border-radius:12px; margin-bottom:8px'>
    <h1 style='margin:0;font-size:2rem'>🎬 {channel["name"]}</h1>
    <p style='color:#aaa;margin:4px 0 0;font-size:0.9rem'>
        {channel["handle"]} &nbsp;|&nbsp; {channel["category"]}
        &nbsp;|&nbsp; Joined {channel["joined"]}
        &nbsp;|&nbsp; {channel["country"]}
    </p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TABS
# ════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 Overview",
    "📈 Trends",
    "🎥 Videos",
    "👥 Audience",
    "💰 Revenue",
    "🔍 Deep Dive",
])


# ╔══════════════════════════════════════════════════════════════╗
# ║  TAB 1 — OVERVIEW                                           ║
# ╚══════════════════════════════════════════════════════════════╝
with tabs[0]:

    # ── KPI Row ───────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    period_views  = int(ts_filtered["views"].sum())    if not ts_filtered.empty else 0
    period_watch  = int(ts_filtered["watch_hours"].sum()) if not ts_filtered.empty else 0
    period_subs   = int(ts_filtered["net_subs"].sum()) if not ts_filtered.empty else 0
    period_rev    = ts_filtered["revenue_usd"].sum()   if not ts_filtered.empty else 0
    avg_ctr       = ts_filtered["ctr_pct"].mean()      if not ts_filtered.empty else 0
    avg_dur       = ts_filtered["avg_view_dur"].mean() if not ts_filtered.empty else 0

    kpi_data = [
        (k1, "👁️",  "Total Views",       fmt_number(channel["total_views"]),
         f"{fmt_number(period_views)} this period", True),
        (k2, "📺",  "Subscribers",       fmt_number(channel["subscribers"]),
         f"+{fmt_number(period_subs)} this period", period_subs >= 0),
        (k3, "⏱️",  "Watch Hours",       fmt_number(period_watch),
         f"This selected period", True),
        (k4, "📹",  "Total Videos",      str(channel["total_videos"]),
         f"{len(vids_filtered)} in filter", True),
        (k5, "🖱️",  "Avg CTR",           f"{avg_ctr:.1f}%",
         "Impressions → Clicks", True),
        (k6, "⌚",  "Avg View Duration", f"{avg_dur:.0f}s",
         f"≈ {avg_dur/60:.1f} min", True),
    ]
    for col, icon, label, val, delta, pos in kpi_data:
        with col:
            st.markdown(kpi_card(icon, label, val, delta, pos),
                        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Views + Subs Overview Chart ───────────────────────────
    if not ts_filtered.empty:
        st.markdown('<div class="section-title">📅 Selected Period Overview</div>',
                    unsafe_allow_html=True)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Daily Views","Subscribers Growth",
                            "Watch Hours","Net Subscribers"),
            vertical_spacing=0.16, horizontal_spacing=0.1,
        )
        fig.add_trace(go.Bar(
            x=ts_filtered["date"], y=ts_filtered["views"],
            name="Views", marker_color="#ff4444", opacity=0.75,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=ts_filtered["date"], y=ts_filtered["subscribers"],
            name="Subscribers", line=dict(color="#4caf50", width=2.5),
            fill="tozeroy", fillcolor="rgba(76,175,80,0.12)",
        ), row=1, col=2)
        fig.add_trace(go.Scatter(
            x=ts_filtered["date"], y=ts_filtered["watch_hours"],
            name="Watch Hrs", line=dict(color="#ff9800", width=2.5),
            fill="tozeroy", fillcolor="rgba(255,152,0,0.12)",
        ), row=2, col=1)
        fig.add_trace(go.Bar(
            x=ts_filtered["date"], y=ts_filtered["net_subs"],
            name="Net Subs",
            marker_color=ts_filtered["net_subs"].apply(
                lambda v: "#4caf50" if v >= 0 else "#f44336"),
        ), row=2, col=2)
        fig.update_layout(**PLOTLY_THEME, height=520,
                          showlegend=False, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)

    # ── Metric Comparison Cards ───────────────────────────────
    st.markdown('<div class="section-title">📊 Period Snapshot</div>',
                unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Views This Period",    fmt_number(period_views))
    with m2: st.metric("Watch Hours",          fmt_number(period_watch))
    with m3: st.metric("Revenue (Est.)",       f"${period_rev:,.0f}")
    with m4: st.metric("Net New Subscribers",  fmt_number(period_subs),
                        delta_color="normal")


# ╔══════════════════════════════════════════════════════════════╗
# ║  TAB 2 — TRENDS                                             ║
# ╚══════════════════════════════════════════════════════════════╝
with tabs[1]:
    if ts_filtered.empty:
        st.info("No time-series data available.")
    else:
        st.markdown('<div class="section-title">📈 Performance Trends</div>',
                    unsafe_allow_html=True)

        # ── Metric Selector ───────────────────────────────────
        trend_metric = st.selectbox(
            "Select Trend Metric",
            ["views","watch_hours","subscribers","revenue_usd",
             "subs_gained","subs_lost","impressions","ctr_pct"],
            key="trend_metric"
        )

        ts_filtered["rolling_7"]  = ts_filtered[trend_metric].rolling(7).mean()
        ts_filtered["rolling_30"] = ts_filtered[trend_metric].rolling(30).mean()

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=ts_filtered["date"], y=ts_filtered[trend_metric],
            name="Daily", marker_color="#ff4444", opacity=0.4,
        ))
        fig_trend.add_trace(go.Scatter(
            x=ts_filtered["date"], y=ts_filtered["rolling_7"],
            name="7-Day Avg", line=dict(color="#ffeb3b", width=2.5),
        ))
        fig_trend.add_trace(go.Scatter(
            x=ts_filtered["date"], y=ts_filtered["rolling_30"],
            name="30-Day Avg", line=dict(color="#4caf50", width=2),
        ))
        fig_trend.update_layout(**PLOTLY_THEME,
                                title=f"{trend_metric.replace('_',' ').title()} Over Time",
                                height=420)
        st.plotly_chart(fig_trend, use_container_width=True)

        # ── Month-over-Month Comparison ───────────────────────
        st.markdown('<div class="section-title">📆 Month-over-Month</div>',
                    unsafe_allow_html=True)
        ts_filtered["month_yr"] = ts_filtered["date"].dt.to_period("M").astype(str)
        mom = ts_filtered.groupby("month_yr")[
            ["views","watch_hours","revenue_usd","subs_gained"]
        ].sum().reset_index()

        fig_mom = px.bar(
            mom, x="month_yr",
            y=["views","watch_hours","subs_gained"],
            barmode="group",
            color_discrete_sequence=["#ff4444","#ff9800","#4caf50"],
            title="Monthly Performance Breakdown",
        )
        fig_mom.update_layout(**PLOTLY_THEME, height=400,
                               xaxis_title="Month", yaxis_title="Value")
        st.plotly_chart(fig_mom, use_container_width=True)

        # ── Weekday Heatmap ───────────────────────────────────
        st.markdown('<div class="section-title">🗓️ Day-of-Week Patterns</div>',
                    unsafe_allow_html=True)
        ts_filtered["weekday"]  = ts_filtered["date"].dt.day_name()
        ts_filtered["week_num"] = ts_filtered["date"].dt.isocalendar().week.astype(int)

        wday_order = ["Monday","Tuesday","Wednesday","Thursday",
                      "Friday","Saturday","Sunday"]
        hm_data = ts_filtered.groupby("weekday")["views"].mean().reindex(wday_order)

        fig_hm = px.bar(
            x=hm_data.index, y=hm_data.values,
            color=hm_data.values,
            color_continuous_scale="Reds",
            title="Average Views by Day of Week",
            labels={"x":"Day","y":"Avg Views","color":"Views"},
        )
        fig_hm.update_layout(**PLOTLY_THEME, height=340,
                              coloraxis_showscale=False)
        st.plotly_chart(fig_hm, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  TAB 3 — VIDEOS                                             ║
# ╚══════════════════════════════════════════════════════════════╝
with tabs[2]:
    if vids_filtered.empty:
        st.info("No videos found for the selected filters.")
    else:
        st.markdown('<div class="section-title">🏆 Top Performing Videos</div>',
                    unsafe_allow_html=True)

        top_vids = vids_filtered.nlargest(top_n, metric_opt)

        # ── Top N Bar Chart ───────────────────────────────────
        fig_bar = px.bar(
            top_vids.sort_values(metric_opt),
            x=metric_opt, y="title",
            orientation="h",
            color=metric_opt,
            color_continuous_scale="Reds",
            title=f"Top {top_n} Videos by {metric_opt.replace('_',' ').title()}",
            hover_data=["category","views","likes","comments",
                        "engagement_rate","duration_min"],
            text=top_vids.sort_values(metric_opt)[metric_opt].apply(fmt_number),
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(**PLOTLY_THEME, height=max(380, top_n*38),
                               coloraxis_showscale=False,
                               yaxis_title="", xaxis_title=metric_opt)
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Views vs Engagement Scatter ───────────────────────
        st.markdown('<div class="section-title">🔴 Views vs Engagement</div>',
                    unsafe_allow_html=True)
        fig_sc = px.scatter(
            vids_filtered,
            x="views", y="engagement_rate",
            size="watch_hours", color="category",
            hover_name="title",
            hover_data=["likes","comments","duration_min"],
            title="Views vs Engagement Rate (bubble = Watch Hours)",
            size_max=40,
        )
        fig_sc.update_layout(**PLOTLY_THEME, height=480)
        st.plotly_chart(fig_sc, use_container_width=True)

        # ── Category Breakdown ────────────────────────────────
        st.markdown('<div class="section-title">📂 Category Breakdown</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        cat_stats = vids_filtered.groupby("category").agg(
            count      = ("video_id","count"),
            total_views= ("views","sum"),
            avg_engage = ("engagement_rate","mean"),
        ).reset_index().sort_values("total_views", ascending=False)

        with c1:
            fig_cat = px.pie(
                cat_stats, names="category", values="total_views",
                title="Total Views by Category",
                color_discrete_sequence=px.colors.sequential.Reds_r,
                hole=0.55,
            )
            fig_cat.update_layout(**PLOTLY_THEME, height=380)
            st.plotly_chart(fig_cat, use_container_width=True)

        with c2:
            fig_eng = px.bar(
                cat_stats, x="category", y="avg_engage",
                color="avg_engage", color_continuous_scale="RdYlGn",
                title="Avg Engagement Rate by Category (%)",
                text=cat_stats["avg_engage"].apply(lambda v: f"{v:.1f}%"),
            )
            fig_eng.update_traces(textposition="outside")
            fig_eng.update_layout(**PLOTLY_THEME, height=380,
                                   coloraxis_showscale=False)
            st.plotly_chart(fig_eng, use_container_width=True)

        # ── Video Table ───────────────────────────────────────
        st.markdown('<div class="section-title">📋 Video Details Table</div>',
                    unsafe_allow_html=True)
        show_cols = ["title","category","published_at","views","likes",
                     "comments","watch_hours","engagement_rate",
                     "duration_min","revenue_usd"]
        disp = vids_filtered[show_cols].nlargest(50, "views").copy()
        disp["views"]    = disp["views"].apply(fmt_number)
        disp["likes"]    = disp["likes"].apply(fmt_number)
        disp["watch_hours"] = disp["watch_hours"].apply(fmt_number)
        disp["revenue_usd"] = disp["revenue_usd"].apply(lambda v: f"${v:,.0f}")
        disp["published_at"] = disp["published_at"].dt.strftime("%b %d, %Y")
        st.dataframe(disp.rename(columns={
            "title":"Title","category":"Category",
            "published_at":"Published","views":"Views",
            "likes":"Likes","comments":"Comments",
            "watch_hours":"Watch Hrs","engagement_rate":"Eng. Rate %",
            "duration_min":"Duration (min)","revenue_usd":"Est. Revenue",
        }), height=380, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  TAB 4 — AUDIENCE                                           ║
# ╚══════════════════════════════════════════════════════════════╝
with tabs[3]:
    if not demo:
        st.info("Audience data available in Demo mode only.")
    else:
        st.markdown('<div class="section-title">👥 Audience Demographics</div>',
                    unsafe_allow_html=True)

        age_g, age_v = demo["age_groups"]
        gender_d     = demo["gender"]
        countries_d  = demo["top_countries"]
        traffic_d    = demo["traffic_sources"]
        devices_d    = demo["devices"]

        r1c1, r1c2, r1c3 = st.columns(3)

        # Age distribution
        with r1c1:
            fig_age = px.bar(
                x=age_g, y=age_v,
                color=age_v,
                color_continuous_scale="Reds",
                title="Age Group Distribution (%)",
                text=[f"{v}%" for v in age_v],
            )
            fig_age.update_traces(textposition="outside")
            fig_age.update_layout(**PLOTLY_THEME, height=380,
                                   coloraxis_showscale=False,
                                   xaxis_title="Age Group",
                                   yaxis_title="% of Viewers")
            st.plotly_chart(fig_age, use_container_width=True)

        # Gender donut
        with r1c2:
            fig_gen = px.pie(
                names=list(gender_d.keys()),
                values=list(gender_d.values()),
                title="Gender Breakdown",
                color_discrete_sequence=["#2196f3","#e91e63","#9c27b0"],
                hole=0.60,
            )
            fig_gen.update_layout(**PLOTLY_THEME, height=380)
            st.plotly_chart(fig_gen, use_container_width=True)

        # Device breakdown
        with r1c3:
            fig_dev = px.pie(
                devices_d, names="device", values="pct",
                title="Device Type",
                color_discrete_sequence=["#ff4444","#ff9800",
                                          "#ffeb3b","#4caf50"],
                hole=0.55,
            )
            fig_dev.update_layout(**PLOTLY_THEME, height=380)
            st.plotly_chart(fig_dev, use_container_width=True)

        # ── Geography ─────────────────────────────────────────
        st.markdown('<div class="section-title">🌍 Top Countries</div>',
                    unsafe_allow_html=True)
        gc1, gc2 = st.columns(2)

        with gc1:
            fig_geo = px.bar(
                countries_d.sort_values("pct_views"),
                x="pct_views", y="country",
                orientation="h",
                color="pct_views",
                color_continuous_scale="Reds",
                title="Views by Country (%)",
                text=countries_d.sort_values("pct_views")["pct_views"].apply(
                    lambda v: f"{v}%"),
            )
            fig_geo.update_traces(textposition="outside")
            fig_geo.update_layout(**PLOTLY_THEME, height=420,
                                   coloraxis_showscale=False)
            st.plotly_chart(fig_geo, use_container_width=True)

        with gc2:
            fig_wt = px.bar(
                countries_d.sort_values("pct_watch_time"),
                x="pct_watch_time", y="country",
                orientation="h",
                color="pct_watch_time",
                color_continuous_scale="Oranges",
                title="Watch Time by Country (%)",
                text=countries_d.sort_values("pct_watch_time")["pct_watch_time"].apply(
                    lambda v: f"{v}%"),
            )
            fig_wt.update_traces(textposition="outside")
            fig_wt.update_layout(**PLOTLY_THEME, height=420,
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_wt, use_container_width=True)

        # ── Traffic Sources ───────────────────────────────────
        st.markdown('<div class="section-title">🚦 Traffic Sources</div>',
                    unsafe_allow_html=True)
        fig_tr = px.funnel(
            traffic_d, x="pct", y="source",
            title="Traffic Source Funnel (%)",
            color="source",
            color_discrete_sequence=px.colors.sequential.Reds_r,
        )
        fig_tr.update_layout(**PLOTLY_THEME, height=420, showlegend=False)
        st.plotly_chart(fig_tr, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  TAB 5 — REVENUE                                            ║
# ╚══════════════════════════════════════════════════════════════╝
with tabs[4]:
    if ts_filtered.empty:
        st.info("No revenue data available.")
    else:
        st.markdown('<div class="section-title">💰 Revenue Analysis</div>',
                    unsafe_allow_html=True)

        total_rev  = ts_filtered["revenue_usd"].sum()
        daily_avg  = ts_filtered["revenue_usd"].mean()
        best_day   = ts_filtered.loc[ts_filtered["revenue_usd"].idxmax()]
        rpm        = (total_rev / ts_filtered["views"].sum() * 1000)

        rv1, rv2, rv3, rv4 = st.columns(4)
        with rv1: st.metric("Total Revenue",    f"${total_rev:,.0f}")
        with rv2: st.metric("Daily Average",    f"${daily_avg:,.0f}")
        with rv3: st.metric("Best Day",         f"${best_day['revenue_usd']:,.0f}")
        with rv4: st.metric("Est. RPM",         f"${rpm:.2f}")

        # ── Revenue trend ─────────────────────────────────────
        ts_filtered["rev_7d"] = ts_filtered["revenue_usd"].rolling(7).mean()
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=ts_filtered["date"], y=ts_filtered["revenue_usd"],
            name="Daily Revenue", marker_color="#4caf50", opacity=0.5,
        ))
        fig_rev.add_trace(go.Scatter(
            x=ts_filtered["date"], y=ts_filtered["rev_7d"],
            name="7-Day Avg", line=dict(color="#ffeb3b", width=2.5),
        ))
        fig_rev.update_layout(**PLOTLY_THEME, height=380,
                               title="Daily Revenue Trend ($)",
                               yaxis_title="Revenue ($)")
        st.plotly_chart(fig_rev, use_container_width=True)

        # ── Revenue by Video ──────────────────────────────────
        st.markdown('<div class="section-title">🎥 Top Revenue Videos</div>',
                    unsafe_allow_html=True)
        top_rev_vids = vids_filtered.nlargest(10,"revenue_usd")[
            ["title","category","views","revenue_usd","engagement_rate"]
        ].copy()
        top_rev_vids["revenue_usd"] = top_rev_vids["revenue_usd"].apply(
            lambda v: f"${v:,.0f}")
        top_rev_vids["views"] = top_rev_vids["views"].apply(fmt_number)
        st.dataframe(top_rev_vids, use_container_width=True)

        # ── Monthly revenue ───────────────────────────────────
        mon_rev = ts_filtered.groupby(
            ts_filtered["date"].dt.to_period("M").astype(str)
        )["revenue_usd"].sum().reset_index()
        mon_rev.columns = ["month","revenue"]
        fig_mr = px.area(
            mon_rev, x="month", y="revenue",
            title="Monthly Revenue ($)",
            color_discrete_sequence=["#4caf50"],
        )
        fig_mr.update_layout(**PLOTLY_THEME, height=360)
        st.plotly_chart(fig_mr, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  TAB 6 — DEEP DIVE                                          ║
# ╚══════════════════════════════════════════════════════════════╝
with tabs[5]:
    st.markdown('<div class="section-title">🔍 Advanced Analysis</div>',
                unsafe_allow_html=True)

    if not vids_filtered.empty:

        # ── Correlation Matrix ────────────────────────────────
        corr_cols = ["views","likes","comments","watch_hours",
                     "engagement_rate","duration_min","revenue_usd"]
        corr_m    = vids_filtered[corr_cols].corr().round(2)

        fig_corr = px.imshow(
            corr_m, text_auto=True,
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            title="Feature Correlation Matrix",
            aspect="auto",
        )
        fig_corr.update_layout(**PLOTLY_THEME, height=480)
        st.plotly_chart(fig_corr, use_container_width=True)

        # ── Publish Time Analysis ─────────────────────────────
        st.markdown('<div class="section-title">🕐 Optimal Posting Time</div>',
                    unsafe_allow_html=True)

        vids_filtered["pub_hour"]    = vids_filtered["published_at"].dt.hour
        vids_filtered["pub_weekday"] = vids_filtered["published_at"].dt.day_name()

        hour_perf = vids_filtered.groupby("pub_hour")["views"].mean().reset_index()
        day_perf  = vids_filtered.groupby("pub_weekday")["views"].mean()
        day_perf  = day_perf.reindex([
            "Monday","Tuesday","Wednesday","Thursday",
            "Friday","Saturday","Sunday"
        ]).reset_index()

        pc1, pc2 = st.columns(2)
        with pc1:
            fig_hr = px.bar(
                hour_perf, x="pub_hour", y="views",
                color="views", color_continuous_scale="Reds",
                title="Avg Views by Publish Hour",
                labels={"pub_hour":"Hour of Day","views":"Avg Views"},
            )
            fig_hr.update_layout(**PLOTLY_THEME, height=360,
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_hr, use_container_width=True)

        with pc2:
            fig_dy = px.bar(
                day_perf, x="pub_weekday", y="views",
                color="views", color_continuous_scale="Oranges",
                title="Avg Views by Publish Day",
                labels={"pub_weekday":"Day","views":"Avg Views"},
            )
            fig_dy.update_layout(**PLOTLY_THEME, height=360,
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_dy, use_container_width=True)

        # ── Duration vs Performance ───────────────────────────
        st.markdown('<div class="section-title">⏱️ Duration vs Performance</div>',
                    unsafe_allow_html=True)

        vids_filtered["dur_band"] = pd.cut(
            vids_filtered["duration_min"],
            bins=[0,1,5,10,20,60,300],
            labels=["<1 min","1–5 min","5–10 min",
                    "10–20 min","20–60 min",">60 min"],
        )
        dur_perf = vids_filtered.groupby("dur_band").agg(
            avg_views   = ("views","mean"),
            avg_engage  = ("engagement_rate","mean"),
            count       = ("video_id","count"),
        ).dropna().reset_index()

        fig_dur = make_subplots(specs=[[{"secondary_y":True}]])
        fig_dur.add_trace(go.Bar(
            x=dur_perf["dur_band"].astype(str),
            y=dur_perf["avg_views"],
            name="Avg Views",
            marker_color="#ff4444",
        ), secondary_y=False)
        fig_dur.add_trace(go.Scatter(
            x=dur_perf["dur_band"].astype(str),
            y=dur_perf["avg_engage"],
            name="Avg Engagement %",
            mode="lines+markers",
            line=dict(color="#ffeb3b", width=3),
            marker=dict(size=9),
        ), secondary_y=True)
        fig_dur.update_layout(**PLOTLY_THEME, height=420,
                               title="Video Duration vs Views & Engagement")
        fig_dur.update_yaxes(title_text="Avg Views",
                             secondary_y=False, color="#ff4444")
        fig_dur.update_yaxes(title_text="Avg Engagement %",
                             secondary_y=True, color="#ffeb3b")
        st.plotly_chart(fig_dur, use_container_width=True)

        # ── Growth Rate Calculator ────────────────────────────
        st.markdown('<div class="section-title">📐 Growth Rate Calculator</div>',
                    unsafe_allow_html=True)
        if not ts_filtered.empty and len(ts_filtered) > 14:
            half = len(ts_filtered) // 2
            h1   = ts_filtered.iloc[:half]["views"].sum()
            h2   = ts_filtered.iloc[half:]["views"].sum()
            gr   = (h2 - h1) / h1 * 100 if h1 > 0 else 0
            col_a, col_b, col_c = st.columns(3)
            with col_a: st.metric("First Half Views",  fmt_number(h1))
            with col_b: st.metric("Second Half Views", fmt_number(h2))
            with col_c: st.metric("Growth Rate",
                                  f"{gr:+.1f}%",
                                  delta_color="normal")


# ════════════════════════════════════════════════════════════════
#  EXPORT
# ════════════════════════════════════════════════════════════════
if export_btn and not vids_filtered.empty:
    csv = vids_filtered.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label    = "📄 Click to Save CSV",
        data     = csv,
        file_name= f"youtube_report_{datetime.today().strftime('%Y%m%d')}.csv",
        mime     = "text/csv",
    )
    st.sidebar.success("✅ Report ready!")


# ════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#555;font-size:0.78rem;padding:8px'>
    🎬 YouTube Analytics Dashboard &nbsp;|&nbsp;
    Built with Streamlit + Plotly &nbsp;|&nbsp;
    Data refreshes every 30 min (API) or is simulated (Demo)
</div>
""", unsafe_allow_html=True)