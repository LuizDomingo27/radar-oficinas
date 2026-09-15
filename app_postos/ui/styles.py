"""
ui/styles.py
-------------
Centraliza todo o CSS customizado da aplicacao. Tema claro (light)
alinhado ao padrao visual do SO, com cards brancos e radial-gradient
teal partindo do topo — identico ao design de referencia.

O tema usa CSS Custom Properties espelhando `core.config.Theme`,
de modo que qualquer ajuste de paleta deve ser feito nos dois lugares.
"""

from __future__ import annotations

from app_postos.core.config import Theme


def build_css() -> str:
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

:root {{
    --bg-primary:   {Theme.BG_PRIMARY};
    --bg-secondary: {Theme.BG_SECONDARY};
    --card-bg:      {Theme.CARD_BG};
    --card-border:  {Theme.CARD_BORDER};
    --accent:       {Theme.ACCENT};
    --accent-soft:  {Theme.ACCENT_SOFT};
    --accent-glow:  {Theme.ACCENT_GLOW};
    --positive:     {Theme.POSITIVE};
    --negative:     {Theme.NEGATIVE};
    --neutral:      {Theme.NEUTRAL};
    --text-primary: {Theme.TEXT_PRIMARY};
    --text-muted:   {Theme.TEXT_MUTED};
    --font-heading: {Theme.FONT_HEADING};
    --font-body:    {Theme.FONT_BODY};
    --radius-lg: 16px;
    --radius-md: 12px;
    --radius-sm:  8px;
}}

/* ---------- Base ---------- */
html, body, [class*="css"] {{
    font-family: var(--font-body);
}}

.stApp {{
    background: var(--bg-primary);
    color: var(--text-primary);
}}

h1, h2, h3, h4 {{
    font-family: var(--font-heading) !important;
    color: var(--text-primary) !important;
    letter-spacing: 0.2px;
}}

/* ---------- Cabecalho ---------- */
.app-header {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 0.25rem 0 1.25rem 0;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 1.5rem;
}}

.app-header .title-row {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}

.app-header .title-row .icon {{
    font-size: 1.9rem;
}}

.app-header h1 {{
    font-size: 1.65rem;
    margin: 0;
    color: var(--text-primary) !important;
}}

.app-header .subtitle {{
    color: var(--text-muted);
    font-size: 0.92rem;
    margin-top: 2px;
}}

/* ---------- Grid de Cards (KPIs) ---------- */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
    margin-bottom: 1.6rem;
}}

/* Card: superfície escura com radial-gradient teal partindo do topo */
.kpi-card {{
    background: var(--card-bg);
    background-image: radial-gradient(
        ellipse 120% 90% at 50% -15%,
        var(--accent-glow) 0%,
        var(--accent-soft) 45%,
        transparent 70%
    );
    border: 1px solid var(--card-border);
    border-radius: var(--radius-lg);
    padding: 1.1rem 1.25rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 12px 34px -18px rgba(0,0,0,0.65);
}}

.kpi-card::before {{ display: none; }}
.kpi-card::after  {{ display: none; }}

.kpi-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 26px rgba(0,0,0,0.55), 0 0 24px var(--accent-soft);
}}

/* Icone ✦ + label — teal, uppercase */
.kpi-card .kpi-label {{
    display: flex;
    align-items: center;
    gap: 0.28rem;
    font-size: 0.68rem;
    font-family: var(--font-body);
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-bottom: 0.15rem;
}}

.kpi-card .kpi-star {{
    font-size: 0.72rem;
    line-height: 1;
    color: var(--accent);
}}

/* Valor principal — grande, escuro, bold */
.kpi-card .kpi-value {{
    font-family: var(--font-heading);
    font-size: 1.95rem;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}}

/* Delta / variacao */
.kpi-card .kpi-delta {{
    font-size: 0.78rem;
    margin-top: 0.45rem;
    font-weight: 500;
}}

.kpi-delta.positive {{ color: var(--positive); }}
.kpi-delta.negative {{ color: var(--negative); }}
.kpi-delta.neutral  {{ color: var(--neutral); }}

/* ---------- Cartao generico (secoes) ---------- */
.section-card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    padding: 1.1rem 1.25rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}

.section-card h4 {{
    margin-top: 0;
    font-size: 1.02rem;
}}

.delta-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 999px;
    background: var(--accent-soft);
    border: 1px solid var(--card-border);
    font-size: 0.85rem;
    font-weight: 500;
    margin-right: 8px;
}}

/* Pílula da Média (ao lado do seletor de indicador na evolução) */
.media-pill-wrap {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    height: 100%;
}}

