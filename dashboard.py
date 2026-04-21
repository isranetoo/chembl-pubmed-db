"""
dashboard.py
------------
Dashboard Streamlit para explorar o banco ChEMBL + PubMed.

Instalação:
    pip install streamlit plotly pandas psycopg2-binary

Execução:
    streamlit run dashboard.py

Seções:
  1. Visão geral        — métricas do banco
  2. Busca de compostos — busca por nome, filtros ADMET
  3. Perfil do composto — ADMET + indicações + mecanismos
  4. Artigos científicos— lista com abstract e snippet
  5. Análise ADMET      — tabela comparativa e gráficos
  6. Indicações         — gráfico por fase clínica
"""

import json
import textwrap
from contextlib import contextmanager

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
import streamlit as st

# ============================================================
# Configuração da página
# ============================================================

st.set_page_config(
    page_title="DrugXpert",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Conexão com o banco
# ============================================================

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "chembl_pubmed",
    "user":     "admin",
    "password": "admin123",
}


@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def cursor():
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def query(sql: str, params=None) -> pd.DataFrame:
    with cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ============================================================
# CSS customizado
# ============================================================

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 16px 20px;
        border-left: 4px solid #1D9E75;
        margin-bottom: 8px;
    }
    .metric-label { font-size: 12px; color: #666; font-weight: 500; }
    .metric-value { font-size: 28px; font-weight: 700; color: #1a1a1a; }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin: 2px;
    }
    .badge-approved  { background: #d4edda; color: #155724; }
    .badge-phase3    { background: #cce5ff; color: #004085; }
    .badge-phase2    { background: #fff3cd; color: #856404; }
    .badge-inhibitor { background: #f8d7da; color: #721c24; }
    .badge-agonist   { background: #d1ecf1; color: #0c5460; }
    .article-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        background: white;
    }
    .article-title { font-size: 14px; font-weight: 600; color: #1a1a1a; }
    .article-meta  { font-size: 12px; color: #888; margin: 4px 0 8px; }
    .article-abstract { font-size: 13px; color: #444; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Sidebar — navegação
# ============================================================

with st.sidebar:
    st.markdown("## 🧬 DrugXpert")
    st.markdown("Explorador do banco ChEMBL + PubMed")
    st.divider()

    page = st.radio(
        "Navegar para",
        ["Visão geral", "Busca de compostos", "Perfil do composto",
         "Artigos científicos", "Análise ADMET", "Indicações"],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Banco: `{DB_CONFIG['dbname']}` em `{DB_CONFIG['host']}:{DB_CONFIG['port']}`")


# ============================================================
# Helpers
# ============================================================

PHASE_LABELS = {4: "Aprovado", 3: "Fase 3", 2: "Fase 2", 1: "Fase 1", 0.5: "Early Phase 1"}
PHASE_COLORS = {4: "#28a745", 3: "#007bff", 2: "#ffc107", 1: "#fd7e14", 0.5: "#6c757d"}

def phase_badge(phase):
    if phase is None:
        return ""
    label = PHASE_LABELS.get(float(phase), f"Fase {phase}")
    cls   = "badge-approved" if float(phase) >= 4 else (
            "badge-phase3"   if float(phase) == 3 else "badge-phase2")
    return f'<span class="badge {cls}">{label}</span>'


def action_badge(action):
    if not action:
        return ""
    cls = "badge-inhibitor" if "INHIBITOR" in action else "badge-agonist"
    return f'<span class="badge {cls}">{action}</span>'


@st.cache_data(ttl=60)
def load_compound_list():
    return query("""
        SELECT c.id::text, c.chembl_id, c.name, c.molecular_formula,
               c.mol_weight, a.qed_weighted
        FROM compounds c
        LEFT JOIN admet_properties a ON a.compound_id = c.id
        ORDER BY c.name
    """)


# ============================================================
# Página 1: Visão geral
# ============================================================

def page_overview():
    st.title("Visão geral do banco")

    try:
        df_counts = query("""
            SELECT
                (SELECT COUNT(*) FROM compounds)              AS compostos,
                (SELECT COUNT(*) FROM articles)               AS artigos,
                (SELECT COUNT(*) FROM indications)            AS indicacoes,
                (SELECT COUNT(*) FROM mechanisms)             AS mecanismos,
                (SELECT COUNT(*) FROM bioactivities)          AS bioatividades,
                (SELECT COUNT(*) FROM targets)                AS alvos,
                (SELECT COUNT(*) FILTER (WHERE abstract IS NOT NULL)
                 FROM articles)                               AS artigos_com_abstract,
                (SELECT COUNT(*) FILTER (WHERE max_phase >= 4)
                 FROM indications)                            AS indicacoes_aprovadas
        """)
    except Exception as e:
        st.error(f"Erro ao conectar ao banco: {e}")
        st.info("Verifique se o Docker está rodando: `docker compose up -d`")
        return

    row = df_counts.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Compostos",     int(row["compostos"]))
        st.metric("Alvos biológicos", int(row["alvos"]))
    with col2:
        st.metric("Artigos",       int(row["artigos"]))
        st.metric("Com abstract",  int(row["artigos_com_abstract"]))
    with col3:
        st.metric("Indicações",    int(row["indicacoes"]))
        st.metric("Aprovadas",     int(row["indicacoes_aprovadas"]))
    with col4:
        st.metric("Mecanismos",    int(row["mecanismos"]))
        st.metric("Bioatividades", int(row["bioatividades"]))

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Ranking por druglikeness (QED)")
        df_qed = query("""
            SELECT c.name, ROUND(a.qed_weighted::numeric, 3) AS qed,
                   a.num_ro5_violations AS ro5_violations
            FROM admet_properties a
            JOIN compounds c ON c.id = a.compound_id
            WHERE a.qed_weighted IS NOT NULL
            ORDER BY a.qed_weighted DESC
        """)
        if not df_qed.empty:
            fig = px.bar(
                df_qed, x="qed", y="name", orientation="h",
                color="qed", color_continuous_scale="Teal",
                labels={"qed": "QED Score", "name": ""},
                height=420,
            )
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=0, r=10, t=10, b=10),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, width='stretch')

    with col_r:
        st.subheader("Artigos por ano")
        df_year = query("""
            SELECT pub_year, COUNT(*) AS total
            FROM articles
            WHERE pub_year IS NOT NULL
            GROUP BY pub_year
            ORDER BY pub_year
        """)
        if not df_year.empty:
            fig = px.area(
                df_year, x="pub_year", y="total",
                labels={"pub_year": "Ano", "total": "Artigos"},
                color_discrete_sequence=["#1D9E75"],
                height=420,
            )
            fig.update_layout(margin=dict(l=0, r=10, t=10, b=10))
            st.plotly_chart(fig, width='stretch')


# ============================================================
# Página 2: Busca de compostos
# ============================================================

def page_search():
    st.title("Busca de compostos")

    col_search, col_filter = st.columns([3, 1])

    with col_search:
        search = st.text_input("Buscar por nome", placeholder="ex: aspirin, ibuprofen, metformin...")

    with col_filter:
        lipinski_only = st.checkbox("Só Lipinski OK", value=False)

    col_qed, col_phase = st.columns(2)
    with col_qed:
        min_qed = st.slider("QED mínimo", 0.0, 1.0, 0.0, 0.05)
    with col_phase:
        min_phase = st.selectbox(
            "Fase clínica mínima",
            [None, 1, 2, 3, 4],
            format_func=lambda x: "Todas" if x is None else PHASE_LABELS.get(x, str(x)),
        )

    sql = """
        SELECT c.chembl_id, c.name, c.molecular_formula,
               ROUND(c.mol_weight::numeric, 2)  AS mol_weight,
               ROUND(a.qed_weighted::numeric, 3) AS qed,
               a.num_ro5_violations              AS ro5,
               ROUND(a.alogp::numeric, 2)        AS alogp,
               ROUND(a.psa::numeric, 1)          AS psa,
               COALESCE(i.max_phase, 0)::numeric AS max_phase,
               i.n_ind,
               ar.n_art
        FROM compounds c
        LEFT JOIN admet_properties a ON a.compound_id = c.id
        LEFT JOIN (
            SELECT compound_id,
                   MAX(max_phase) AS max_phase,
                   COUNT(*)       AS n_ind
            FROM indications GROUP BY compound_id
        ) i ON i.compound_id = c.id
        LEFT JOIN (
            SELECT compound_id, COUNT(*) AS n_art
            FROM article_compounds GROUP BY compound_id
        ) ar ON ar.compound_id = c.id
        WHERE 1=1
    """
    params = []

    if search:
        sql += " AND LOWER(c.name) LIKE LOWER(%s)"
        params.append(f"%{search}%")
    if min_qed > 0:
        sql += " AND a.qed_weighted >= %s"
        params.append(min_qed)
    if lipinski_only:
        sql += " AND (a.num_ro5_violations = 0 OR a.num_ro5_violations IS NULL)"
    if min_phase:
        sql += " AND i.max_phase >= %s"
        params.append(min_phase)

    sql += " ORDER BY a.qed_weighted DESC NULLS LAST LIMIT 50"

    try:
        df = query(sql, params if params else None)
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return

    if df.empty:
        st.info("Nenhum composto encontrado.")
        return

    st.caption(f"{len(df)} compostos encontrados")

    # Tabela interativa
    df_display = df.copy()
    df_display["fase"]     = df_display["max_phase"].apply(
        lambda x: PHASE_LABELS.get(float(x), f"{x}") if x else "—"
    )
    df_display["artigos"]  = df_display["n_art"].fillna(0).astype(int)
    df_display["indicações"] = df_display["n_ind"].fillna(0).astype(int)

    st.dataframe(
        df_display[["chembl_id", "name", "molecular_formula", "mol_weight",
                    "qed", "alogp", "psa", "ro5", "fase", "indicações", "artigos"]],
        width='stretch',
        hide_index=True,
        column_config={
            "chembl_id":        st.column_config.TextColumn("ChEMBL ID"),
            "name":             st.column_config.TextColumn("Nome"),
            "molecular_formula":st.column_config.TextColumn("Fórmula"),
            "mol_weight":       st.column_config.NumberColumn("MW", format="%.2f"),
            "qed":              st.column_config.ProgressColumn("QED", min_value=0, max_value=1, format="%.3f"),
            "alogp":            st.column_config.NumberColumn("ALogP", format="%.2f"),
            "psa":              st.column_config.NumberColumn("PSA (Å²)", format="%.1f"),
            "ro5":              st.column_config.NumberColumn("Ro5 viol.", format="%d"),
            "fase":             st.column_config.TextColumn("Fase"),
            "indicações":       st.column_config.NumberColumn("Indicações"),
            "artigos":          st.column_config.NumberColumn("Artigos"),
        },
        height=480,
    )


# ============================================================
# Página 3: Perfil do composto
# ============================================================

def page_compound_profile():
    st.title("Perfil do composto")

    compounds = load_compound_list()
    if compounds.empty:
        st.warning("Nenhum composto no banco.")
        return

    options = {f"{row['name']} ({row['chembl_id']})": row["id"]
               for _, row in compounds.iterrows()}
    selected_label = st.selectbox("Selecione o composto", list(options.keys()))
    compound_id    = options[selected_label]

    # ── Dados básicos ─────────────────────────────────────────
    df_base = query("""
        SELECT c.chembl_id, c.name, c.molecular_formula, c.mol_weight, c.smiles,
               a.qed_weighted, a.alogp, a.psa, a.hbd, a.hba, a.rtb,
               a.num_ro5_violations, a.molecular_species, a.num_alerts,
               a.aromatic_rings, a.heavy_atoms
        FROM compounds c
        LEFT JOIN admet_properties a ON a.compound_id = c.id
        WHERE c.id = %s
    """, (compound_id,))

    if df_base.empty:
        return

    row = df_base.iloc[0]

    col_info, col_admet = st.columns([1, 1])

    with col_info:
        st.markdown(f"### {row['name']}")
        st.code(row["smiles"] or "SMILES não disponível", language=None)
        m1, m2, m3 = st.columns(3)
        m1.metric("Fórmula",   row["molecular_formula"] or "—")
        m2.metric("MW",        f"{float(row['mol_weight']):.2f}" if row["mol_weight"] else "—")
        m3.metric("ChEMBL ID", row["chembl_id"])

        m4, m5, m6 = st.columns(3)
        m4.metric("QED",       f"{float(row['qed_weighted']):.3f}" if row["qed_weighted"] else "—")
        m5.metric("ALogP",     f"{float(row['alogp']):.2f}"        if row["alogp"]        else "—")
        m6.metric("Ro5 viol.", str(row["num_ro5_violations"])       if row["num_ro5_violations"] is not None else "—")

    with col_admet:
        st.markdown("#### Radar ADMET")
        # Radar com propriedades normalizadas
        if all(row[k] is not None for k in ["qed_weighted","alogp","psa","hbd","hba","rtb"]):
            categories = ["QED", "Lipofilia\n(1-ALogP/5)", "PSA\n(1-PSA/140)",
                          "HBD\n(1-HBD/5)", "HBA\n(1-HBA/10)", "RTB\n(1-RTB/10)"]
            values = [
                float(row["qed_weighted"]),
                max(0, 1 - float(row["alogp"]) / 5),
                max(0, 1 - float(row["psa"])   / 140),
                max(0, 1 - int(row["hbd"])     / 5),
                max(0, 1 - int(row["hba"])     / 10),
                max(0, 1 - int(row["rtb"])     / 10),
            ]
            fig = go.Figure(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(29,158,117,0.2)",
                line_color="#1D9E75",
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=False,
                height=320,
                margin=dict(l=30, r=30, t=30, b=30),
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Dados ADMET insuficientes para o radar.")

    st.divider()

    tab_ind, tab_mec, tab_bio = st.tabs(["Indicações terapêuticas", "Mecanismos de ação", "Bioatividades"])

    # ── Indicações ────────────────────────────────────────────
    with tab_ind:
        df_ind = query("""
            SELECT mesh_heading, efo_term, max_phase
            FROM indications
            WHERE compound_id = %s
            ORDER BY max_phase DESC NULLS LAST, mesh_heading
        """, (compound_id,))

        if df_ind.empty:
            st.info("Nenhuma indicação registrada.")
        else:
            # Gráfico de fases
            phase_counts = df_ind["max_phase"].dropna().apply(
                lambda x: PHASE_LABELS.get(float(x), str(x))
            ).value_counts().reset_index()
            phase_counts.columns = ["fase", "count"]

            fig = px.bar(
                phase_counts, x="count", y="fase", orientation="h",
                color="fase",
                color_discrete_map={v: PHASE_COLORS.get(k, "#888")
                                    for k, v in PHASE_LABELS.items()},
                labels={"count": "Nº de indicações", "fase": ""},
                height=260,
            )
            fig.update_layout(showlegend=False, margin=dict(l=0, r=10, t=10, b=10))
            st.plotly_chart(fig, width='stretch')

            # Tabela completa
            df_display = df_ind.copy()
            df_display["fase"] = df_display["max_phase"].apply(
                lambda x: PHASE_LABELS.get(float(x), str(x)) if x is not None else "—"
            )
            df_display["indicação"] = df_display["mesh_heading"].fillna(df_display["efo_term"])
            st.dataframe(
                df_display[["indicação", "efo_term", "fase"]],
                hide_index=True,
                width='stretch',
                height=320,
            )

    # ── Mecanismos ────────────────────────────────────────────
    with tab_mec:
        df_mec = query("""
            SELECT mechanism_of_action, action_type, target_name,
                   direct_interaction, disease_efficacy, mechanism_comment
            FROM mechanisms
            WHERE compound_id = %s
            ORDER BY action_type, target_name
        """, (compound_id,))

        if df_mec.empty:
            st.info("Nenhum mecanismo registrado.")
        else:
            for _, m in df_mec.iterrows():
                with st.expander(
                    f"{m['mechanism_of_action'] or m['action_type'] or 'Mecanismo'} "
                    f"— {m['target_name'] or '?'}"
                ):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Tipo:** {m['action_type'] or '—'}")
                    c2.markdown(f"**Interação direta:** {'✓' if m['direct_interaction'] else '✗'}")
                    c3.markdown(f"**Eficácia clínica:** {'✓' if m['disease_efficacy'] else '✗'}")
                    if m["mechanism_comment"]:
                        st.caption(m["mechanism_comment"])

    # ── Bioatividades ─────────────────────────────────────────
    with tab_bio:
        df_bio = query("""
            SELECT t.name AS target, b.activity_type, b.value, b.units, b.relation
            FROM bioactivities b
            JOIN targets t ON t.id = b.target_id
            WHERE b.compound_id = %s
            ORDER BY b.activity_type, b.value
        """, (compound_id,))

        if df_bio.empty:
            st.info("Nenhuma bioatividade registrada.")
        else:
            st.dataframe(
                df_bio,
                hide_index=True,
                width='stretch',
                column_config={
                    "target":        st.column_config.TextColumn("Alvo biológico"),
                    "activity_type": st.column_config.TextColumn("Tipo"),
                    "value":         st.column_config.NumberColumn("Valor", format="%.2f"),
                    "units":         st.column_config.TextColumn("Unidade"),
                    "relation":      st.column_config.TextColumn("Relação"),
                },
            )


# ============================================================
# Página 4: Artigos científicos
# ============================================================

def page_articles():
    st.title("Artigos científicos")

    compounds = load_compound_list()
    if compounds.empty:
        st.warning("Nenhum composto no banco.")
        return

    col_sel, col_filter = st.columns([2, 1])
    with col_sel:
        options = {"Todos os compostos": None} | {
            f"{row['name']} ({row['chembl_id']})": row["id"]
            for _, row in compounds.iterrows()
        }
        selected = st.selectbox("Filtrar por composto", list(options.keys()))
        compound_id = options[selected]

    with col_filter:
        search_text = st.text_input("Buscar no título / abstract", placeholder="ex: inflammation")

    col_year, col_abstract = st.columns(2)
    with col_year:
        year_range = st.slider("Ano de publicação", 1990, 2025, (2000, 2025))
    with col_abstract:
        only_abstract = st.checkbox("Só artigos com abstract", value=True)

    # Query
    sql = """
        SELECT a.pmid, a.title, a.journal, a.pub_year, a.doi,
               a.abstract,
               a.pub_types,
               STRING_AGG(DISTINCT c.name, ', ') AS compostos
        FROM articles a
        JOIN article_compounds ac ON ac.article_id = a.id
        JOIN compounds c          ON c.id = ac.compound_id
        WHERE a.pub_year BETWEEN %s AND %s
    """
    params = [year_range[0], year_range[1]]

    if compound_id:
        sql += " AND ac.compound_id = %s"
        params.append(compound_id)

    if only_abstract:
        sql += " AND a.abstract IS NOT NULL"

    if search_text:
        sql += " AND (a.title ILIKE %s OR a.abstract ILIKE %s)"
        params += [f"%{search_text}%", f"%{search_text}%"]

    sql += " GROUP BY a.pmid, a.title, a.journal, a.pub_year, a.doi, a.abstract, a.pub_types"
    sql += " ORDER BY a.pub_year DESC NULLS LAST LIMIT 50"

    try:
        df = query(sql, params)
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    if df.empty:
        st.info("Nenhum artigo encontrado.")
        return

    st.caption(f"{len(df)} artigos encontrados")

    for _, art in df.iterrows():
        pub_types = []
        if art["pub_types"]:
            try:
                pub_types = json.loads(art["pub_types"]) if isinstance(art["pub_types"], str) else art["pub_types"]
            except Exception:
                pass

        with st.expander(f"📄 {art['title'] or 'Sem título'}", expanded=False):
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.markdown(f"**PMID:** {art['pmid']}")
            col_m2.markdown(f"**Ano:** {int(art['pub_year']) if art['pub_year'] else '—'}")
            col_m3.markdown(f"**Journal:** {art['journal'] or '—'}")
            col_m4.markdown(f"**Composto(s):** {art['compostos']}")

            if pub_types:
                st.caption("  ".join(f"`{t}`" for t in pub_types[:3]))

            if art["abstract"]:
                abstract = art["abstract"]
                # Destaque do termo de busca
                if search_text:
                    abstract = abstract.replace(
                        search_text,
                        f"**{search_text}**"
                    )
                snippet = textwrap.shorten(abstract, width=500, placeholder="…")
                st.markdown(snippet)

                with st.expander("Abstract completo"):
                    st.markdown(art["abstract"])
            else:
                st.caption("Abstract não disponível. Rode `python backfill_abstracts.py`.")

            if art["doi"]:
                st.link_button(
                    "Ver no PubMed",
                    f"https://pubmed.ncbi.nlm.nih.gov/{art['pmid']}/",
                    width='content',
                )


# ============================================================
# Página 5: Análise ADMET
# ============================================================

def page_admet():
    st.title("Análise ADMET comparativa")

    compounds = load_compound_list()
    if compounds.empty:
        st.warning("Nenhum composto no banco.")
        return

    all_names = compounds["name"].tolist()
    selected_names = st.multiselect(
        "Selecionar compostos para comparar",
        all_names,
        default=all_names[:6] if len(all_names) >= 6 else all_names,
    )

    if not selected_names:
        st.info("Selecione ao menos um composto.")
        return

    placeholders = ",".join(["%s"] * len(selected_names))
    df = query(f"""
        SELECT c.name,
               ROUND(a.qed_weighted::numeric,  3) AS qed,
               ROUND(a.alogp::numeric,          2) AS alogp,
               ROUND(a.psa::numeric,            1) AS psa,
               a.hbd, a.hba, a.rtb,
               a.num_ro5_violations              AS ro5_violations,
               a.num_alerts,
               ROUND(a.mw_freebase::numeric,    2) AS mw,
               a.aromatic_rings,
               a.molecular_species,
               CASE WHEN a.num_ro5_violations = 0 THEN 'Sim' ELSE 'Não' END AS lipinski,
               CASE WHEN COALESCE(a.rtb, 99) <= 10
                     AND COALESCE(a.psa, 999) <= 140 THEN 'Sim' ELSE 'Não' END AS veber
        FROM admet_properties a
        JOIN compounds c ON c.id = a.compound_id
        WHERE c.name IN ({placeholders})
        ORDER BY a.qed_weighted DESC NULLS LAST
    """, selected_names)

    if df.empty:
        st.info("Nenhum dado ADMET encontrado.")
        return

    # Tabela comparativa com cores
    st.subheader("Tabela comparativa")
    st.dataframe(
        df,
        hide_index=True,
        width='stretch',
        column_config={
            "name":         st.column_config.TextColumn("Composto"),
            "qed":          st.column_config.ProgressColumn("QED", min_value=0, max_value=1, format="%.3f"),
            "alogp":        st.column_config.NumberColumn("ALogP", format="%.2f"),
            "psa":          st.column_config.NumberColumn("PSA (Å²)", format="%.1f"),
            "hbd":          st.column_config.NumberColumn("HBD"),
            "hba":          st.column_config.NumberColumn("HBA"),
            "rtb":          st.column_config.NumberColumn("RTB"),
            "ro5_violations":st.column_config.NumberColumn("Ro5 viol."),
            "num_alerts":   st.column_config.NumberColumn("Alertas PAINS"),
            "mw":           st.column_config.NumberColumn("MW", format="%.2f"),
            "aromatic_rings":st.column_config.NumberColumn("Anéis aromáticos"),
            "molecular_species":st.column_config.TextColumn("Espécie"),
            "lipinski":     st.column_config.TextColumn("Lipinski"),
            "veber":        st.column_config.TextColumn("Veber"),
        },
        height=360,
    )

    st.divider()

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("ALogP × PSA")
        fig = px.scatter(
            df, x="alogp", y="psa", text="name", size="mw",
            color="qed", color_continuous_scale="Teal",
            labels={"alogp": "ALogP (lipofilia)", "psa": "PSA (Å²)"},
            height=360,
        )
        fig.update_traces(textposition="top center", textfont_size=10)
        # Linhas de corte Lipinski / Veber
        fig.add_hline(y=140, line_dash="dot", line_color="red",
                      annotation_text="PSA = 140 Å²")
        fig.add_vline(x=5,   line_dash="dot", line_color="orange",
                      annotation_text="ALogP = 5")
        fig.update_layout(margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    with col_r:
        st.subheader("QED por composto")
        fig = px.bar(
            df.sort_values("qed", ascending=True),
            x="qed", y="name", orientation="h",
            color="qed", color_continuous_scale="Teal",
            labels={"qed": "QED Score", "name": ""},
            height=360,
        )
        fig.add_vline(x=0.5, line_dash="dot", line_color="gray",
                      annotation_text="QED = 0.5")
        fig.update_layout(
            coloraxis_showscale=False,
            margin=dict(l=0, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, width='stretch')


# ============================================================
# Página 6: Indicações
# ============================================================

def page_indications():
    st.title("Indicações terapêuticas")

    col_l, col_r = st.columns([1, 1])

    with col_l:
        # Distribuição por fase — gráfico de pizza
        df_phase = query("""
            SELECT
                CASE max_phase
                    WHEN 4   THEN 'Aprovado'
                    WHEN 3   THEN 'Fase 3'
                    WHEN 2   THEN 'Fase 2'
                    WHEN 1   THEN 'Fase 1'
                    WHEN 0.5 THEN 'Early Phase 1'
                    ELSE          'Pré-clínico'
                END AS fase,
                COUNT(*) AS total
            FROM indications
            GROUP BY max_phase
            ORDER BY max_phase DESC NULLS LAST
        """)
        if not df_phase.empty:
            st.subheader("Distribuição por fase clínica")
            color_map = {v: PHASE_COLORS.get(k, "#888") for k, v in PHASE_LABELS.items()}
            color_map["Pré-clínico"] = "#888"
            fig = px.pie(
                df_phase, values="total", names="fase",
                color="fase", color_discrete_map=color_map,
                height=360,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')

    with col_r:
        # Indicações aprovadas mais frequentes
        df_top = query("""
            SELECT COALESCE(mesh_heading, efo_term) AS indicacao,
                   COUNT(DISTINCT compound_id)       AS compostos
            FROM indications
            WHERE max_phase >= 4
              AND (mesh_heading IS NOT NULL OR efo_term IS NOT NULL)
            GROUP BY mesh_heading, efo_term
            ORDER BY compostos DESC
            LIMIT 15
        """)
        if not df_top.empty:
            st.subheader("Top 15 indicações aprovadas")
            fig = px.bar(
                df_top.sort_values("compostos"),
                x="compostos", y="indicacao", orientation="h",
                labels={"compostos": "Nº de compostos", "indicacao": ""},
                color="compostos", color_continuous_scale="Teal",
                height=400,
            )
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=0, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, width='stretch')

    st.divider()
    st.subheader("Indicações por composto")

    df_matrix = query("""
        SELECT c.name AS composto,
               COALESCE(i.mesh_heading, i.efo_term) AS indicacao,
               i.max_phase
        FROM indications i
        JOIN compounds c ON c.id = i.compound_id
        WHERE i.max_phase >= 2
          AND (i.mesh_heading IS NOT NULL OR i.efo_term IS NOT NULL)
        ORDER BY i.max_phase DESC, c.name
    """)

    if not df_matrix.empty:
        # Pivô: compostos × indicações com fase como valor
        pivot = df_matrix.pivot_table(
            index="composto", columns="indicacao",
            values="max_phase", aggfunc="max"
        ).fillna(0)

        # Só colunas com pelo menos 2 compostos
        pivot = pivot.loc[:, (pivot > 0).sum() >= 2]

        if not pivot.empty:
            fig = px.imshow(
                pivot,
                color_continuous_scale=[
                    [0,    "#f0f0f0"],
                    [0.25, "#FFE0B2"],
                    [0.5,  "#FFA726"],
                    [0.75, "#42A5F5"],
                    [1.0,  "#28a745"],
                ],
                zmin=0, zmax=4,
                labels={"color": "Fase"},
                height=max(350, len(pivot) * 30),
                aspect="auto",
            )
            fig.update_layout(
                xaxis=dict(side="bottom", tickangle=-45),
                margin=dict(l=0, r=0, t=10, b=100),
                coloraxis_colorbar=dict(
                    tickvals=[0, 1, 2, 3, 4],
                    ticktext=["—", "Fase 1", "Fase 2", "Fase 3", "Aprovado"],
                ),
            )
            st.plotly_chart(fig, width='stretch')
            st.caption("Heatmap: cada célula mostra a fase clínica máxima atingida para aquela indicação. Só indicações com ≥ 2 compostos são exibidas.")


# ============================================================
# Roteador
# ============================================================

try:
    if page == "Visão geral":
        page_overview()
    elif page == "Busca de compostos":
        page_search()
    elif page == "Perfil do composto":
        page_compound_profile()
    elif page == "Artigos científicos":
        page_articles()
    elif page == "Análise ADMET":
        page_admet()
    elif page == "Indicações":
        page_indications()
except psycopg2.OperationalError:
    st.error("Não foi possível conectar ao banco de dados.")
    st.markdown("""
    **Verifique se o Docker está rodando:**
    ```bash
    docker compose up -d
    docker compose ps
    ```
    """)
