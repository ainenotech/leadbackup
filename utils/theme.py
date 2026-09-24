"""Theme utility module for AINeotechnology Outreach & Intelligence Suite.
Provides comprehensive Light & Dark mode design systems, CSS variables,
Google Fonts typography (Outfit, Inter, JetBrains Mono), and Plotly figure theme wrappers.
"""

from typing import Optional
import streamlit as st
import plotly.graph_objects as go


def get_current_theme() -> str:
    """Returns 'dark' or 'light' based on session state, default is 'light'."""
    if "app_theme" not in st.session_state:
        st.session_state.app_theme = "light"
    return st.session_state.app_theme


def is_dark_mode() -> bool:
    """Convenience helper to check if dark mode is active."""
    return get_current_theme() == "dark"


def set_theme(theme_name: str) -> None:
    """Updates the active theme in session state."""
    if theme_name in {"dark", "light"}:
        st.session_state.app_theme = theme_name


def apply_chart_theme(fig: go.Figure, is_dark: Optional[bool] = None) -> go.Figure:
    """Adapts any Plotly figure to the active UI theme with crisp fonts,
    transparent backgrounds, and theme-matched axes and grids.
    """
    if is_dark is None:
        is_dark = is_dark_mode()

    text_color = "#F9FAFB" if is_dark else "#0F172A"
    grid_color = "#1F2937" if is_dark else "#E2E8F0"
    sub_color = "#9CA3AF" if is_dark else "#64748B"
    template = "plotly_dark" if is_dark else "plotly_white"

    fig.update_layout(
        template=template,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=text_color, size=12),
        hoverlabel=dict(
            bgcolor="#1F2937" if is_dark else "#FFFFFF",
            font=dict(color="#F9FAFB" if is_dark else "#0F172A", family="Inter, sans-serif", size=12),
            bordercolor="#374151" if is_dark else "#CBD5E1",
        ),
    )

    fig.update_xaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
        tickfont=dict(color=sub_color, size=11, family="Inter, sans-serif"),
    )
    fig.update_yaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
        tickfont=dict(color=sub_color, size=11, family="JetBrains Mono, monospace"),
    )
    return fig