.media-pill {{
    display: inline-flex;
    align-items: baseline;
    gap: 7px;
    padding: 5px 14px;
    border-radius: 999px;
    background: var(--accent-soft);
    border: 1px solid rgba(79,208,195,0.35);
    white-space: nowrap;
    font-family: var(--font-body);
}}

.media-pill .mp-label {{
    font-size: 0.64rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--accent);
    font-weight: 700;
}}

.media-pill .mp-value {{
    font-family: var(--font-heading);
    font-weight: 800;
    font-size: 0.95rem;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}}

/* ---------- Sidebar (desativada — navegação e filtros migraram para o topo) ---------- */
section[data-testid="stSidebar"] {{
    display: none !important;
}}
button[data-testid="stSidebarCollapseButton"],
div[data-testid="collapsedControl"] {{
    display: none !important;
}}

/* Aproxima o conteúdo do topo já que não há mais sidebar */
.block-container {{
    padding-top: 3.4rem !important;
}}

/* ---------- Navbar (topo) ---------- */
.app-navbar {{
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding-top: 1.15rem;
}}

.app-navbar .brand-title {{
    font-family: var(--font-heading);
    font-weight: 800;
    font-size: 1.15rem;
    line-height: 1.1;
    color: var(--text-primary);
    letter-spacing: 0.3px;
}}

.app-navbar .brand-sub {{
    font-size: 0.68rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 600;
}}

/* Linha divisória sob a navbar inteira */
.navbar-divider {{
    height: 1px;
    background: linear-gradient(90deg, var(--accent-soft), var(--card-border) 40%, transparent);
    margin: 0.15rem 0 1.4rem 0;
}}

/* ---------- Barra de filtros (topo do dashboard) ---------- */
.filter-bar-header {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0.2rem 0 0.55rem 0;
}}
.filter-bar-header .fb-title {{
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
}}
.filter-bar-header .fb-hint {{
    font-size: 0.74rem;
    color: var(--text-muted);
}}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    border-bottom: 1px solid var(--card-border);
}}

.stTabs [data-baseweb="tab"] {{
    color: var(--text-muted);
    font-family: var(--font-heading);
    font-weight: 500;
    padding: 8px 4px;
}}

.stTabs [aria-selected="true"] {{
    color: var(--accent) !important;
}}

/* ---------- Inputs ---------- */
div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {{
    background-color: var(--bg-secondary) !important;
    border-color: var(--card-border) !important;
}}

.stButton button, .stDownloadButton button {{
    border-radius: var(--radius-sm);
    border: 1px solid var(--card-border);
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    font-family: var(--font-body);
}}

.stButton button:hover, .stDownloadButton button:hover {{
    border-color: var(--accent);
    color: var(--accent);
    background-color: var(--accent-soft);
}}

/* ---------- Botao primario ---------- */
button[data-testid="baseButton-primary"],
button[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #18C99E 0%, #12A882 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid #18C99E !important;
    font-weight: 700 !important;
    font-family: var(--font-heading) !important;
    font-size: 0.97rem !important;
    border-radius: var(--radius-md) !important;
    box-shadow: 0 4px 18px rgba(24,201,158,0.20) !important;
    transition: all 0.2s ease !important;
}}

button[data-testid="baseButton-primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {{
    box-shadow: 0 6px 28px rgba(24,201,158,0.38) !important;
    transform: translateY(-1px) !important;
}}

/* ---------- Responsividade ---------- */
@media (max-width: 640px) {{
    .kpi-grid {{
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 10px;
    }}
    .kpi-card .kpi-value {{
        font-size: 1.5rem;
    }}
    .app-header h1 {{
        font-size: 1.3rem;
    }}
}}

/* ---------- Tabela Customizada ---------- */
.custom-table-container {{
    max-height: 420px;
    overflow-y: auto;
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    margin-top: 12px;
    background-color: var(--card-bg);
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}

/* Scrollbar */
.custom-table-container::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
.custom-table-container::-webkit-scrollbar-track {{
    background: transparent;
}}
.custom-table-container::-webkit-scrollbar-thumb {{
    background: var(--card-border);
    border-radius: 10px;
}}
.custom-table-container::-webkit-scrollbar-thumb:hover {{
    background: var(--accent);
}}

.custom-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-body);
    font-size: 0.88rem;
}}

/* Cabecalho: fundo levemente teal, texto teal escuro */
.custom-table thead tr {{
    background-color: var(--bg-secondary) !important;
    position: sticky;
    top: 0;
    z-index: 5;
}}

.custom-table th {{
    padding: 11px 16px;
    font-family: var(--font-heading);
    font-weight: 700;
    color: var(--accent);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    border-bottom: 2px solid var(--card-border);
    background: var(--bg-secondary);
}}

