"""Shared visual identity for the Streamlit app and the HTML export.

Tokens come from the Claude Design mockup (design/Pocket Clock.html): dark surfaces, one amber accent,
Archivo for display text and Inter for body text (self-hosted in static/fonts).
"""
import plotly.graph_objects as go
import plotly.io as pio

# ---- design tokens -------------------------------------------------------------------------------
BG, SURFACE, SURFACE_2 = "#0b0d10", "#14171c", "#1b1f26"
BORDER, BORDER_STRONG, GRID = "#2a2f38", "#3a404b", "#232831"
TEXT, MUTED, SUBTLE, REF = "#eef1f5", "#a3abb8", "#8b94a3", "#c7cdd6"
ACCENT, GOOD, BAD = "#ffb703", "#06d6a0", "#ef476f"
FONT_DISPLAY = "'Archivo', system-ui, sans-serif"
FONT_BODY = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"
OUTLINE = "rgba(199,205,214,.9)"   # light outline for team colours too dark for the surface (LV black, navy...)
SEQ = [GOOD, ACCENT, BAD, "#9b5de5", "#4cc9f0"]
FONT_URL = "/app/static/fonts"      # served by Streamlit static serving (see .streamlit/config.toml)

TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Football Team"}


def _luminance(hex_color: str) -> float:
    c = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def needs_outline(color: str) -> bool:
    """True when a bar colour has less than 3:1 contrast against the card surface."""
    a, b = sorted((_luminance(color), _luminance(SURFACE)), reverse=True)
    return (a + .05) / (b + .05) < 3


pio.templates["pocket"] = go.layout.Template(layout=dict(
    font=dict(family=FONT_BODY, color=TEXT, size=13),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, colorway=SEQ,   # explicit: Streamlit re-themes transparent backgrounds
    xaxis=dict(gridcolor=GRID, zerolinecolor=BORDER_STRONG, linecolor=BORDER_STRONG, tickfont=dict(color=MUTED), automargin=True),
    yaxis=dict(gridcolor=GRID, zerolinecolor=BORDER_STRONG, linecolor=BORDER_STRONG, tickfont=dict(color=MUTED), automargin=True),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.1, x=0, font=dict(color=MUTED)),
    hoverlabel=dict(bgcolor=SURFACE_2, bordercolor=BORDER_STRONG, font=dict(family=FONT_BODY, color=TEXT)),
    margin=dict(l=10, r=10, t=30, b=10),
    title=dict(font=dict(size=16), x=0)))
pio.templates.default = "pocket"