def get_complete_theme_css(is_dark: bool) -> str:
    """Generates the master CSS for the entire dashboard with complete
    Light and Dark mode tokens, modern typography, and all 124 component classes.
    """
    if is_dark:
        tokens = """
    --bg-canvas: #090D16;
    --bg-surface: #111827;
    --bg-elevated: #1F2937;
    --bg-nested: #161F30;
    --border-subtle: #1F2937;
    --border-strong: #374151;
    --border-highlight: #4B5563;
    --text-primary: #F9FAFB;
    --text-secondary: #E5E7EB;
    --text-muted: #9CA3AF;
    --text-micro: #6B7280;
    --brand-primary: #3B82F6;
    --brand-hover: #2563EB;
    --brand-soft: rgba(59, 130, 246, 0.16);
    --brand-border: rgba(59, 130, 246, 0.35);
    --teal-primary: #14B8A6;
    --teal-soft: rgba(20, 184, 166, 0.16);
    --teal-border: rgba(20, 184, 166, 0.35);
    --amber-primary: #F59E0B;
    --amber-soft: rgba(245, 158, 11, 0.16);
    --amber-border: rgba(245, 158, 11, 0.35);
    --danger-primary: #EF4444;
    --danger-soft: rgba(239, 68, 68, 0.16);
    --danger-border: rgba(239, 68, 68, 0.35);
    --purple-primary: #8B5CF6;
    --purple-soft: rgba(139, 92, 246, 0.16);
    --purple-border: rgba(139, 92, 246, 0.35);
    --card-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4), 0 2px 6px -1px rgba(0, 0, 0, 0.2);
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.25);
    --shadow-md: 0 4px 14px -2px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.55);
    --input-bg: #1F2937;
    --input-border: #374151;
    --input-color: #F9FAFB;
    --sidebar-bg: #0D1322;
        """
        badge_styles = """
    .badge-sent      { background: rgba(20, 184, 166, 0.18) !important; color: #5EEAD4 !important; border: 1px solid rgba(20, 184, 166, 0.35) !important; }
    .badge-drafted   { background: rgba(245, 158, 11, 0.18) !important; color: #FCD34D !important; border: 1px solid rgba(245, 158, 11, 0.35) !important; }
    .badge-pending   { background: rgba(107, 114, 128, 0.18) !important; color: #D1D5DB !important; border: 1px solid rgba(107, 114, 128, 0.35) !important; }
    .badge-rejected  { background: rgba(239, 68, 68, 0.18) !important; color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.35) !important; }
    .badge-failed    { background: rgba(239, 68, 68, 0.18) !important; color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.35) !important; }
    .badge-replied   { background: rgba(20, 184, 166, 0.18) !important; color: #5EEAD4 !important; border: 1px solid rgba(20, 184, 166, 0.35) !important; }
    .badge-scheduled { background: rgba(139, 92, 246, 0.18) !important; color: #C4B5FD !important; border: 1px solid rgba(139, 92, 246, 0.35) !important; }
        """
    else:
        tokens = """
    --bg-canvas: #F8FAFC;
    --bg-surface: #FFFFFF;
    --bg-elevated: #F1F5F9;
    --bg-nested: #F8FAFC;
    --border-subtle: #E2E8F0;
    --border-strong: #CBD5E1;
    --border-highlight: #94A3B8;
    --text-primary: #0F172A;
    --text-secondary: #334155;
    --text-muted: #64748B;
    --text-micro: #94A3B8;
    --brand-primary: #2563EB;
    --brand-hover: #1D4ED8;
    --brand-soft: #EFF6FF;
    --brand-border: #BFDBFE;
    --teal-primary: #0D9488;
    --teal-soft: #F0FDFA;
    --teal-border: #99F6E4;
    --amber-primary: #D97706;
    --amber-soft: #FFFBEB;
    --amber-border: #FDE68A;
    --danger-primary: #DC2626;
    --danger-soft: #FEF2F2;
    --danger-border: #FECACA;
    --purple-primary: #7C3AED;
    --purple-soft: #F5F3FF;
    --purple-border: #DDD6FE;
    --card-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02);
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02);
    --shadow-md: 0 4px 12px -2px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
    --input-bg: #FFFFFF;
    --input-border: #CBD5E1;
    --input-color: #0F172A;
    --sidebar-bg: #FFFFFF;
        """
        badge_styles = """
    .badge-sent      { background: #F0FDFA !important; color: #0F766E !important; border: 1px solid #99F6E4 !important; }
    .badge-drafted   { background: #FFFBEB !important; color: #92400E !important; border: 1px solid #FDE68A !important; }
    .badge-pending   { background: #F4F4F5 !important; color: #27272A !important; border: 1px solid #E4E4E7 !important; }
    .badge-rejected  { background: #FEF2F2 !important; color: #991B1B !important; border: 1px solid #FECACA !important; }
    .badge-failed    { background: #FEF2F2 !important; color: #991B1B !important; border: 1px solid #FECACA !important; }
    .badge-replied   { background: #F0FDFA !important; color: #0F766E !important; border: 1px solid #99F6E4 !important; }
    .badge-scheduled { background: #F5F3FF !important; color: #5B21B6 !important; border: 1px solid #DDD6FE !important; }
        """

    return f"""
<style>
/* ── Modern Premium Typography: Outfit + Inter + JetBrains Mono ── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {{
{tokens}
    --radius-lg: 12px;
    --radius-md: 8px;
    --radius-sm: 6px;
}}

/* ── Global Layout & Resets ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    color: var(--text-primary) !important;
    background-color: var(--bg-canvas) !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    letter-spacing: -0.01em !important;
    line-height: 1.6 !important;
}}

/* ── Crisp Executive Headings (Outfit) ── */
h1, h2, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2 {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    color: var(--text-primary) !important;
    line-height: 1.25 !important;
}}

h3, h4, h5, h6, [data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4 {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em !important;
    color: var(--text-primary) !important;
}}

p, [data-testid="stMarkdownContainer"] p {{
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.01em !important;
    line-height: 1.6 !important;
    color: var(--text-secondary);
}}

code, pre, .mono-text, .kpi-number, [data-testid="stMetricValue"] {{
    font-family: 'JetBrains Mono', ui-monospace, Menlo, Monaco, Consolas, monospace !important;
    font-feature-settings: "zero", "tnum" !important;
}}

[data-testid="stHeader"] {{
    background: transparent !important;
}}

[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],
.stDeployButton,
#MainMenu, footer {{
    display: none !important;
}}

/* ── Sidebar Styling ── */
section[data-testid="stSidebar"] {{
    background-color: var(--sidebar-bg) !important;
    border-right: 1px solid var(--border-subtle) !important;
    box-shadow: 2px 0 14px rgba(0, 0, 0, {'0.3' if is_dark else '0.02'}) !important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    padding-top: 1rem !important;
    padding-left: 0.9rem !important;
    padding-right: 0.9rem !important;
}}

/* Sidebar Brand Card */
.sidebar-brand-card {{
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 14px 16px;
    background: {'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)' if is_dark else 'linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%)'} !important;
    border: 1px solid {'#1F2937' if is_dark else '#E2E8F0'} !important;
    border-radius: var(--radius-md);
    margin-bottom: 12px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
}}
.sidebar-brand-card:hover {{
    border-color: var(--brand-primary);
    box-shadow: 0 4px 16px rgba(59, 130, 246, {'0.25' if is_dark else '0.12'});
}}
.sidebar-brand-logo-img {{
    height: 32px;
    max-width: 100%;
    width: auto;
    object-fit: contain;
    display: block;
}}
.sidebar-brand-subtitle {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    margin: 8px 0 0 0 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
}}
.sidebar-brand-dot {{
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #10B981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
}}

/* Sidebar Nav Buttons */
section[data-testid="stSidebar"] .stButton > button {{
    font-family: 'Inter', sans-serif !important;
    width: 100%;
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-secondary) !important;
    text-align: left !important;
    padding: 9px 12px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    justify-content: flex-start !important;
    margin-bottom: 3px !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border-color: var(--border-strong) !important;
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: var(--brand-soft) !important;
    color: {'#60A5FA' if is_dark else 'var(--brand-primary)'} !important;
    font-weight: 600 !important;
    border: 1px solid var(--brand-border) !important;
    border-left: 4px solid var(--brand-primary) !important;
}}

/* Sidebar Health Card */
.sidebar-health-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 12px 14px;
    margin-top: 14px;
    box-shadow: var(--shadow-sm);
}}
.sidebar-health-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}}
.sidebar-health-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--text-muted);
    padding: 3px 0;
}}
.health-pill {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
}}
.health-pill-green {{
    background: {'rgba(16, 185, 129, 0.2)' if is_dark else '#ECFDF5'};
    color: {'#34D399' if is_dark else '#047857'};
    border: 1px solid {'rgba(16, 185, 129, 0.35)' if is_dark else '#A7F3D0'};
}}

/* ── Top Executive Banner ── */
.top-header-banner {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 24px;
    margin-bottom: 22px;
    box-shadow: var(--shadow-sm);
}}
.top-header-title {{
    font-family: 'Outfit', sans-serif !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.025em !important;
    line-height: 1.25 !important;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.top-header-desc {{
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    color: var(--text-muted) !important;
    margin: 6px 0 0 0;
    line-height: 1.5 !important;
}}

/* ── KPI Grid & KPI Cards ── */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 24px;
    width: 100%;
}}
@media (max-width: 1100px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 680px) {{
    .kpi-grid {{ grid-template-columns: 1fr; }}
}}
.kpi-grid-4 {{
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 16px !important;
    margin-bottom: 22px !important;
    width: 100% !important;
}}
@media (max-width: 1100px) {{
    .kpi-grid-4 {{ grid-template-columns: repeat(2, 1fr) !important; }}
}}
@media (max-width: 600px) {{
    .kpi-grid-4 {{ grid-template-columns: 1fr !important; }}
}}
.kpi-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 22px 18px 22px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 142px;
}}
.kpi-card:hover {{
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    border-color: var(--border-strong);
}}
.kpi-top-bar {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
}}
.kpi-bar-blue   {{ background: linear-gradient(90deg, #3B82F6, #60A5FA); }}
.kpi-bar-amber  {{ background: linear-gradient(90deg, #F59E0B, #FCD34D); }}
.kpi-bar-teal   {{ background: linear-gradient(90deg, #14B8A6, #2DD4BF); }}
.kpi-bar-cyan   {{ background: linear-gradient(90deg, #06B6D4, #67E8F9); }}
.kpi-bar-purple {{ background: linear-gradient(90deg, #8B5CF6, #C4B5FD); }}
.kpi-bar-rose   {{ background: linear-gradient(90deg, #F43F5E, #FDA4AF); }}

.kpi-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}}
.kpi-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.kpi-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
    margin: 4px 0 6px 0;
    letter-spacing: -0.02em;
}}
.kpi-footer {{
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
}}
.kpi-icon-box {{
    width: 36px !important;
    height: 36px !important;
    border-radius: 9px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 17px !important;
    flex-shrink: 0 !important;
}}
.kpi-micro {{
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    letter-spacing: -0.01em !important;
    margin-top: 4px !important;
}}
.kpi-pill {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    padding: 2.5px 8px !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
}}
.kpi-pill-blue   {{ background: {'rgba(59, 130, 246, 0.16)' if is_dark else '#EFF6FF'} !important; color: {'#93C5FD' if is_dark else '#1D4ED8'} !important; border: 1px solid {'rgba(59, 130, 246, 0.35)' if is_dark else '#BFDBFE'} !important; }}
.kpi-pill-amber  {{ background: {'rgba(245, 158, 11, 0.16)' if is_dark else '#FFFBEB'} !important; color: {'#FCD34D' if is_dark else '#B45309'} !important; border: 1px solid {'rgba(245, 158, 11, 0.35)' if is_dark else '#FDE68A'} !important; }}
.kpi-pill-teal   {{ background: {'rgba(20, 184, 166, 0.16)' if is_dark else '#F0FDFA'} !important; color: {'#5EEAD4' if is_dark else '#0F766E'} !important; border: 1px solid {'rgba(20, 184, 166, 0.35)' if is_dark else '#99F6E4'} !important; }}
.kpi-pill-cyan   {{ background: {'rgba(6, 182, 212, 0.16)' if is_dark else '#ECFEFF'} !important; color: {'#67E8F9' if is_dark else '#0E7490'} !important; border: 1px solid {'rgba(6, 182, 212, 0.35)' if is_dark else '#A5F3FC'} !important; }}
.kpi-pill-purple {{ background: {'rgba(139, 92, 246, 0.16)' if is_dark else '#F5F3FF'} !important; color: {'#C4B5FD' if is_dark else '#6D28D9'} !important; border: 1px solid {'rgba(139, 92, 246, 0.35)' if is_dark else '#DDD6FE'} !important; }}
.kpi-pill-rose   {{ background: {'rgba(244, 63, 94, 0.16)' if is_dark else '#FFF1F2'} !important; color: {'#FDA4AF' if is_dark else '#BE123C'} !important; border: 1px solid {'rgba(244, 63, 94, 0.35)' if is_dark else '#FECDD3'} !important; }}

/* ── Visual Conversion Funnel Card ── */
.funnel-container {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 22px 24px 20px 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow-sm);
}}
.funnel-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}}
.funnel-title {{
    font-family: 'Outfit', sans-serif !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.015em !important;
    display: flex;
    align-items: center;
    gap: 10px;
}}
.funnel-stages {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
}}
@media (max-width: 1024px) {{
    .funnel-stages {{ grid-template-columns: repeat(3, 1fr); }}
}}
.funnel-stage {{
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 12px 10px;
    text-align: center;
    transition: all 0.2s ease;
}}
.funnel-stage:hover {{
    border-color: var(--border-strong);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
}}
.funnel-stage-name {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-bottom: 4px;
}}
.funnel-stage-val {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 2px;
}}
.funnel-stage-sub {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
}}

/* ── Modern Premium Chart Containers ── */
.chart-box {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 20px 22px 16px 22px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 20px;
    transition: all 0.2s ease;
}}
.chart-box:hover {{
    border-color: var(--border-strong);
    box-shadow: var(--shadow-md);
}}
.chart-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}}
.chart-title-group h3 {{
    font-family: 'Outfit', sans-serif !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
    letter-spacing: -0.015em !important;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.chart-title-group p {{
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    color: var(--text-muted) !important;
    margin: 3px 0 0 0 !important;
}}

/* ── Native Streamlit Bordered Containers Styled as Premium Cards ── */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-sm) !important;
    padding: 18px 20px !important;
    transition: all 0.2s ease !important;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color: var(--border-strong) !important;
    box-shadow: var(--shadow-md) !important;
}}

/* ── Superhuman Email Client Preview Card ── */
.email-preview-window {{
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    overflow: hidden;
    margin: 16px 0;
}}
.email-preview-mac-header {{
    background: var(--bg-elevated);
    padding: 10px 16px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    gap: 6px;
}}
.mac-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
.dot-red   {{ background: #EF4444; }}
.dot-amber {{ background: #F59E0B; }}
.dot-green {{ background: #10B981; }}

.email-preview-meta {{
    padding: 14px 18px;
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-elevated);
}}
.email-preview-meta-row {{
    display: flex;
    align-items: center;
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 4px;
}}
.email-preview-meta-label {{
    width: 60px;
    font-weight: 600;
    color: var(--text-muted);
}}
.email-preview-subject {{
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    margin-top: 6px;
}}
.email-preview-body {{
    padding: 18px 22px;
    font-size: 14px;
    line-height: 1.55;
    color: var(--text-primary);
    background: var(--bg-surface);
    word-break: break-word;
}}

/* ── Live Reply & Conversation Thread Feed ── */
.chat-thread-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
}}
.chat-thread-card:hover {{
    border-color: var(--border-strong);
    box-shadow: var(--shadow-md);
}}
.chat-thread-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 10px;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 10px;
}}
.chat-bubble-inbound {{
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px 12px 12px 2px;
    padding: 12px 14px;
    margin-bottom: 10px;
    color: var(--text-primary);
}}
.chat-bubble-outbound {{
    background: {'rgba(20, 184, 166, 0.12)' if is_dark else '#F0FDFA'};
    border: 1px solid {'rgba(20, 184, 166, 0.25)' if is_dark else '#CCFBF1'};
    border-radius: 12px 12px 2px 12px;
    padding: 12px 14px;
    color: var(--text-primary);
}}

/* ── Executive Analytics Suite Styles ── */
.analytics-feature-box {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
}}
.analytics-feature-box:hover {{
    border-color: var(--border-strong);
    box-shadow: var(--shadow-md);
}}
.feature-title-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.feature-title-left {{
    display: flex;
    align-items: center;
    gap: 12px;
}}
.feature-icon-bubble {{
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: var(--brand-soft);
    color: var(--brand-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}}
.feature-name-text {{
    font-family: 'Outfit', sans-serif !important;
    font-size: 15.5px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.015em;
    margin: 0;
}}
.feature-explanation-sub {{
    font-size: 12.5px;
    color: var(--text-muted);
    margin: 2px 0 0 0;
}}
.feature-tag-pill {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
}}
.feature-status-active {{
    background: {'rgba(20, 184, 166, 0.2)' if is_dark else '#F0FDFA'};
    color: {'#5EEAD4' if is_dark else '#0F766E'};
    border: 1px solid {'rgba(20, 184, 166, 0.35)' if is_dark else '#99F6E4'};
}}

/* ── Badges & Chips ── */
.badge {{
    font-family: 'JetBrains Mono', monospace !important;
    display: inline-flex;
    align-items: center;
    padding: 2.5px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    line-height: 1.3;
    letter-spacing: 0.02em;
}}
{badge_styles}

/* ── Form Inputs, Textarea, Select ── */
label, [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] p {{
    color: var(--text-primary) !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    margin-bottom: 5px !important;
}}
div[data-baseweb="input"],
div[data-baseweb="textarea"],
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    background-color: var(--input-bg) !important;
    color: var(--input-color) !important;
    -webkit-text-fill-color: var(--input-color) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: var(--radius-sm) !important;
    font-size: 14px !important;
    box-shadow: var(--shadow-sm) !important;
}}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {{
    border-color: var(--brand-primary) !important;
    box-shadow: 0 0 0 3px {'rgba(59, 130, 246, 0.25)' if is_dark else 'rgba(37, 99, 235, 0.15)'} !important;
}}
[data-testid="stSelectbox"] [data-baseweb="select"] {{
    background: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--input-color) !important;
}}
[data-testid="stSelectbox"] [data-baseweb="select"] * {{
    color: var(--input-color) !important;
}}

/* ── Buttons (Elevated Executive Aesthetics) ── */
.stButton > button {{
    border-radius: 9px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 8px 18px !important;
    letter-spacing: -0.01em !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 7px !important;
}}
.stButton > button[kind="primary"] {{
    background: {'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)' if is_dark else 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)'} !important;
    border: 1px solid {'rgba(96, 165, 250, 0.5)' if is_dark else '#1D4ED8'} !important;
    color: #FFFFFF !important;
    box-shadow: {'0 2px 8px rgba(37, 99, 235, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2)' if is_dark else '0 2px 6px rgba(37, 99, 235, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.25)'} !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: {'linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%)' if is_dark else 'linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%)'} !important;
    border-color: {'#93C5FD' if is_dark else '#1E40AF'} !important;
    transform: translateY(-1px) !important;
    box-shadow: {'0 6px 20px rgba(59, 130, 246, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.3)' if is_dark else '0 6px 18px rgba(37, 99, 235, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.3)'} !important;
}}
.stButton > button[kind="primary"]:active {{
    transform: translateY(0px) !important;
    box-shadow: 0 1px 3px rgba(37, 99, 235, 0.2) !important;
}}
.stButton > button[kind="secondary"] {{
    background: {'linear-gradient(180deg, #1F2937 0%, #161F30 100%)' if is_dark else 'linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%)'} !important;
    color: {'#F3F4F6' if is_dark else '#1E293B'} !important;
    border: 1px solid {'#374151' if is_dark else '#CBD5E1'} !important;
    box-shadow: {'0 1px 3px rgba(0, 0, 0, 0.3)' if is_dark else '0 1px 2px rgba(0, 0, 0, 0.04)'} !important;
}}
.stButton > button[kind="secondary"]:hover {{
    background: {'linear-gradient(180deg, #374151 0%, #1F2937 100%)' if is_dark else 'linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%)'} !important;
    border-color: {'#60A5FA' if is_dark else '#94A3B8'} !important;
    color: {'#FFFFFF' if is_dark else '#0F172A'} !important;
    transform: translateY(-1px) !important;
    box-shadow: {'0 4px 12px rgba(0, 0, 0, 0.4)' if is_dark else '0 4px 12px rgba(0, 0, 0, 0.06)'} !important;
}}
.stButton > button[kind="secondary"]:active {{
    transform: translateY(0px) !important;
}}

/* ── Luxury Glassmorphic Feature Cards (Whole Box Clickable) ── */
.glass-feature-card {{
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    background: {'linear-gradient(135deg, rgba(17, 24, 39, 0.88) 0%, rgba(31, 41, 55, 0.68) 100%)' if is_dark else 'linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.85) 100%)'} !important;
    backdrop-filter: blur(16px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
    border: 1px solid {'rgba(55, 65, 81, 0.85)' if is_dark else 'rgba(226, 232, 240, 0.9)'} !important;
    border-radius: 16px !important;
    padding: 22px 24px !important;
    margin-bottom: 18px !important;
    text-decoration: none !important;
    color: inherit !important;
    cursor: pointer !important;
    box-shadow: {'0 4px 20px -2px rgba(0, 0, 0, 0.4), inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)' if is_dark else '0 4px 20px -2px rgba(15, 23, 42, 0.05), inset 0 1px 1px 0 rgba(255, 255, 255, 0.95)'} !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
    min-height: 148px !important;
}}
.glass-feature-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3.5px;
    background: linear-gradient(90deg, #3B82F6 0%, #14B8A6 50%, #8B5CF6 100%);
    opacity: 0;
    transition: opacity 0.25s ease;
}}
.glass-feature-card:hover {{
    transform: translateY(-4px) !important;
    border-color: {'rgba(96, 165, 250, 0.6)' if is_dark else 'rgba(37, 99, 235, 0.45)'} !important;
    box-shadow: {'0 16px 36px -4px rgba(0, 0, 0, 0.6), 0 0 20px rgba(59, 130, 246, 0.25)' if is_dark else '0 16px 36px -4px rgba(37, 99, 235, 0.12), inset 0 1px 2px 0 rgba(255, 255, 255, 1)'} !important;
    text-decoration: none !important;
}}
.glass-feature-card:hover::before {{
    opacity: 1;
}}
.glass-feature-card:hover .glass-card-title {{
    color: {'#60A5FA' if is_dark else '#2563EB'} !important;
}}
.glass-feature-card:hover .glass-arrow-circle {{
    background: {'#3B82F6' if is_dark else '#2563EB'} !important;
    color: #FFFFFF !important;
    transform: translateX(4px) !important;
    border-color: {'#3B82F6' if is_dark else '#2563EB'} !important;
}}
.glass-card-header {{
    display: flex !important;
    justify-content: space-between !important;
    align-items: flex-start !important;
    margin-bottom: 10px !important;
}}
.glass-card-left {{
    display: flex !important;
    align-items: flex-start !important;
    gap: 14px !important;
}}
.glass-icon-box {{
    width: 44px !important;
    height: 44px !important;
    border-radius: 12px !important;
    background: {'linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.8) 100%)' if is_dark else 'linear-gradient(135deg, rgba(239, 246, 255, 0.95) 0%, rgba(219, 234, 254, 0.8) 100%)'} !important;
    border: 1px solid {'rgba(59, 130, 246, 0.35)' if is_dark else 'rgba(191, 219, 254, 0.8)'} !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 22px !important;
    flex-shrink: 0 !important;
    box-shadow: {'0 2px 8px rgba(0, 0, 0, 0.3)' if is_dark else '0 2px 8px rgba(37, 99, 235, 0.08)'} !important;
}}
.glass-card-title {{
    font-family: 'Outfit', sans-serif !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.015em !important;
    margin: 0 !important;
    transition: color 0.2s ease !important;
}}
.glass-card-desc {{
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: var(--text-muted) !important;
    margin: 4px 0 0 0 !important;
    line-height: 1.5 !important;
}}
.glass-card-footer {{
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    margin-top: 14px !important;
    padding-top: 10px !important;
    border-top: 1px solid {'rgba(55, 65, 81, 0.6)' if is_dark else 'rgba(226, 232, 240, 0.8)'} !important;
}}
.glass-explore-text {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    color: {'#93C5FD' if is_dark else '#2563EB'} !important;
    letter-spacing: -0.01em !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
}}
.glass-arrow-circle {{
    width: 26px !important;
    height: 26px !important;
    border-radius: 50% !important;
    background: {'#1F2937' if is_dark else '#FFFFFF'} !important;
    border: 1px solid {'#374151' if is_dark else '#E2E8F0'} !important;
    color: {'#93C5FD' if is_dark else '#2563EB'} !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}}
.card-stretch-link {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100% !important;
    height: 100% !important;
    z-index: 15 !important;
    cursor: pointer !important;
    background: transparent !important;
    text-decoration: none !important;
    display: block !important;
    border: none !important;
    outline: none !important;
}}

/* ── Action Toolbar Card ── */
.action-toolbar-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 16px 20px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow-sm);
    gap: 16px;
    flex-wrap: wrap;
}}
.action-toolbar-status {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.action-toolbar-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10B981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
    display: inline-block;
}}

/* ── Consultation Booking Cards ── */
.booking-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    margin-bottom: 16px;
    height: 100%;
}}
.booking-card:hover {{
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    border-color: var(--border-strong);
}}
.booking-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}}
.booking-lead-profile {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.booking-avatar {{
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: var(--brand-soft);
    color: var(--brand-primary);
    font-weight: 700;
    font-size: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.booking-name-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
}}
.booking-company-badge {{
    font-size: 12px;
    color: var(--text-muted);
}}
.booking-slot-highlight {{
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0;
}}
.booking-slot-text {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--brand-primary);
}}
.booking-info-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 8px 0;
}}
.booking-info-item {{
    font-size: 12px;
}}
.booking-info-label {{
    color: var(--text-muted);
    font-size: 11px;
    text-transform: uppercase;
}}
.booking-info-val {{
    color: var(--text-primary);
    font-weight: 600;
}}
.booking-note-box {{
    background: var(--bg-nested);
    border-left: 3px solid var(--brand-primary);
    padding: 8px 10px;
    font-size: 12px;
    color: var(--text-secondary);
    border-radius: 0 6px 6px 0;
    margin: 8px 0;
}}
.teams-join-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%);
    color: #FFFFFF !important;
    font-weight: 600;
    font-size: 12.5px;
    border-radius: var(--radius-sm);
    text-decoration: none !important;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
    transition: all 0.2s ease;
}}
.teams-join-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.45);
}}

/* ── Export & Download Button ── */
.btn-export-download {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 9px 16px;
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    transition: all 0.15s ease !important;
    box-shadow: var(--shadow-sm);
}}
.btn-export-download:hover {{
    border-color: var(--brand-primary) !important;
    color: var(--brand-primary) !important;
    background-color: var(--bg-elevated) !important;
    box-shadow: var(--shadow-md);
}}

/* ── Data Tables ── */
[data-testid="stDataFrame"] {{
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-subtle) !important;
    background: var(--bg-surface) !important;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}}

/* ── Alerts & Expanders ── */
[data-testid="stAlert"] {{
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm) !important;
    background-color: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-subtle) !important;
}}
[data-testid="stExpander"] {{
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
}}
[data-testid="stExpander"] summary {{
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
    border-bottom: 1px solid var(--border-subtle) !important;
    background: transparent !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    padding: 8px 14px !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    border: none !important;
    background: transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color: var(--brand-primary) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid var(--brand-primary) !important;
    background: transparent !important;
}}

/* ── Dialog Modals ── */
div[data-testid="stModal"] [data-testid="stModalContent"] {{
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-lg) !important;
}}
</style>
"""