.custom-table td {{
    padding: 10px 16px;
    border-bottom: 1px solid rgba(79,208,195,0.12);
    color: var(--text-primary);
    vertical-align: middle;
}}

.custom-table tbody tr {{
    background-color: transparent;
    transition: background-color 0.12s ease;
}}

.custom-table tbody tr:nth-child(even) {{
    background-color: rgba(79,208,195,0.03);
}}

.custom-table tbody tr:hover {{
    background-color: rgba(79,208,195,0.07) !important;
}}

.custom-table tbody tr:last-child td {{
    border-bottom: none;
}}

/* ---------- Badges de absenteismo ---------- */
.badge-abs {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.8rem;
    min-width: 65px;
}}

.badge-abs.high {{
    background-color: rgba(217,48,37,0.10);
    color: var(--negative);
    border: 1px solid rgba(217,48,37,0.22);
}}

.badge-abs.low {{
    background-color: rgba(24,201,158,0.10);
    color: var(--positive);
    border: 1px solid rgba(24,201,158,0.22);
}}

.badge-abs.medium {{
    background-color: rgba(94,139,131,0.10);
    color: var(--neutral);
    border: 1px solid rgba(94,139,131,0.20);
}}

/* ---------- Formulario de Cadastro ---------- */
.form-section-hdr {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.5rem 0 0.55rem 0;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 0.85rem;
    margin-top: 0.1rem;
}}

.form-section-hdr .fsh-num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    background: var(--accent-soft);
    border: 1px solid rgba(24,201,158,0.28);
    font-family: var(--font-heading);
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--accent);
    flex-shrink: 0;
    letter-spacing: 0;
}}

.form-section-hdr .fsh-icon {{
    font-size: 0.95rem;
}}

.form-section-hdr .fsh-title {{
    font-family: var(--font-heading) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
    letter-spacing: 0.2px;
}}

.form-section-hdr .fsh-hint {{
    margin-left: auto;
    font-size: 0.73rem;
    color: var(--text-muted);
    font-style: italic;
    padding-right: 2px;
}}

/* ---------- Info box de importacao ---------- */
.import-info-box {{
    background: linear-gradient(145deg, var(--accent-soft) 0%, var(--bg-secondary) 100%);
    border: 1px solid rgba(24,201,158,0.18);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius-sm);
    padding: 0.9rem 1.15rem 1rem;
    margin-bottom: 1.1rem;
}}

.import-info-box .iib-title {{
    font-family: var(--font-heading);
    font-size: 0.86rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 6px;
}}

.import-info-box .iib-desc {{
    font-size: 0.81rem;
    color: var(--text-muted);
    margin-bottom: 0.55rem;
    line-height: 1.55;
}}

/* ---------- Formulario Manual: centralizado + cards modernos ---------- */
.st-key-cadastro_manual_form {{
    max-width: 800px;
    margin: 0 auto;
}}

.st-key-cadastro_manual_form div[data-testid="stVerticalBlock"][data-test-scroll-behavior="normal"] {{
    border-radius: var(--radius-md) !important;
    border-color: var(--card-border) !important;
    background: var(--card-bg);
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    padding: 1rem 1.1rem 0.3rem !important;
    margin-bottom: 1.1rem;
}}

/* Bordas modernas + foco com glow teal nos campos de texto, data e select */
.st-key-cadastro_manual_form input,
.st-key-cadastro_manual_form div[data-baseweb="select"] > div,
.st-key-cadastro_manual_form div[data-baseweb="base-input"] {{
    border-radius: var(--radius-sm) !important;
    border: 1.5px solid var(--card-border) !important;
    background-color: var(--bg-secondary) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}

.st-key-cadastro_manual_form input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}}

.st-key-cadastro_manual_form div[data-baseweb="select"]:focus-within > div {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}}

/* Campos numericos compactos — nao precisam ocupar a largura total da coluna */
.st-key-cadastro_manual_form div[data-testid="stNumberInput"] {{
    max-width: 140px;
}}

/* ---------- Chips de coluna ---------- */
.col-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 0.55rem;
}}

.col-chip {{
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 6px;
    background: var(--accent-soft);
    border: 1px solid rgba(24,201,158,0.22);
    font-size: 0.76rem;
    font-family: 'Courier New', monospace;
    color: var(--accent);
    font-weight: 600;
    white-space: nowrap;
}}

/* ---------- Misc ---------- */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}

::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: var(--bg-secondary); }}
::-webkit-scrollbar-thumb {{ background: var(--card-border); border-radius: 6px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}
</style>"""