CSS = f"""
<style>
@font-face {{ font-family: 'Archivo'; font-weight: 500 800; font-stretch: 62% 125%; font-display: swap;
             src: url({FONT_URL}/archivo.woff2) format('woff2'); }}
@font-face {{ font-family: 'Inter'; font-weight: 400 600; font-display: swap; src: url({FONT_URL}/inter.woff2) format('woff2'); }}
:root {{
  --bg: {BG}; --surface: {SURFACE}; --surface-2: {SURFACE_2}; --line: {BORDER}; --line-strong: {BORDER_STRONG};
  --text: {TEXT}; --muted: {MUTED}; --subtle: {SUBTLE}; --accent: {ACCENT}; --good: {GOOD}; --bad: {BAD};
  --display: {FONT_DISPLAY}; --body: {FONT_BODY};
  --r-sm: 4px; --r-md: 8px; --r-lg: 12px;
  --s-1: .25rem; --s-2: .5rem; --s-3: 1rem; --s-4: 1.5rem; --s-5: 2.5rem;
}}
html, body, [class*="css"], .stApp {{ font-family: var(--body); font-variant-numeric: tabular-nums; }}
.stApp {{ background: var(--bg); color: var(--text); }}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ visibility: hidden; }}
/* the header stays (transparent) because it holds the button that reopens the collapsed sidebar */
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {{ color: var(--text); }}
[data-testid="stExpandSidebarButton"] {{ visibility: visible !important; border: 1px solid var(--line-strong); border-radius: var(--r-md); background: var(--surface); }}
.block-container {{ padding: 2rem 2.5rem 3rem; max-width: 1360px; }}
:focus-visible {{ outline: 2px solid var(--accent) !important; outline-offset: 2px; }}

/* sidebar */
section[data-testid="stSidebar"] {{ background: var(--surface); border-right: 1px solid var(--line); }}
section[data-testid="stSidebar"] > div {{ padding-top: var(--s-2); }}
.brand {{ display: flex; align-items: center; gap: 10px; margin-bottom: var(--s-3); }}
.brand span {{ font-family: var(--display); font-weight: 800; font-size: 1.25rem; letter-spacing: .04em; font-stretch: 85%; }}
.side-label {{ font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: var(--s-3) 0 var(--s-2); }}
.facts {{ display: grid; grid-template-columns: auto 1fr; gap: var(--s-2) .75rem; font-size: .8rem; margin-top: var(--s-4); }}
.facts dt {{ color: var(--subtle); }} .facts dd {{ margin: 0; }}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{ background: var(--surface-2); border-color: var(--line-strong); min-height: 44px; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{ min-height: 44px; padding: 0 .75rem; border: 1px solid var(--line-strong);
    border-radius: var(--r-md); margin-bottom: var(--s-2); align-items: center; }}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{ border-color: var(--accent); background: rgba(255,183,3,.12); font-weight: 600; }}

/* page header */
.page-head {{ margin-bottom: var(--s-4); }}
.eyebrow {{ margin: 0 0 6px; font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }}
.page-head h1 {{ margin: 0; font-family: var(--display); font-size: clamp(1.9rem, 4.5vw, 2.75rem); line-height: 1.05; font-weight: 800; font-stretch: 85%; padding: 0; }}
.page-head p {{ margin: var(--s-2) 0 0; color: var(--muted); }}

/* tabs as section navigation */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--line); overflow-x: auto; }}
.stTabs [data-baseweb="tab"] {{ min-height: 44px; padding: 0 1rem; font-weight: 500; color: var(--muted); white-space: nowrap; }}
.stTabs [aria-selected="true"] {{ color: var(--text) !important; font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--accent); height: 2px; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: var(--s-4); }}

/* KPI widgets */
.kpi {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 20px 20px 18px;
       display: flex; flex-direction: column; gap: var(--s-2); height: 100%; box-sizing: border-box; margin-bottom: var(--s-3); }}
.kpi .l {{ font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
.kpi .v {{ display: flex; align-items: baseline; gap: 6px; }}
.kpi .v b {{ font-family: var(--display); font-size: 2.5rem; line-height: 1.05; font-weight: 700; font-stretch: 90%; }}
.kpi .v i {{ font-style: normal; font-size: .95rem; color: var(--muted); }}
.kpi .d {{ display: flex; align-items: center; gap: var(--s-2); font-size: .82rem; color: var(--muted); flex-wrap: wrap; }}
.pill {{ padding: 1px 8px; border: 1px solid currentColor; border-radius: 999px; font-weight: 700; }}
.kpi.sm {{ padding: 14px 16px; gap: var(--s-1); }}
.kpi.sm .v b {{ font-size: 1.65rem; line-height: 1.15; }}
.kpi.sm .d {{ font-size: .78rem; }}
.kpi.sm .w {{ font-weight: 700; }}
.good {{ color: var(--good); }} .bad {{ color: var(--bad); }} .neutral {{ color: var(--muted); }}

/* chart / table cards (st.container(border=True, key="card_*")) */
[class*="st-key-card"] {{ background: var(--surface); border: 1px solid var(--line) !important; border-radius: var(--r-lg); padding: var(--s-4); }}
[class*="st-key-card"] h4 {{ margin: 0; font-size: 1.25rem; font-weight: 600; padding: 0; }}
[class*="st-key-alt"] {{ background: var(--surface-2); }}
.cap {{ margin: var(--s-1) 0 var(--s-2); font-size: .82rem; color: var(--muted); }}
.note {{ color: var(--subtle); font-size: .82rem; }}
.insights {{ margin: var(--s-3) 0 0; padding-left: 1.25rem; display: flex; flex-direction: column; gap: .75rem; color: var(--muted); }}
.insights strong {{ color: var(--text); }}
[data-testid="stDataFrame"] {{ border: 1px solid var(--line); border-radius: var(--r-md); overflow: hidden; }}

@media (max-width: 900px) {{ .block-container {{ padding: 1.25rem 1rem 2rem; }} }}
@media (max-width: 640px) {{ .kpi .v b {{ font-size: 2rem; }} .kpi.sm .v b {{ font-size: 1.4rem; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; scroll-behavior: auto !important; }} }}
</style>
"""

WORD = {"good": "Better", "bad": "Worse", "neutral": "Neutral"}   # the verdict is never conveyed by colour alone


def kpi(label: str, value: str, unit: str = "", delta: str = "", tone: str = "neutral", small: bool = False) -> str:
    unit_html = f"<i>{unit}</i>" if unit else ""
    if small:
        word = f'<span class="w {tone}">{WORD[tone]}</span>'
    else:
        word = f'<span class="pill {tone}">{WORD[tone]}</span>'
    return (f'<section class="kpi{" sm" if small else ""}" aria-label="{label}"><div class="l">{label}</div>'
            f'<div class="v"><b>{value}</b>{unit_html}</div><div class="d">{word}<span>{delta}</span></div></section>')


def page_header(eyebrow: str, title: str, subtitle: str) -> str:
    return f'<header class="page-head"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{subtitle}</p></header>'


def brand() -> str:
    return ('<div class="brand"><svg aria-hidden="true" width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#ffb703" '
            'stroke-width="2" stroke-linecap="round"><circle cx="14" cy="15" r="10"/><path d="M14 15V9M14 15l4 3M11 3h6"/></svg>'
            '<span>POCKET CLOCK</span></div>')


def card_title(title: str, caption: str = "") -> str:
    return f"<h4>{title}</h4>" + (f'<p class="cap">{caption}</p>' if caption else "")
