import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend
import matplotlib.pyplot as plt
import io
import base64
import json
import urllib.request
from html import escape

st.set_page_config(
    page_title="Corrida Financiera - Farmacia Líbano",
    page_icon="💊",
    layout="wide"
)

# ═══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE CÓDIGOS DE ACCESO
# Local: lee de codigos.txt | Producción: lee de Streamlit Secrets
# ═══════════════════════════════════════════════════════════════════════════════
import os
from datetime import datetime

def cargar_codigos():
    """Carga los códigos desde archivo local o Streamlit Secrets"""
    codigos = {}
    
    # Intentar cargar desde archivo local primero
    archivo = os.path.join(os.path.dirname(__file__), 'codigos.txt')
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#') and '=' in linea:
                    codigo, nombre = linea.split('=', 1)
                    codigos[codigo.strip()] = nombre.strip()
    
    # Si no hay códigos locales, intentar Streamlit Secrets (producción)
    if not codigos:
        try:
            if 'codigos' in st.secrets:
                codigos = dict(st.secrets['codigos'])
        except:
            pass
    
    # Código dinámico del día (cambia cada día) - siempre disponible
    codigo_diario = f"DIA{datetime.now().strftime('%d%m%y')}"
    codigos[codigo_diario] = "Acceso Temporal"
    
    return codigos

def registrar_acceso(codigo, nombre):
    """Registra el acceso en session, archivo local, /tmp y webhook opcional."""
    registrar_evento("ACCESO", {
        "codigo": codigo,
        "usuario": nombre,
    })

def registrar_corrida(datos_franquicia, usuario):
    """Registra cuando se crea una corrida financiera"""
    registrar_evento("CORRIDA", {
        "usuario": usuario,
        "cliente": datos_franquicia.get("nombre", ""),
        "ubicacion": datos_franquicia.get("ubicacion", ""),
        "proposito": datos_franquicia.get("proposito", ""),
    })

def _obtener_webhook_auditoria():
    """Obtiene URL de webhook para auditoría desde secrets si existe."""
    try:
        if "audit_webhook_url" in st.secrets:
            return st.secrets["audit_webhook_url"]
        if "logging" in st.secrets and "webhook_url" in st.secrets["logging"]:
            return st.secrets["logging"]["webhook_url"]
    except Exception:
        return None
    return None

def registrar_evento(tipo, payload):
    """Registra eventos de auditoría de forma compatible con Streamlit Cloud."""
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    evento = {"fecha_hora": fecha_hora, "tipo": tipo, **payload}
    registro_txt = " | ".join([fecha_hora, tipo] + [str(v) for v in payload.values()])

    # 1) Session state (visible en runtime actual)
    if "registro_accesos" not in st.session_state:
        st.session_state["registro_accesos"] = []
    st.session_state["registro_accesos"].append(registro_txt)

    # 2) Archivo del repo (local/dev)
    try:
        archivo_log = os.path.join(os.path.dirname(__file__), "accesos.log")
        with open(archivo_log, "a", encoding="utf-8") as f:
            f.write(registro_txt + "\n")
    except Exception:
        pass

    # 3) /tmp (funciona bien en Streamlit Cloud mientras el contenedor vive)
    try:
        archivo_tmp = "/tmp/corrida_accesos.jsonl"
        with open(archivo_tmp, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # 4) Webhook opcional para persistencia externa (recomendado en nube)
    webhook_url = _obtener_webhook_auditoria()
    if webhook_url:
        try:
            body = json.dumps(evento, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

CODIGOS_ACCESO = cargar_codigos()
CODIGO_ACCESO_DIRECTO = "0301"

# Verificar si el usuario ya está autenticado
if 'acceso_autorizado' not in st.session_state:
    st.session_state['acceso_autorizado'] = False

# Si no está autenticado, mostrar pantalla de login
if not st.session_state['acceso_autorizado']:
    st.markdown("""
    <div style="text-align: center; padding: 30px 0;">
        <div style="font-size: 40px; font-weight: bold;">
            <span style="color: #00A651;">+FARMACIA</span> 
            <span style="color: #003D7A;">LÍBANO</span>
        </div>
        <div style="font-style: italic; font-size: 16px; color: #003D7A; margin-top: 10px;">
            Siempre al cuidado de tu salud
        </div>
        <div style="font-size: 24px; color: #003D7A; margin-top: 30px; font-weight: bold;">
            Corrida Financiera - Portal de Franquicias
        </div>
        <div style="font-size: 14px; color: #666; margin-top: 10px;">
            Ingresa tu código de acceso para continuar
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            codigo = st.text_input("🔑 Código de Acceso:", type="password", placeholder="Ingresa tu código...")
            submit = st.form_submit_button("🚀 Acceder", use_container_width=True)
            
            if submit:
                if codigo == CODIGO_ACCESO_DIRECTO:
                    st.session_state['acceso_autorizado'] = True
                    st.session_state['usuario_nombre'] = "Acceso Directo"
                    st.session_state['datos_franquicia'] = {
                        'nombre': "Consulta Interna",
                        'ubicacion': "Sin captura",
                        'proposito': "Acceso directo",
                        'notas': ""
                    }
                    registrar_acceso(codigo, "Acceso Directo")
                    st.rerun()
                elif codigo in CODIGOS_ACCESO:
                    st.session_state['acceso_autorizado'] = True
                    st.session_state['usuario_nombre'] = CODIGOS_ACCESO[codigo]
                    registrar_acceso(codigo, CODIGOS_ACCESO[codigo])
                    st.rerun()
                else:
                    st.error("❌ Código de acceso inválido")
    
    st.stop()  # Detiene la ejecución aquí si no está autenticado

# ═══════════════════════════════════════════════════════════════════════════════
# USUARIO AUTENTICADO - FORMULARIO INICIAL
# ═══════════════════════════════════════════════════════════════════════════════

# Inicializar datos del franquiciatario si no existen
if 'datos_franquicia' not in st.session_state:
    st.session_state['datos_franquicia'] = None

# Si no ha llenado el formulario, mostrarlo
if st.session_state['datos_franquicia'] is None:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <div style="font-size: 36px; font-weight: bold;">
            <span style="color: #00A651;">+FARMACIA</span> 
            <span style="color: #003D7A;">LÍBANO</span>
        </div>
        <div style="font-size: 20px; color: #003D7A; margin-top: 15px;">
            Corrida Financiera para Franquicias
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📋 Datos de la Corrida Financiera")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("datos_franquicia_form"):
            nombre_franquiciatario = st.text_input(
                "👤 Nombre del Franquiciatario:",
                placeholder="Ej: Juan Pérez García"
            )
            ubicacion_franquicia = st.text_input(
                "📍 Ubicación/Ciudad de la Franquicia:",
                placeholder="Ej: Monterrey, N.L."
            )
            proposito = st.selectbox(
                "🎯 Propósito de esta corrida:",
                [
                    "Nueva apertura",
                    "Análisis de expansión",
                    "Revisión de desempeño",
                    "Presentación a inversionistas",
                    "Otro"
                ]
            )
            notas = st.text_area(
                "📝 Notas adicionales (opcional):",
                placeholder="Cualquier información relevante...",
                height=80
            )
            
            submit_datos = st.form_submit_button("▶️ Continuar a la Corrida", use_container_width=True)
            
            if submit_datos:
                if nombre_franquiciatario.strip() and ubicacion_franquicia.strip():
                    st.session_state['datos_franquicia'] = {
                        'nombre': nombre_franquiciatario.strip(),
                        'ubicacion': ubicacion_franquicia.strip(),
                        'proposito': proposito,
                        'notas': notas.strip()
                    }
                    # Registrar la corrida en el log
                    registrar_corrida(st.session_state['datos_franquicia'], st.session_state.get('usuario_nombre', 'Usuario'))
                    st.rerun()
                else:
                    st.error("Por favor completa el nombre y la ubicación")
    
    # Botón de logout
    st.markdown("---")
    col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
    with col_l2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state['acceso_autorizado'] = False
            st.session_state['datos_franquicia'] = None
            st.rerun()
    
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL - Header limpio
# ═══════════════════════════════════════════════════════════════════════════════

# Header compacto con info del usuario y franquicia
datos_f = st.session_state['datos_franquicia']
col_h1, col_h2, col_h3 = st.columns([3, 2, 1])
with col_h1:
    st.markdown(f"""
    <div style="font-size: 14px; color: #d8e6f5;">
        <strong style="color: #8ac5ff;">{datos_f['nombre']}</strong> · {datos_f['ubicacion']} · {datos_f['proposito']}
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.caption(f"Sesión: {st.session_state.get('usuario_nombre', 'Usuario')}")
with col_h3:
    if st.button("🚪 Salir", key="logout_main"):
        st.session_state['acceso_autorizado'] = False
        st.session_state['datos_franquicia'] = None
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES Y ESTILO FARMACIA LÍBANO
# ═══════════════════════════════════════════════════════════════════════════════
VERDE = "#00A651"
AZUL = "#003D7A"

st.markdown(f"""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background:
            radial-gradient(circle at top right, rgba(36, 92, 156, 0.18), transparent 22%),
            radial-gradient(circle at top left, rgba(18, 74, 124, 0.14), transparent 16%),
            linear-gradient(180deg, #020d1f 0%, #05162f 40%, #08284b 100%);
    }}
    [data-testid="stHeader"] {{
        background: rgba(2, 13, 31, 0.90);
        border-bottom: 1px solid rgba(138, 197, 255, 0.10);
    }}
    [data-testid="stAppViewBlockContainer"] {{
        padding-top: 2rem;
    }}
    .main, .main p, .main li, .main label, .main span {{
        color: #e6eef7;
    }}
    .main small, .main .stCaption, div[data-testid="stCaptionContainer"] p {{
        color: #bed0e4 !important;
    }}
    .main hr {{
        border-color: rgba(162, 184, 210, 0.12);
    }}
    /* Header y títulos */
    .main h1 {{
        color: #f6fbff !important;
    }}
    .main h2, .main h3 {{
        color: #dff5eb !important;
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {AZUL} 0%, #002952 100%);
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stNumberInput label,
    [data-testid="stSidebar"] .stSlider label {{
        color: white !important;
        font-weight: 500;
    }}
    
    /* Metrics */
    [data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.055);
        border: 1px solid rgba(214, 231, 248, 0.11);
        border-radius: 18px;
        padding: 14px 16px 12px 16px;
        min-height: 138px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }}
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
        color: #dce8f6 !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricValue"] {{
        color: #f6fbff !important;
        font-weight: 800 !important;
    }}
    [data-testid="stMetricDelta"] {{
        color: {VERDE} !important;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: white;
        border: 2px solid {VERDE};
        border-radius: 8px;
        color: {VERDE};
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {VERDE} !important;
        color: white !important;
    }}
    
    /* Info boxes */
    .stAlert {{
        border-left: 4px solid {VERDE};
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        font-weight: 600;
        color: white !important;
    }}
    
    /* Logo header */
    .logo-header {{
        text-align: center;
        padding: 10px;
        margin-bottom: 20px;
    }}
    .logo-text {{
        font-size: 28px;
        font-weight: bold;
    }}
    .logo-green {{
        color: {VERDE};
    }}
    .logo-blue {{
        color: #3b8ed8;
    }}
    .logo-slogan {{
        font-style: italic;
        color: #8ac5ff;
        font-size: 14px;
    }}

    .sidebar-scenario-box {{
        background: linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.05) 100%);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 16px;
        padding: 14px 14px 10px 14px;
        margin: 8px 0 14px 0;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }}
    .sidebar-scenario-title {{
        color: #dff5eb;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 10px;
    }}
    .sidebar-scenario-grid {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
    }}
    .sidebar-scenario-kpi {{
        background: rgba(4, 20, 37, 0.32);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 10px 12px;
    }}
    .sidebar-scenario-kpi span {{
        display: block;
        color: #b8cce1 !important;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 2px;
    }}
    .sidebar-scenario-kpi strong {{
        color: #ffffff;
        font-size: 18px;
        font-weight: 800;
        line-height: 1.1;
    }}

    .sales-hero {{
        background: linear-gradient(135deg, {AZUL} 0%, #0b5a97 58%, #dff5eb 58%, #f7fbf8 100%);
        border-radius: 22px;
        padding: 26px 28px;
        margin: 8px 0 24px 0;
        box-shadow: 0 18px 38px rgba(0, 61, 122, 0.12);
    }}
    .sales-hero h2 {{
        margin: 0 0 8px 0;
        color: white !important;
        font-size: 32px;
        line-height: 1.05;
    }}
    .sales-hero p {{
        margin: 0;
        color: rgba(255,255,255,0.92);
        font-size: 14px;
        line-height: 1.5;
        max-width: 640px;
    }}
    .sales-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-top: 14px;
    }}
    .sales-stat {{
        background: rgba(255,255,255,0.92);
        border-radius: 18px;
        padding: 14px 16px;
        min-height: 106px;
    }}
    .sales-stat-label {{
        font-size: 11px;
        color: #5d7187;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
        font-weight: 700;
    }}
    .sales-stat-value {{
        font-size: 28px;
        line-height: 1;
        color: {AZUL};
        font-weight: 800;
        margin-bottom: 8px;
    }}
    .sales-stat-caption {{
        font-size: 12px;
        color: #536273;
        line-height: 1.45;
    }}
    .sales-card {{
        background: white;
        border: 1px solid rgba(0, 61, 122, 0.10);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 24px rgba(0, 61, 122, 0.06);
        height: 100%;
    }}
    .sales-card h4 {{
        margin: 0 0 8px 0;
        color: {AZUL};
        font-size: 18px;
    }}
    .sales-card p {{
        margin: 0;
        color: #556474;
        font-size: 13px;
        line-height: 1.55;
    }}
    .sales-card strong {{
        color: {AZUL};
    }}
    .sales-section-title {{
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #5a7088;
        margin-bottom: 10px;
        font-weight: 700;
    }}
    .sales-callout {{
        border-radius: 18px;
        padding: 18px 20px;
        margin: 10px 0 18px 0;
        border: 1px solid rgba(0, 61, 122, 0.10);
        background: linear-gradient(180deg, #f8fbfd 0%, #eef6fb 100%);
    }}
    .sales-callout h3 {{
        margin: 0 0 8px 0;
        color: {AZUL} !important;
        font-size: 20px;
    }}
    .sales-callout p {{
        margin: 0;
        color: #546679;
        line-height: 1.6;
        font-size: 13px;
    }}
    .sales-checklist {{
        margin: 10px 0 0 0;
        padding-left: 18px;
        color: #4f6173;
        font-size: 13px;
        line-height: 1.6;
    }}
    .sales-checklist li {{
        margin-bottom: 4px;
    }}
    .insight-panel {{
        border-radius: 18px;
        padding: 18px 20px;
        border: 1px solid rgba(0, 61, 122, 0.10);
        background: white;
        box-shadow: 0 10px 24px rgba(0, 61, 122, 0.05);
        margin: 8px 0 16px 0;
    }}
    .insight-kicker {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6a7e91;
        font-weight: 700;
        margin-bottom: 8px;
    }}
    .insight-panel h4 {{
        margin: 0 0 8px 0;
        color: {AZUL};
        font-size: 20px;
    }}
    .insight-panel p {{
        margin: 0;
        color: #556474;
        font-size: 13px;
        line-height: 1.6;
    }}
    .insight-list {{
        margin: 12px 0 0 0;
        padding-left: 18px;
        color: #4f6173;
        font-size: 13px;
        line-height: 1.6;
    }}
    .insight-list li {{
        margin-bottom: 4px;
    }}
    .summary-strip {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 8px 0 18px 0;
    }}
    .summary-box {{
        border-radius: 16px;
        padding: 16px;
        background: linear-gradient(180deg, #ffffff 0%, #f5f9fc 100%);
        border: 1px solid rgba(0, 61, 122, 0.08);
    }}
    .summary-box strong {{
        display: block;
        margin-bottom: 6px;
        color: {AZUL};
        font-size: 14px;
    }}
    .summary-box span {{
        color: #5a6c7d;
        font-size: 12px;
        line-height: 1.5;
    }}
    @media (max-width: 980px) {{
        .sales-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        .summary-strip {{
            grid-template-columns: 1fr;
        }}
    }}
    @media (max-width: 640px) {{
        .sales-grid {{
            grid-template-columns: 1fr;
        }}
        .sales-hero {{
            background: linear-gradient(180deg, {AZUL} 0%, #0b5a97 55%, #f7fbf8 55%, #f7fbf8 100%);
        }}
    }}
</style>
""", unsafe_allow_html=True)

# Función para formatear dinero
def fmt_dinero(valor):
    if valor >= 1_000_000:
        return f"${valor:,.0f}"
    return f"${valor:,.0f}"

MESES_PROYECCION = 30
DIAS_MES = 30

BANDAS_RETORNO = {
    "Conservador": {"etiqueta": "Máximo", "payback_min": 27.0, "payback_max": 30.0, "equilibrio_mes": 8},
    "Medio": {"etiqueta": "Intermedio", "payback_min": 20.0, "payback_max": 26.0, "equilibrio_mes": 7},
    "Alto": {"etiqueta": "Óptimo", "payback_min": 18.0, "payback_max": 19.0, "equilibrio_mes": 6},
}

MINIMOS_MODELO = {
    "🏪 Mini": {"flujo": 35, "flujo_vehicular": 50, "ticket": 75, "horas": 10},
    "🩺 Consultorio": {"flujo": 45, "flujo_vehicular": 70, "ticket": 90, "horas": 10},
    "🛒 Super": {"flujo": 60, "flujo_vehicular": 90, "ticket": 110, "horas": 10},
}

CONVERSION_MINIMA = {"Conservador": 3.5, "Medio": 4.0, "Alto": 5.0}
CAPTACION_VEHICULAR_MINIMA = {"Conservador": 0.4, "Medio": 0.6, "Alto": 1.0}
SURTEN_MINIMO = {"Conservador": 52.0, "Medio": 60.0, "Alto": 68.0}
CRECIMIENTO_ESCENARIO = {"Conservador": 0.015, "Medio": 0.035, "Alto": 0.05}
ARRANQUE_ESCENARIO = {"Conservador": 0.55, "Medio": 0.68, "Alto": 0.78}
RAMPA_MAXIMA_ESCENARIO = {"Conservador": 5, "Medio": 4, "Alto": 3}
ARRANQUE_OPCIONES_UI = {
    "Prudente (55%)": 0.55,
    "Comercial (68%)": 0.68,
    "Fuerte (78%)": 0.78,
}
CRECIMIENTO_OPCIONES_UI = {
    "Base (1.5%/mes)": 0.015,
    "Comercial (3.5%/mes)": 0.035,
    "Acelerado (5%/mes)": 0.05,
}
DEFAULT_ARRANQUE_ESCENARIO = {
    "Conservador": "Prudente (55%)",
    "Medio": "Comercial (68%)",
    "Alto": "Fuerte (78%)",
}
ARRANQUE_OPCIONES_POR_ESCENARIO = {
    "Conservador": ["Prudente (55%)", "Comercial (68%)", "Fuerte (78%)"],
    "Medio": ["Comercial (68%)", "Fuerte (78%)"],
    "Alto": ["Fuerte (78%)"],
}
DEFAULT_CRECIMIENTO_ESCENARIO = {
    "Conservador": "Base (1.5%/mes)",
    "Medio": "Comercial (3.5%/mes)",
    "Alto": "Acelerado (5%/mes)",
}
MES_TOPE_OPERATIVO_ESCENARIO = {
    "Conservador": 16,
    "Medio": 16,
    "Alto": 16,
}
CRECIMIENTO_OPCIONES_POR_ESCENARIO = {
    "Conservador": ["Base (1.5%/mes)", "Comercial (3.5%/mes)", "Acelerado (5%/mes)"],
    "Medio": ["Comercial (3.5%/mes)", "Acelerado (5%/mes)"],
    "Alto": ["Acelerado (5%/mes)"],
}
RAMPA_OPCIONES_POR_ESCENARIO = {
    "Conservador": [3, 4, 5],
    "Medio": [3, 4],
    "Alto": [3],
}

GASTOS_FIJOS_AUTOMATICOS = {
    "🏪 Mini": {
        "Cumplimiento sanitario (RP / RPBI)": 500,
    },
    "🩺 Consultorio": {
        "Cumplimiento sanitario (RP / RPBI)": 500,
    },
    "🛒 Super": {
        "Cumplimiento sanitario (RP / RPBI)": 500,
    },
}

GASTOS_FIJOS_EDITABLES = {
    "🏪 Mini": {
        "Renta": 8000,
        "Nómina": 6000,
        "Luz": 1500,
        "Internet/Tel": 500,
        "Contador": 1000,
        "Seguros": 500,
        "Limpieza": 500,
    },
    "🩺 Consultorio": {
        "Renta": 12000,
        "Nómina farmacia": 8000,
        "Nómina médico": 10000,
        "Luz": 2500,
        "Internet/Tel": 800,
        "Contador": 1500,
        "Seguros": 1200,
        "Limpieza": 800,
        "Insumos médicos": 1200,
    },
    "🛒 Super": {
        "Renta": 18000,
        "Nómina farmacia": 10000,
        "Nómina médico": 10000,
        "Nómina abarrotes": 5000,
        "Luz": 4000,
        "Internet/Tel": 1000,
        "Contador": 2000,
        "Seguros": 1500,
        "Limpieza": 1200,
        "Insumos médicos": 1300,
    },
}

MODELO_COMERCIAL = {
    "🏪 Mini": {
        "headline": "Entrada ágil al negocio farmacéutico",
        "pitch": "Un formato ligero para abrir rápido, operar simple y capitalizar la demanda diaria de medicamentos esenciales.",
        "cards": [
            ("Inversión accesible", "Permite presentar una oportunidad de entrada más ligera y con recuperación controlada."),
            ("Operación simple", "Menos complejidad operativa facilita supervisión, capacitación y apertura más veloz."),
            ("Mercado amplio", "Se apoya en categorías de alta rotación y consumo recurrente en prácticamente cualquier zona."),
        ],
        "cierre": "Es una buena base cuando se busca una unidad rentable, fácil de controlar y clara de ejecutar.",
    },
    "🩺 Consultorio": {
        "headline": "Farmacia con ancla médica y mayor ticket",
        "pitch": "Combina dispensación con consulta para capturar más recetas, elevar frecuencia de compra y fortalecer fidelización.",
        "cards": [
            ("Doble ingreso", "La mezcla farmacia + consulta amplía las fuentes de ingreso y eleva el ticket blended."),
            ("Receta inmediata", "La cercanía entre consulta y surtido impulsa conversión y recompra de forma natural."),
            ("Mayor fidelidad", "La relación médico-paciente sostiene recurrencia y vuelve más estable la sucursal."),
        ],
        "cierre": "Funciona bien cuando se busca diferenciación y una historia clara de tráfico calificado.",
    },
    "🛒 Super": {
        "headline": "Formato integral con tráfico y venta cruzada",
        "pitch": "Suma farmacia, consultorio y conveniencia para maximizar visitas, diversificar ingresos y elevar permanencia en tienda.",
        "cards": [
            ("Mayor tráfico", "La conveniencia agrega razones de visita y sostiene flujo más frecuente durante el día."),
            ("Venta cruzada", "Cada visita puede convertirse en varias líneas de ingreso dentro del mismo ticket."),
            ("Diversificación", "Reduce dependencia de una sola categoría y fortalece la estabilidad operativa del negocio."),
        ],
        "cierre": "Funciona mejor cuando se quiere una unidad robusta, visible y con una ruta de crecimiento superior.",
    },
}

ESCENARIO_COMERCIAL = {
    "Conservador": "Lectura prudente para validar que la ubicación resiste incluso con un arranque más frío.",
    "Medio": "Escenario base porque combina realismo operativo y una recuperación defendible.",
    "Alto": "Muestra el techo comercial alcanzable cuando la ejecución, la visibilidad y la ubicación juegan a favor.",
}


def redondear_miles(valor):
    return int(round(valor / 1000.0) * 1000)


def limitar(valor, minimo=None, maximo=None):
    if minimo is not None:
        valor = max(valor, minimo)
    if maximo is not None:
        valor = min(valor, maximo)
    return valor


def obtener_gastos_fijos_modelo(modelo):
    return {**GASTOS_FIJOS_EDITABLES[modelo], **GASTOS_FIJOS_AUTOMATICOS[modelo]}


def construir_factores_mensuales(
    arranque_inicial,
    meses_rampa,
    crec,
    mes_tope_operativo=None,
    meses_proyeccion=MESES_PROYECCION,
):
    rampa = np.linspace(arranque_inicial, 1.0, meses_rampa)
    factores = []
    factor_tope = None
    if mes_tope_operativo is not None:
        if mes_tope_operativo <= meses_rampa:
            factor_tope = float(rampa[max(mes_tope_operativo - 1, 0)])
        else:
            factor_tope = float((1 + crec) ** (mes_tope_operativo - meses_rampa))
    for t in range(meses_proyeccion):
        mes_actual = t + 1
        if t < meses_rampa:
            factor = rampa[t]
        else:
            factor_crecimiento = ((1 + crec) ** (t - meses_rampa + 1))
            if factor_tope is not None and mes_actual > mes_tope_operativo:
                factor = factor_tope
            else:
                factor = factor_crecimiento
        factores.append(factor)
    factor_tope_efectivo = max(factores) if factores else 1.0
    return factores, factor_tope_efectivo, mes_tope_operativo


def clasificar_retorno(meses_recuperacion):
    if not np.isfinite(meses_recuperacion):
        return "Fuera de estándar"
    if meses_recuperacion <= BANDAS_RETORNO["Alto"]["payback_max"]:
        return BANDAS_RETORNO["Alto"]["etiqueta"]
    if meses_recuperacion <= BANDAS_RETORNO["Medio"]["payback_max"]:
        return BANDAS_RETORNO["Medio"]["etiqueta"]
    if meses_recuperacion <= BANDAS_RETORNO["Conservador"]["payback_max"]:
        return BANDAS_RETORNO["Conservador"]["etiqueta"]
    return "Fuera de estándar"


def construir_retorno_visual(meses_recuperacion, escenario, cumple_estandar):
    meta = BANDAS_RETORNO[escenario]
    banda_corta = f"{meta['payback_min']:.0f}-{meta['payback_max']:.0f}m"
    banda_larga = f"{meta['payback_min']:.0f}-{meta['payback_max']:.0f} meses"
    if cumple_estandar and np.isfinite(meses_recuperacion):
        retorno_real = f"{meses_recuperacion:.1f} meses"
        return {
            "hero": f"{meses_recuperacion:.1f}m",
            "metrica": retorno_real,
            "resumen": f"{retorno_real}, dentro de la banda objetivo {banda_larga}.",
            "caption": f"Recuperación ya dentro de la banda comercial {banda_larga}.",
        }

    return {
        "hero": banda_corta,
        "metrica": banda_larga,
        "resumen": f"Objetivo comercial {banda_larga}. Hoy la corrida requiere ajuste para volver a ese rango.",
        "caption": f"Banda comercial del escenario. Hoy la corrida requiere ajuste para volver a {banda_larga}.",
    }


def _render_sales_cards(cards, eyebrow="Argumento Comercial"):
    columnas = st.columns(len(cards))
    for col, (titulo, descripcion) in zip(columnas, cards):
        with col:
            st.markdown(
                f"""
                <div class="sales-card">
                    <div class="sales-section-title">{escape(str(eyebrow))}</div>
                    <h4>{titulo}</h4>
                    <p>{descripcion}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_insight_panel(kicker, titulo, descripcion, bullets=None):
    bullets_html = ""
    if bullets:
        bullets_html = '<ul class="insight-list">' + "".join(f"<li>{item}</li>" for item in bullets) + "</ul>"
    st.markdown(
        f"""
        <div class="insight-panel">
            <div class="insight-kicker">{kicker}</div>
            <h4>{titulo}</h4>
            <p>{descripcion}</p>
            {bullets_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_strip(items):
    if not items:
        return

    cols = st.columns(len(items))
    for col, (titulo, descripcion) in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div class="summary-box">
                    <strong>{escape(str(titulo))}</strong>
                    <span>{escape(str(descripcion))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_horizontal_bar_chart(data, titulo, color):
    etiquetas = list(data.keys())
    valores = list(data.values())
    if not valores:
        return

    fig, ax = plt.subplots(figsize=(6.2, max(2.8, len(etiquetas) * 0.55)))
    posiciones = np.arange(len(etiquetas))
    ax.barh(posiciones, valores, color=color, alpha=0.88)
    ax.set_yticks(posiciones, etiquetas)
    ax.invert_yaxis()
    ax.set_title(titulo, loc="left", fontsize=13, fontweight="bold", color=AZUL)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.18)
    ax.tick_params(axis="y", labelsize=10)
    ax.tick_params(axis="x", labelsize=9)
    for idx, valor in enumerate(valores):
        ax.text(valor * 1.01 if valor > 0 else 0, idx, fmt_dinero(valor), va="center", fontsize=9, color=AZUL)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def calcular_resultados_proyectados(
    *,
    modelo,
    escenario,
    inversion_base,
    flujo,
    flujo_vehicular,
    conversion,
    captacion_vehicular,
    horas,
    dias,
    ticket,
    consultas,
    surten,
    ticket_receta,
    ingreso_consulta,
    abarrotes_pct,
    cogs,
    cogs_receta,
    cogs_abarrotes,
    gastos_fijos,
    gastos_var,
    arranque_inicial,
    meses_rampa,
    crec,
    gasto_lanzamiento,
    meses_proyeccion=MESES_PROYECCION,
):
    meta = BANDAS_RETORNO[escenario]
    colchon_operativo = redondear_miles(max(inversion_base * 0.08, gastos_fijos, gasto_lanzamiento * 2))
    inversion_total = inversion_base + colchon_operativo

    flujo_peatonal_mes = flujo * horas * dias
    flujo_vehicular_mes = flujo_vehicular * horas * dias
    clientes_peatonales_mes = int(flujo_peatonal_mes * conversion)
    clientes_vehiculares_mes = int(flujo_vehicular_mes * captacion_vehicular)
    clientes_mes = max(clientes_peatonales_mes + clientes_vehiculares_mes, 0)

    ventas_farmacia_base = clientes_mes * ticket
    consultas_mes = consultas * dias if consultas else 0
    ventas_recetas_base = consultas_mes * surten * ticket_receta
    ingresos_consulta_base = consultas_mes * ingreso_consulta
    ventas_abarrotes_base = ventas_farmacia_base * abarrotes_pct if abarrotes_pct else 0
    ventas_totales_base = max(
        ventas_farmacia_base + ventas_recetas_base + ventas_abarrotes_base + ingresos_consulta_base,
        0,
    )

    cogs_farmacia_base = ventas_farmacia_base * cogs
    cogs_recetas_base = ventas_recetas_base * cogs_receta
    cogs_abarrotes_base = ventas_abarrotes_base * cogs_abarrotes
    cogs_total_base = cogs_farmacia_base + cogs_recetas_base + cogs_abarrotes_base
    gastos_variables_base = ventas_totales_base * gastos_var
    contribucion = (
        (ventas_totales_base - cogs_total_base - gastos_variables_base) / ventas_totales_base
        if ventas_totales_base > 0
        else 0
    )

    clientes_totales_base = clientes_mes + (consultas_mes if consultas_mes else 0)
    ticket_prom = ventas_totales_base / clientes_totales_base if clientes_totales_base > 0 else 0
    ventas_be = gastos_fijos / contribucion if contribucion > 0 else ventas_totales_base
    clientes_be = ventas_be / ticket_prom if contribucion > 0 and ticket_prom > 0 else clientes_totales_base
    porcentaje_equilibrio = (ventas_be / ventas_totales_base * 100) if ventas_totales_base > 0 else 100
    porcentaje_equilibrio = limitar(porcentaje_equilibrio, 0, 100)
    margen_seguridad = max(100 - porcentaje_equilibrio, 0)

    factores, techo_maduro_factor_efectivo, mes_tope_operativo = construir_factores_mensuales(
        arranque_inicial,
        meses_rampa,
        crec,
        mes_tope_operativo=MES_TOPE_OPERATIVO_ESCENARIO[escenario],
        meses_proyeccion=meses_proyeccion,
    )

    def simular_escala(scale, incluir_detalle):
        proyeccion = []
        proyeccion_num = []
        utilidades_raw = []
        utilidades_display = []
        recuperado_acumulado = 0.0
        meses_recuperacion_real = float("inf")
        mes_equilibrio_real = float("inf")
        ventas_tope = 0.0
        utilidad_tope = 0.0

        ventas_farmacia = ventas_farmacia_base * scale
        ventas_recetas = ventas_recetas_base * scale
        ventas_abarrotes = ventas_abarrotes_base * scale
        ingresos_consulta = ingresos_consulta_base * scale
        ventas_totales = ventas_farmacia + ventas_recetas + ventas_abarrotes + ingresos_consulta
        cogs_total = (
            (ventas_farmacia * cogs)
            + (ventas_recetas * cogs_receta)
            + (ventas_abarrotes * cogs_abarrotes)
        )
        utilidad_bruta = ventas_totales - cogs_total
        gastos_variables = ventas_totales * gastos_var
        utilidad_neta_raw = utilidad_bruta - gastos_fijos - gastos_variables
        utilidad_neta_display = max(utilidad_neta_raw, 0)
        margen_neto = utilidad_neta_display / ventas_totales if ventas_totales > 0 else 0
        clientes_mes_escala = clientes_mes * scale
        ticket_prom_escala = ventas_totales / (clientes_totales_base * scale) if clientes_totales_base > 0 else 0

        for t, factor in enumerate(factores):
            flujo_peatonal_mes_t = flujo_peatonal_mes * factor
            flujo_vehicular_mes_t = flujo_vehicular_mes * factor
            clientes_peatonales_mes_t = clientes_peatonales_mes * factor
            clientes_vehiculares_mes_t = clientes_vehiculares_mes * factor
            tickets_mes_t = clientes_peatonales_mes_t + clientes_vehiculares_mes_t
            vf = ventas_farmacia * factor
            vr = ventas_recetas * factor
            va = ventas_abarrotes * factor
            ic = ingresos_consulta * factor
            vt = vf + vr + va + ic

            ct = (vf * cogs) + (vr * cogs_receta) + (va * cogs_abarrotes)
            ub = vt - ct
            gv = vt * gastos_var
            gasto_extra_t = gasto_lanzamiento if t < 3 else 0
            un_raw = ub - gastos_fijos - gv - gasto_extra_t
            un_display = max(un_raw, 0)
            capital_trabajo_t = max(-un_raw, 0)
            mn = un_display / vt if vt > 0 else 0
            ventas_tope = max(ventas_tope, vt)
            utilidad_tope = max(utilidad_tope, un_display)

            utilidades_raw.append(un_raw)
            utilidades_display.append(un_display)

            recuperado_previo = recuperado_acumulado
            recuperado_acumulado += un_display
            saldo_por_recuperar = max(inversion_total - recuperado_acumulado, 0)
            roi_acumulado = recuperado_acumulado / inversion_total if inversion_total > 0 else 0

            if mes_equilibrio_real == float("inf") and un_raw >= 0:
                mes_equilibrio_real = t + 1
            if meses_recuperacion_real == float("inf") and recuperado_acumulado >= inversion_total and un_display > 0:
                faltante = max(inversion_total - recuperado_previo, 0)
                meses_recuperacion_real = t + (faltante / un_display)

            if incluir_detalle:
                proyeccion.append({
                    "Mes": t + 1,
                    "Escenario": escenario,
                    "Peatones": f"{round(flujo_peatonal_mes_t):,}",
                    "Vehículos": f"{round(flujo_vehicular_mes_t):,}",
                    "Conv. peat.": f"{conversion * 100:.1f}%",
                    "Capt. veh.": f"{captacion_vehicular * 100:.1f}%",
                    "Tickets": f"{round(tickets_mes_t):,}",
                    "Ventas": f"${round(vt):,}",
                    "COGS": f"${round(ct):,}",
                    "Util. Bruta": f"${round(max(ub, 0)):,.0f}",
                    "Gastos Fijos": f"${round(gastos_fijos):,}",
                    "Gastos Var.": f"${round(gv):,}",
                    "Capital de trabajo": f"${round(capital_trabajo_t):,}",
                    "Util. Neta": f"${round(un_display):,}",
                    "Recuperado": f"${round(recuperado_acumulado):,}",
                    "Saldo por recuperar": f"${round(saldo_por_recuperar):,}",
                    "ROI Acum.": f"{roi_acumulado * 100:.1f}%",
                    "Margen %": f"{round(mn * 100, 1)}%",
                })
                proyeccion_num.append({
                    "Mes": t + 1,
                    "Escenario": escenario,
                    "Peatones": round(flujo_peatonal_mes_t),
                    "Vehículos": round(flujo_vehicular_mes_t),
                    "Conv. peat.": round(conversion * 100, 1),
                    "Capt. veh.": round(captacion_vehicular * 100, 1),
                    "Tickets": round(tickets_mes_t),
                    "Ventas": round(vt),
                    "Capital de trabajo": round(capital_trabajo_t),
                    "Util. Neta": round(un_display),
                    "Recuperado": round(recuperado_acumulado),
                    "Saldo por recuperar": round(saldo_por_recuperar),
                    "ROI Acum.": round(roi_acumulado * 100, 1),
                    "Margen %": round(mn * 100, 1),
                })

        util_anual_raw = sum(utilidades_raw[:12])
        util_anual_display = sum(utilidades_display[:12])
        ventas_anual = sum(
            (
                (ventas_farmacia * factor)
                + (ventas_recetas * factor)
                + (ventas_abarrotes * factor)
                + (ingresos_consulta * factor)
            )
            for factor in factores[:12]
        )
        roi_anual = (max(util_anual_raw, 0) / inversion_total) if inversion_total > 0 else 0
        utilidad_run_rate = max(utilidades_display[-1], utilidad_neta_display, 0)
        if meses_recuperacion_real == float("inf") and utilidad_run_rate > 0:
            remanente = max(inversion_total - recuperado_acumulado, 0)
            if remanente > 0:
                meses_recuperacion_real = meses_proyeccion + (remanente / utilidad_run_rate)

        return {
            "ventas_farmacia": ventas_farmacia,
            "ventas_recetas": ventas_recetas,
            "ingresos_consulta": ingresos_consulta,
            "ventas_abarrotes": ventas_abarrotes,
            "ventas_totales": ventas_totales,
            "cogs_total": cogs_total,
            "gastos_variables": gastos_variables,
            "utilidad_bruta": max(utilidad_bruta, 0),
            "utilidad_neta_raw": utilidad_neta_raw,
            "utilidad_neta_display": utilidad_neta_display,
            "margen_neto": margen_neto,
            "clientes_mes": clientes_mes_escala,
            "ticket_prom": ticket_prom_escala,
            "mes_equilibrio_real": mes_equilibrio_real,
            "meses_recuperacion_real": meses_recuperacion_real,
            "util_anual_raw": util_anual_raw,
            "util_anual_display": util_anual_display,
            "ventas_anual": ventas_anual,
            "roi_anual": roi_anual,
            "ventas_mes_1": round(
                ventas_farmacia * factores[0]
                + ventas_recetas * factores[0]
                + ventas_abarrotes * factores[0]
                + ingresos_consulta * factores[0]
            ),
            "utilidad_mes_1": round(utilidades_display[0]) if utilidades_display else 0,
            "ventas_tope": round(ventas_tope),
            "utilidad_tope": round(utilidad_tope),
            "proyeccion": proyeccion,
            "proyeccion_num": proyeccion_num,
            "recuperado_mes_30": recuperado_acumulado,
        }

    def cumple_estandar(simulacion):
        return (
            simulacion["utilidad_neta_raw"] > 0
            and np.isfinite(simulacion["meses_recuperacion_real"])
            and simulacion["meses_recuperacion_real"] <= meta["payback_max"]
            and np.isfinite(simulacion["mes_equilibrio_real"])
            and simulacion["mes_equilibrio_real"] <= meta["equilibrio_mes"]
        )

    resultado_actual = simular_escala(1.0, incluir_detalle=True)
    cumple_estandar_comercial = cumple_estandar(resultado_actual)
    escala_minima_requerida = 1.0 if cumple_estandar_comercial else None
    resultado_objetivo = resultado_actual if cumple_estandar_comercial else None

    if not cumple_estandar_comercial:
        escala_alta = 1.0
        resultado_alto = resultado_actual
        while escala_alta < 8.0:
            escala_alta *= 1.15
            resultado_alto = simular_escala(escala_alta, incluir_detalle=False)
            if cumple_estandar(resultado_alto):
                break

        if cumple_estandar(resultado_alto):
            escala_baja = 1.0
            for _ in range(30):
                escala_media = (escala_baja + escala_alta) / 2
                resultado_medio = simular_escala(escala_media, incluir_detalle=False)
                if cumple_estandar(resultado_medio):
                    escala_alta = escala_media
                    resultado_alto = resultado_medio
                else:
                    escala_baja = escala_media
            escala_minima_requerida = escala_alta
            resultado_objetivo = simular_escala(escala_minima_requerida, incluir_detalle=False)

    ventas_estables_minimas = resultado_objetivo["ventas_totales"] if resultado_objetivo else None
    utilidad_estable_minima = resultado_objetivo["utilidad_neta_display"] if resultado_objetivo else None
    tickets_mes_minimos = int(np.ceil(resultado_objetivo["clientes_mes"])) if resultado_objetivo else None
    ticket_blended_minimo = (
        ventas_estables_minimas / tickets_mes_minimos
        if resultado_objetivo and tickets_mes_minimos
        else None
    )
    faltante_ventas = max((ventas_estables_minimas or 0) - resultado_actual["ventas_totales"], 0)
    faltante_tickets = max((tickets_mes_minimos or 0) - int(np.ceil(resultado_actual["clientes_mes"])), 0)
    mejora_utilidad_requerida = max((utilidad_estable_minima or 0) - resultado_actual["utilidad_neta_display"], 0)
    gasto_fijo_meta = (
        max(gastos_fijos - mejora_utilidad_requerida, 0)
        if resultado_objetivo
        else None
    )
    reduccion_gastos_fijos_requerida = (
        max(gastos_fijos - gasto_fijo_meta, 0)
        if gasto_fijo_meta is not None
        else None
    )
    incremento_ticket_blended = max((ticket_blended_minimo or 0) - resultado_actual["ticket_prom"], 0)
    mes_objetivo_indice = min(int(np.ceil(meta["payback_max"])), meses_proyeccion)
    recuperado_meta_actual = (
        resultado_actual["proyeccion_num"][mes_objetivo_indice - 1]["Recuperado"]
        if resultado_actual["proyeccion_num"] and mes_objetivo_indice > 0
        else 0
    )
    inversion_maxima_presentable = min(inversion_total, recuperado_meta_actual) if recuperado_meta_actual > 0 else 0
    recorte_inversion_requerido = max(inversion_total - inversion_maxima_presentable, 0)

    meses_recuperacion_real = resultado_actual["meses_recuperacion_real"]
    meses_recuperacion_fmt = (
        f"{meses_recuperacion_real:.1f} meses"
        if np.isfinite(meses_recuperacion_real)
        else "Fuera de estándar"
    )
    anios_recuperacion_fmt = (
        f"{meses_recuperacion_real / 12:.1f} años"
        if np.isfinite(meses_recuperacion_real)
        else "Fuera de estándar"
    )

    return {
        "colchon_operativo": colchon_operativo,
        "inversion_total": inversion_total,
        "flujo_peatonal_mes": flujo_peatonal_mes,
        "flujo_vehicular_mes": flujo_vehicular_mes,
        "clientes_peatonales_mes": clientes_peatonales_mes,
        "clientes_vehiculares_mes": clientes_vehiculares_mes,
        "clientes_mes": resultado_actual["clientes_mes"],
        "ventas_farmacia": resultado_actual["ventas_farmacia"],
        "consultas_mes": consultas_mes,
        "ventas_recetas": resultado_actual["ventas_recetas"],
        "ingresos_consulta": resultado_actual["ingresos_consulta"],
        "ventas_abarrotes": resultado_actual["ventas_abarrotes"],
        "ventas_totales": resultado_actual["ventas_totales"],
        "cogs_total": resultado_actual["cogs_total"],
        "utilidad_bruta": resultado_actual["utilidad_bruta"],
        "gastos_variables": resultado_actual["gastos_variables"],
        "utilidad_neta": resultado_actual["utilidad_neta_display"],
        "utilidad_neta_raw": resultado_actual["utilidad_neta_raw"],
        "margen_neto": resultado_actual["margen_neto"],
        "ticket_prom": resultado_actual["ticket_prom"],
        "contribucion": contribucion,
        "ventas_be": ventas_be,
        "clientes_be": clientes_be,
        "porcentaje_equilibrio": porcentaje_equilibrio,
        "margen_seguridad": margen_seguridad,
        "mes_equilibrio_objetivo": meta["equilibrio_mes"],
        "mes_equilibrio_real": resultado_actual["mes_equilibrio_real"],
        "proyeccion": resultado_actual["proyeccion"],
        "proyeccion_num": resultado_actual["proyeccion_num"],
        "df": pd.DataFrame(resultado_actual["proyeccion"]),
        "df_num": pd.DataFrame(resultado_actual["proyeccion_num"]),
        "util_anual": max(resultado_actual["util_anual_display"], 0),
        "util_anual_raw": resultado_actual["util_anual_raw"],
        "ventas_anual": resultado_actual["ventas_anual"],
        "roi_anual": resultado_actual["roi_anual"],
        "meses_recuperacion": meses_recuperacion_real,
        "meses_recuperacion_real": meses_recuperacion_real,
        "meses_recuperacion_fmt": meses_recuperacion_fmt,
        "anios_recuperacion_fmt": anios_recuperacion_fmt,
        "ventas_mes_1": resultado_actual["ventas_mes_1"],
        "utilidad_mes_1": resultado_actual["utilidad_mes_1"],
        "ventas_mes_estable": resultado_actual["ventas_totales"],
        "utilidad_mes_estable": resultado_actual["utilidad_neta_display"],
        "ventas_tope": resultado_actual["ventas_tope"],
        "utilidad_tope": resultado_actual["utilidad_tope"],
        "techo_maduro_factor": techo_maduro_factor_efectivo,
        "mes_tope_operativo": mes_tope_operativo,
        "cumple_estandar_comercial": cumple_estandar_comercial,
        "clasificacion_retorno": clasificar_retorno(meses_recuperacion_real),
        "meta_comercial": {
            "alcanzable": resultado_objetivo is not None,
            "escala_minima_requerida": escala_minima_requerida,
            "ventas_estables_minimas": ventas_estables_minimas,
            "utilidad_estable_minima": utilidad_estable_minima,
            "tickets_mes_minimos": tickets_mes_minimos,
            "ticket_blended_minimo": ticket_blended_minimo,
            "incremento_ticket_blended": incremento_ticket_blended,
            "faltante_ventas": faltante_ventas,
            "faltante_tickets": faltante_tickets,
            "mejora_utilidad_requerida": mejora_utilidad_requerida,
            "gasto_fijo_meta": gasto_fijo_meta,
            "reduccion_gastos_fijos_requerida": reduccion_gastos_fijos_requerida,
            "recuperado_meta_actual": recuperado_meta_actual,
            "inversion_maxima_presentable": inversion_maxima_presentable,
            "recorte_inversion_requerido": recorte_inversion_requerido,
            "retorno_maximo_presentable": meta["payback_max"],
            "equilibrio_maximo_presentable": meta["equilibrio_mes"],
            "retorno_objetivo": (
                resultado_objetivo["meses_recuperacion_real"]
                if resultado_objetivo and np.isfinite(resultado_objetivo["meses_recuperacion_real"])
                else None
            ),
        },
    }

# ═══════════════════════════════════════════════════════════════════════════════
# PRESETS POR MODELO DE FRANQUICIA Y ESCENARIO
# ═══════════════════════════════════════════════════════════════════════════════
MODELOS = {
    "🏪 Mini": {"consultorio": False, "abarrotes": False, "inversion": 570000},
    "🩺 Consultorio": {"consultorio": True, "abarrotes": False, "inversion": 700000},
    "🛒 Super": {"consultorio": True, "abarrotes": True, "inversion": 950000},
}

# ANÁLISIS DE MÁRGENES POR CATEGORÍA (Como analista financiero de farmacias)
# Genéricos: 35-45% margen | Patente: 15-25% margen | Abarrotes: 8-15% margen
# Mix promedio ponderado según flujo y conversión por escenario

PRESETS = {
    "🏪 Mini": {
        "Conservador": {"flujo": 75, "conversion": 0.035, "ticket": 110, "cogs": 0.68, "gastos_fijos": 22000, "gastos_var": 0.03, "crec": 0.03},
        "Medio":       {"flujo": 65, "conversion": 0.04, "ticket": 100, "cogs": 0.68, "gastos_fijos": 28000, "gastos_var": 0.03, "crec": 0.035},
        "Alto":        {"flujo": 60, "conversion": 0.05, "ticket": 95, "cogs": 0.68, "gastos_fijos": 35000, "gastos_var": 0.03, "crec": 0.05},
    },
    "🩺 Consultorio": {
        "Conservador": {"flujo": 45, "conversion": 0.035, "ticket": 95, "cogs": 0.69, "gastos_fijos": 35000, "gastos_var": 0.03, "crec": 0.03,
                        "consultas": 12, "surten": 0.52, "ticket_receta": 180, "ingreso_consulta": 45, "cogs_receta": 0.61},
        "Medio":       {"flujo": 50, "conversion": 0.04, "ticket": 95, "cogs": 0.68, "gastos_fijos": 45000, "gastos_var": 0.03, "crec": 0.035,
                        "consultas": 10, "surten": 0.60, "ticket_receta": 160, "ingreso_consulta": 50, "cogs_receta": 0.60},
        "Alto":        {"flujo": 50, "conversion": 0.05, "ticket": 100, "cogs": 0.68, "gastos_fijos": 58000, "gastos_var": 0.03, "crec": 0.05,
                        "consultas": 10, "surten": 0.68, "ticket_receta": 150, "ingreso_consulta": 45, "cogs_receta": 0.58},
    },
    "🛒 Super": {
        "Conservador": {"flujo": 60, "conversion": 0.035, "ticket": 110, "cogs": 0.71, "gastos_fijos": 48000, "gastos_var": 0.03, "crec": 0.03,
                        "consultas": 14, "surten": 0.52, "ticket_receta": 200, "ingreso_consulta": 50, "cogs_receta": 0.60,
                        "abarrotes_pct": 0.18, "cogs_abarrotes": 0.90},
        "Medio":       {"flujo": 60, "conversion": 0.04, "ticket": 110, "cogs": 0.69, "gastos_fijos": 62000, "gastos_var": 0.03, "crec": 0.035,
                        "consultas": 12, "surten": 0.60, "ticket_receta": 180, "ingreso_consulta": 55, "cogs_receta": 0.60,
                        "abarrotes_pct": 0.18, "cogs_abarrotes": 0.89},
        "Alto":        {"flujo": 60, "conversion": 0.05, "ticket": 110, "cogs": 0.67, "gastos_fijos": 78000, "gastos_var": 0.03, "crec": 0.05,
                        "consultas": 8, "surten": 0.68, "ticket_receta": 200, "ingreso_consulta": 60, "cogs_receta": 0.57,
                        "abarrotes_pct": 0.18, "cogs_abarrotes": 0.88},
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown(f'''
<div style="text-align: center; padding: 10px 0 20px 0;">
    <div style="font-size: 22px; font-weight: bold;">
        <span style="color: {VERDE};">+FARMACIA</span> 
        <span style="color: white;">LÍBANO</span>
    </div>
    <div style="font-style: italic; font-size: 11px; color: #aaa;">Siempre al cuidado de tu salud</div>
</div>
''', unsafe_allow_html=True)

st.sidebar.markdown("### ⚙️ Configuración")

# Modelo y escenario
modelo = st.sidebar.selectbox("Modelo de Franquicia", list(MODELOS.keys()))
escenario = st.sidebar.selectbox("Escenario", ["Conservador", "Medio", "Alto"], index=1)
p = PRESETS[modelo][escenario]
m = MODELOS[modelo]
banda_sidebar = BANDAS_RETORNO[escenario]
st.sidebar.caption(
    f"Meta comercial: retorno {banda_sidebar['payback_min']:.0f}-{banda_sidebar['payback_max']:.0f} meses "
    f"y equilibrio en mes {banda_sidebar['equilibrio_mes']}."
)
st.sidebar.markdown(
    f"""
    <div class="sidebar-scenario-box">
        <div class="sidebar-scenario-title">Parámetros Iniciales del Escenario</div>
        <div class="sidebar-scenario-grid">
            <div class="sidebar-scenario-kpi">
                <span>Retorno Meta</span>
                <strong>{banda_sidebar['payback_min']:.0f}-{banda_sidebar['payback_max']:.0f} meses</strong>
            </div>
            <div class="sidebar-scenario-kpi">
                <span>Punto de Equilibrio</span>
                <strong>Mes {banda_sidebar['equilibrio_mes']}</strong>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Explicación de escenarios
with st.sidebar.expander("📚 ¿Qué significa cada escenario?", expanded=False):
    st.markdown("""
    **🔴 CONSERVADOR**: Para ser cauteloso
    - Ubicación nueva o con mucha competencia
    - Zona con poco flujo peatonal
    - Clientes aún no te conocen
    - Prefieres "pecar de precavido"
    
    **🟡 MEDIO**: Lo más probable que pase
    - Ubicación decente con flujo normal
    - Algo de competencia pero manejable
    - Ya tienes algunos clientes fieles
    - Escenario "realista" más común
    
    **🟢 ALTO**: Si todo sale perfecto
    - Excelente ubicación (esquina, plaza, etc.)
    - Poco o nada de competencia cerca
    - Zona con mucho flujo peatonal
    - Clientes muy fieles que te recomiendan
    """)
    
    st.info(f"""
    **Tu escenario actual: {escenario}**
    
    {'🔴 Mejor prevenir que lamentar' if escenario == 'Conservador' 
     else '🟡 El punto medio más realista' if escenario == 'Medio'
     else '🟢 El mejor de los casos posibles'}
    """)

st.sidebar.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# INVERSIÓN INICIAL EDITABLE
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar.expander("💰 Inversión Inicial", expanded=False):
    st.caption(f"Usa el monto sugerido o ajústalo manualmente para {modelo}")

    if st.session_state.get("modelo_inversion_simple") != modelo:
        st.session_state["inversion_simple"] = m["inversion"]
        st.session_state["modelo_inversion_simple"] = modelo

    inversion_input = st.number_input(
        "Monto total de inversión inicial ($)",
        min_value=100000,
        value=st.session_state.get("inversion_simple", m["inversion"]),
        step=10000,
        key="inversion_simple",
        help="Incluye adecuación, inventario inicial, permisos y capital de trabajo"
    )

    st.session_state.inversion_personalizada = inversion_input

    diferencia = inversion_input - m["inversion"]
    if diferencia > 0:
        st.info(f"📈 +${diferencia:,} sobre precio base")
    elif diferencia < 0:
        st.success(f"📉 ${abs(diferencia):,} menos que precio base")
    else:
        st.info("💰 Precio base estándar")

    st.markdown(f"**Inversión total estimada: ${inversion_input:,}**")

# Usar inversión personalizada
inversion = st.session_state.inversion_personalizada

# Parámetros técnicos base
cogs = p["cogs"]
cogs_receta = p.get("cogs_receta", cogs)
cogs_abarrotes = p.get("cogs_abarrotes", 0.88)
minimos_modelo = MINIMOS_MODELO[modelo]
combo_parametros_iniciales = f"{modelo}|{escenario}"

if st.session_state.get("combo_parametros_iniciales") != combo_parametros_iniciales:
    st.session_state["combo_parametros_iniciales"] = combo_parametros_iniciales
    st.session_state["flujo_sidebar"] = max(int(p["flujo"]), minimos_modelo["flujo"])
    st.session_state["flujo_vehicular_sidebar"] = max(minimos_modelo["flujo_vehicular"], int(st.session_state["flujo_sidebar"] * 1.5))
    st.session_state["conversion_sidebar"] = max(float(p.get("conversion", CONVERSION_MINIMA[escenario] / 100) * 100), float(CONVERSION_MINIMA[escenario]))
    st.session_state["captacion_vehicular_sidebar"] = float(CAPTACION_VEHICULAR_MINIMA[escenario])
    st.session_state["horas_sidebar"] = max(int(p.get("horas", 12)), minimos_modelo["horas"])
    st.session_state["ticket_sidebar"] = min(max(int(p["ticket"]), minimos_modelo["ticket"]), 220)
    st.session_state["gasto_variable_simple"] = min(max(float(p.get("gastos_var", 0.03) * 100), 0.0), 5.0)
    st.session_state["arranque_sidebar"] = DEFAULT_ARRANQUE_ESCENARIO[escenario]
    st.session_state["meses_rampa_sidebar"] = RAMPA_MAXIMA_ESCENARIO[escenario]
    st.session_state["crecimiento_sidebar"] = DEFAULT_CRECIMIENTO_ESCENARIO[escenario]
    st.session_state["gasto_lanzamiento_sidebar"] = {"🏪 Mini": 12000, "🩺 Consultorio": 18000, "🛒 Super": 25000}[modelo]
    if m["consultorio"]:
        st.session_state["consultas_sidebar"] = int(max(p.get("consultas", 0), 0))
        st.session_state["ingreso_consulta_sidebar"] = int(max(p.get("ingreso_consulta", 40), 0))
        st.session_state["ticket_receta_sidebar"] = int(max(p.get("ticket_receta", 120), 80))
        st.session_state["surten_sidebar"] = max(float(p.get("surten", SURTEN_MINIMO[escenario] / 100) * 100), float(SURTEN_MINIMO[escenario]))

with st.sidebar.expander("👥 Tráfico peatonal y vehicular", expanded=True):
    st.caption("La corrida aplica pisos comerciales para evitar escenarios inferiores a una operación rentable.")
    flujo = st.number_input(
        "Peatones por hora",
        min_value=minimos_modelo["flujo"],
        value=st.session_state.get("flujo_sidebar", max(p["flujo"], minimos_modelo["flujo"])),
        step=5,
        key="flujo_sidebar",
        help="Personas caminando frente al local en una hora normal"
    )
    flujo_vehicular = st.number_input(
        "Vehículos por hora",
        min_value=minimos_modelo["flujo_vehicular"],
        value=st.session_state.get("flujo_vehicular_sidebar", max(minimos_modelo["flujo_vehicular"], int(p["flujo"] * 1.5))),
        step=10,
        key="flujo_vehicular_sidebar",
        help="Autos o motos que pasan frente al local"
    )
    conversion = st.number_input(
        "Conversión peatonal (%)",
        min_value=float(CONVERSION_MINIMA[escenario]),
        value=st.session_state.get("conversion_sidebar", float(CONVERSION_MINIMA[escenario])),
        step=0.5,
        key="conversion_sidebar",
        help="Porcentaje de peatones que entra y compra"
    ) / 100
    captacion_vehicular = st.number_input(
        "Captación vehicular (%)",
        min_value=float(CAPTACION_VEHICULAR_MINIMA[escenario]),
        value=st.session_state.get("captacion_vehicular_sidebar", float(CAPTACION_VEHICULAR_MINIMA[escenario])),
        step=0.1,
        key="captacion_vehicular_sidebar",
        help="Porcentaje de vehículos que sí se detienen a comprar"
    ) / 100
    horas = st.number_input(
        "Horas abiertas por día",
        min_value=minimos_modelo["horas"],
        max_value=16,
        value=st.session_state.get("horas_sidebar", 12),
        step=1,
        key="horas_sidebar",
        help="Horario diario de operación de la sucursal"
    )
    dias = DIAS_MES

    flujo_peatonal_dia = flujo * horas
    flujo_vehicular_dia = flujo_vehicular * horas
    clientes_vehiculares_dia = flujo_vehicular_dia * captacion_vehicular
    st.info(
        f"📊 Tráfico diario estimado: **{flujo_peatonal_dia:,} peatones** y "
        f"**{flujo_vehicular_dia:,} vehículos**. Con tu captación, "
        f"eso agrega **~{clientes_vehiculares_dia:,.0f} tickets/día** desde autos."
    )

with st.sidebar.expander("🧾 Gasto variable", expanded=False):
    st.caption("Se mantiene dentro de un rango comercialmente saludable para no castigar de más la utilidad.")
    gasto_variable_pct = st.number_input(
        "Gasto variable sobre ventas (%)",
        min_value=0.0,
        max_value=5.0,
        value=min(st.session_state.get("gasto_variable_simple", float(p.get("gastos_var", 0.03) * 100)), 5.0),
        step=0.1,
        key="gasto_variable_simple",
        help="Si no estás seguro, deja el sugerido"
    )
    gastos_var = gasto_variable_pct / 100
    st.markdown(f"**Se descuenta {gasto_variable_pct:.1f}% de cada peso vendido**")

with st.sidebar.expander("🛒 ¿Cuánto compra cada cliente?", expanded=True):
    st.caption("💡 El ticket promedio es lo que gasta un cliente típico")
    ticket = st.number_input(
        "Ticket promedio farmacia ($)", 
        min_value=minimos_modelo["ticket"],
        max_value=220,
        value=st.session_state.get("ticket_sidebar", min(max(p["ticket"], minimos_modelo["ticket"]), 220)),
        step=5,
        key="ticket_sidebar",
        help="¿Cuánto gasta en promedio un cliente en farmacia?"
    )
    
    if ticket < 70:
        st.warning("⚠️ Ticket bajo - típico de zonas populares")
    elif ticket > 120:
        st.success("✅ Ticket alto - típico de zonas con mayor poder adquisitivo")

# Consultorio
if m["consultorio"]:
    with st.sidebar.expander("🩺 Consultorio médico", expanded=True):
        st.caption("💡 El consultorio genera ingresos extra y atrae clientes a la farmacia")
        consultas = st.number_input(
            "Consultas por día", 
            min_value=0,
            max_value=30,
            value=st.session_state.get("consultas_sidebar", min(max(p.get("consultas", 0), 0), 30)),
            step=1,
            key="consultas_sidebar",
            help="¿Cuántas consultas médicas esperas al día?"
        )
        ingreso_consulta = st.number_input(
            "Cobro por consulta ($)", 
            min_value=0,
            max_value=120,
            value=st.session_state.get("ingreso_consulta_sidebar", min(max(p.get("ingreso_consulta", 40), 0), 120)),
            step=5,
            key="ingreso_consulta_sidebar",
            help="¿Cuánto cobras por cada consulta?"
        )
        ticket_receta = st.number_input(
            "Compra promedio con receta ($)", 
            min_value=80,
            max_value=320,
            value=st.session_state.get("ticket_receta_sidebar", min(max(p.get("ticket_receta", 120), 80), 320)),
            step=10,
            key="ticket_receta_sidebar",
            help="Los pacientes con receta gastan más"
        )
        surten = st.number_input(
            "Pacientes que surten en tu farmacia (%)",
            min_value=float(SURTEN_MINIMO[escenario]),
            value=st.session_state.get("surten_sidebar", float(SURTEN_MINIMO[escenario])),
            step=5.0,
            key="surten_sidebar",
            help="No todos los pacientes compran la receta contigo"
        ) / 100
        
        ingresos_consultas_dia = consultas * ingreso_consulta
        st.info(f"💊 Ingreso diario por consultas: **${ingresos_consultas_dia:,}**")
else:
    consultas, surten, ticket_receta, ingreso_consulta, cogs_receta = 0, 0, 0, 0, cogs

# Abarrotes
if m["abarrotes"]:
    with st.sidebar.expander("🛒 Abarrotes", expanded=True):
        st.caption("💡 Los abarrotes atraen tráfico pero tienen menor margen")
        abarrotes_pct = p.get("abarrotes_pct", 0.15)
        st.info(f"📦 Abarrotes representan ~{int(abarrotes_pct*100)}% de las ventas de farmacia")
else:
    abarrotes_pct, cogs_abarrotes = 0, 0

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYGROUND DE GASTOS FIJOS
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar.expander("🏢 Gastos Fijos (Detalle)", expanded=True):
    st.caption("El cumplimiento sanitario se considera como un solo parámetro automático.")
    gf_default = obtener_gastos_fijos_modelo(modelo)
    gastos_automaticos_modelo = GASTOS_FIJOS_AUTOMATICOS[modelo]
    conceptos_automaticos_legado = {
        "Responsable sanitario (RP)",
        "RPBI",
        "Cumplimiento sanitario (RP / RPBI)",
    }
    
    # Inicializar estado
    if "gastos_fijos_items" not in st.session_state or st.session_state.get("modelo_gf_anterior") != modelo:
        st.session_state.gastos_fijos_items = gf_default.copy()
        st.session_state.modelo_gf_anterior = modelo
    else:
        for concepto in list(st.session_state.gastos_fijos_items.keys()):
            if concepto in conceptos_automaticos_legado and concepto not in gastos_automaticos_modelo:
                del st.session_state.gastos_fijos_items[concepto]
        for concepto, monto in gastos_automaticos_modelo.items():
            st.session_state.gastos_fijos_items[concepto] = monto
    
    # Mostrar items de gastos
    gastos_fijos_total = 0
    items_gf = list(st.session_state.gastos_fijos_items.keys())
    
    for item in items_gf:
        col1, col2 = st.columns([3, 1])
        with col1:
            nuevo_valor = st.number_input(
                f"🔒 {item}" if item in gastos_automaticos_modelo else item,
                min_value=0,
                value=st.session_state.gastos_fijos_items[item],
                step=100,
                key=f"gf_{item}",
                disabled=item in gastos_automaticos_modelo,
            )
            st.session_state.gastos_fijos_items[item] = nuevo_valor
        with col2:
            if item in gastos_automaticos_modelo:
                st.caption("Automático")
            elif st.button("🗑️", key=f"del_gf_{item}"):
                del st.session_state.gastos_fijos_items[item]
                st.rerun()
        gastos_fijos_total += nuevo_valor
    
    # Agregar nuevo gasto
    st.markdown("---")
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        nuevo_gasto = st.text_input("Nuevo gasto", key="new_gf_concept", placeholder="Ej: Publicidad")
    with col_g2:
        nuevo_monto_gf = st.number_input("Monto", min_value=0, value=0, step=100, key="new_gf_amount")
    
    if st.button("➕ Agregar gasto", key="add_gf"):
        if nuevo_gasto and nuevo_monto_gf > 0:
            st.session_state.gastos_fijos_items[nuevo_gasto] = nuevo_monto_gf
            st.rerun()
    
    st.markdown(f"**💵 Total Gastos Fijos: ${gastos_fijos_total:,}/mes**")

# Usar gastos fijos calculados
gastos_fijos = sum(st.session_state.gastos_fijos_items.values()) if "gastos_fijos_items" in st.session_state else p["gastos_fijos"]

# Proyección con rampa de arranque
with st.sidebar.expander("📈 Arranque y crecimiento", expanded=True):
    st.caption("Un negocio suele arrancar flojo, crecer rápido al inicio y luego estabilizarse.")
    opciones_arranque = ARRANQUE_OPCIONES_POR_ESCENARIO[escenario]
    arranque_opcion = st.selectbox(
        "Fuerza del arranque",
        opciones_arranque,
        key="arranque_sidebar",
        help="Qué tan cerca arranca el mes 1 del nivel estabilizado"
    )
    arranque_inicial = ARRANQUE_OPCIONES_UI[arranque_opcion]
    opciones_rampa = RAMPA_OPCIONES_POR_ESCENARIO[escenario]
    meses_rampa = st.selectbox(
        "Meses para estabilizar la sucursal (máx. 5)",
        opciones_rampa,
        key="meses_rampa_sidebar",
        help="Meses que tardas en llegar al nivel operativo normal"
    )
    opciones_crecimiento = CRECIMIENTO_OPCIONES_POR_ESCENARIO[escenario]
    crec_opcion = st.selectbox(
        "Crecimiento mensual una vez estabilizado",
        opciones_crecimiento,
        key="crecimiento_sidebar",
    )
    crec = CRECIMIENTO_OPCIONES_UI[crec_opcion]
    gasto_lanzamiento = st.number_input(
        "Gasto extra de apertura por mes (meses 1-3)",
        min_value=0,
        max_value=40000,
        value=st.session_state.get("gasto_lanzamiento_sidebar", {"🏪 Mini": 12000, "🩺 Consultorio": 18000, "🛒 Super": 25000}[modelo]),
        step=1000,
        key="gasto_lanzamiento_sidebar",
        help="Publicidad de apertura, promociones, contratación y ajustes iniciales"
    )

    arranque_inicial_efectivo = max(arranque_inicial, ARRANQUE_ESCENARIO[escenario])
    crec_efectivo = max(crec, CRECIMIENTO_ESCENARIO[escenario])
    meses_rampa_efectivos = min(meses_rampa, RAMPA_MAXIMA_ESCENARIO[escenario])
    candados_arranque = []
    if arranque_inicial_efectivo > arranque_inicial:
        candados_arranque.append(f"arranque mínimo {arranque_inicial_efectivo*100:.0f}%")
    if crec_efectivo > crec:
        candados_arranque.append(f"crecimiento mínimo {crec_efectivo*100:.1f}%")
    if meses_rampa_efectivos < meses_rampa:
        candados_arranque.append(f"rampa máxima {meses_rampa_efectivos} meses")

    st.info(
        f"📈 Tu escenario opera con un arranque de {arranque_inicial_efectivo*100:.0f}% del nivel estabilizado, "
        f"rampa de {meses_rampa_efectivos} meses y crecimiento posterior de {crec_efectivo*100:.1f}% mensual."
    )
    if candados_arranque:
        st.caption(f"Candado comercial aplicado: {', '.join(candados_arranque)}.")
    else:
        st.caption("Las opciones visibles ya respetan los mínimos comerciales del escenario.")

# ═══════════════════════════════════════════════════════════════════════════════
# CÁLCULOS - MES ESTABILIZADO
# ═══════════════════════════════════════════════════════════════════════════════
resultado = calcular_resultados_proyectados(
    modelo=modelo,
    escenario=escenario,
    inversion_base=inversion,
    flujo=flujo,
    flujo_vehicular=flujo_vehicular,
    conversion=conversion,
    captacion_vehicular=captacion_vehicular,
    horas=horas,
    dias=dias,
    ticket=ticket,
    consultas=consultas,
    surten=surten,
    ticket_receta=ticket_receta,
    ingreso_consulta=ingreso_consulta,
    abarrotes_pct=abarrotes_pct,
    cogs=cogs,
    cogs_receta=cogs_receta,
    cogs_abarrotes=cogs_abarrotes,
    gastos_fijos=gastos_fijos,
    gastos_var=gastos_var,
    arranque_inicial=arranque_inicial_efectivo,
    meses_rampa=meses_rampa_efectivos,
    crec=crec_efectivo,
    gasto_lanzamiento=gasto_lanzamiento,
)

meta_escenario_actual = BANDAS_RETORNO[escenario]
colchon_operativo = resultado["colchon_operativo"]
inversion_total = resultado["inversion_total"]
flujo_peatonal_mes = resultado["flujo_peatonal_mes"]
flujo_vehicular_mes = resultado["flujo_vehicular_mes"]
clientes_peatonales_mes = resultado["clientes_peatonales_mes"]
clientes_vehiculares_mes = resultado["clientes_vehiculares_mes"]
clientes_mes = resultado["clientes_mes"]
ventas_farmacia = resultado["ventas_farmacia"]
consultas_mes = resultado["consultas_mes"]
ventas_recetas = resultado["ventas_recetas"]
ingresos_consulta = resultado["ingresos_consulta"]
ventas_abarrotes = resultado["ventas_abarrotes"]
ventas_totales = resultado["ventas_totales"]
cogs_total = resultado["cogs_total"]
utilidad_bruta = resultado["utilidad_bruta"]
gastos_variables = resultado["gastos_variables"]
utilidad_neta = resultado["utilidad_neta"]
margen_neto = resultado["margen_neto"]
ticket_prom = resultado["ticket_prom"]
contribucion = resultado["contribucion"]
ventas_be = resultado["ventas_be"]
clientes_be = resultado["clientes_be"]
porcentaje_equilibrio = resultado["porcentaje_equilibrio"]
margen_seguridad = resultado["margen_seguridad"]
mes_equilibrio_objetivo = resultado["mes_equilibrio_objetivo"]
proyeccion = resultado["proyeccion"]
proyeccion_num = resultado["proyeccion_num"]
df = resultado["df"]
df_num = resultado["df_num"]
util_anual = resultado["util_anual"]
ventas_anual = resultado["ventas_anual"]
roi_anual = resultado["roi_anual"]
meses_recuperacion = resultado["meses_recuperacion"]
meses_recuperacion_fmt = resultado["meses_recuperacion_fmt"]
anios_recuperacion_fmt = resultado["anios_recuperacion_fmt"]
ventas_mes_1 = resultado["ventas_mes_1"]
utilidad_mes_1 = resultado["utilidad_mes_1"]
ventas_mes_estable = resultado["ventas_mes_estable"]
utilidad_mes_estable = resultado["utilidad_mes_estable"]
ventas_tope = resultado["ventas_tope"]
utilidad_tope = resultado["utilidad_tope"]
techo_maduro_factor = resultado["techo_maduro_factor"]
mes_tope_operativo = resultado["mes_tope_operativo"]
cumple_estandar_comercial = resultado["cumple_estandar_comercial"]
clasificacion_retorno = resultado["clasificacion_retorno"]
meta_comercial = resultado["meta_comercial"]
retorno_visual = construir_retorno_visual(meses_recuperacion, escenario, cumple_estandar_comercial)
clientes_mes_display = int(np.ceil(clientes_mes))
clientes_be_display = int(np.ceil(clientes_be)) if np.isfinite(clientes_be) else 0
techo_sobre_estable_pct = max((techo_maduro_factor - 1) * 100, 0)

resumen_escenarios = []
for escenario_pdf in ["Conservador", "Medio", "Alto"]:
    resultado_escenario = calcular_resultados_proyectados(
        modelo=modelo,
        escenario=escenario_pdf,
        inversion_base=inversion,
        flujo=max(flujo, MINIMOS_MODELO[modelo]["flujo"]),
        flujo_vehicular=max(flujo_vehicular, MINIMOS_MODELO[modelo]["flujo_vehicular"]),
        conversion=max(conversion, CONVERSION_MINIMA[escenario_pdf] / 100),
        captacion_vehicular=max(captacion_vehicular, CAPTACION_VEHICULAR_MINIMA[escenario_pdf] / 100),
        horas=max(horas, MINIMOS_MODELO[modelo]["horas"]),
        dias=dias,
        ticket=max(ticket, MINIMOS_MODELO[modelo]["ticket"]),
        consultas=consultas,
        surten=max(surten, SURTEN_MINIMO[escenario_pdf] / 100) if m["consultorio"] else surten,
        ticket_receta=ticket_receta,
        ingreso_consulta=ingreso_consulta,
        abarrotes_pct=abarrotes_pct,
        cogs=cogs,
        cogs_receta=cogs_receta,
        cogs_abarrotes=cogs_abarrotes,
        gastos_fijos=gastos_fijos,
        gastos_var=gastos_var,
        arranque_inicial=max(arranque_inicial_efectivo, ARRANQUE_ESCENARIO[escenario_pdf]),
        meses_rampa=min(meses_rampa_efectivos, RAMPA_MAXIMA_ESCENARIO[escenario_pdf]),
        crec=max(crec_efectivo, CRECIMIENTO_ESCENARIO[escenario_pdf]),
        gasto_lanzamiento=gasto_lanzamiento,
    )
    resumen_escenarios.append({
        "Escenario": escenario_pdf,
        "Seleccionado": "Sí" if escenario_pdf == escenario else "",
        "Perfil": resultado_escenario["clasificacion_retorno"],
        "Equilibrio meta": f"Mes {BANDAS_RETORNO[escenario_pdf]['equilibrio_mes']}",
        "Meta retorno": f"{BANDAS_RETORNO[escenario_pdf]['payback_min']:.0f}-{BANDAS_RETORNO[escenario_pdf]['payback_max']:.0f} meses",
        "Lectura retorno": (
            f"{resultado_escenario['meses_recuperacion_real']:.1f} meses"
            if resultado_escenario["cumple_estandar_comercial"] and np.isfinite(resultado_escenario["meses_recuperacion_real"])
            else "Requiere ajuste"
        ),
        "ROI año 1": f"{resultado_escenario['roi_anual'] * 100:.1f}%",
        "Ventas estables": f"${resultado_escenario['ventas_totales']:,.0f}",
        "Estatus": "Dentro del estándar" if resultado_escenario["cumple_estandar_comercial"] else "Requiere ajuste",
    })

# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
# Logo header
st.markdown(f'''
<div style="text-align: center; margin-bottom: 20px;">
    <div style="font-size: 36px; font-weight: bold;">
        <span style="color: {VERDE};">+FARMACIA</span> 
        <span style="color: {AZUL};">LÍBANO</span>
    </div>
    <div style="font-style: italic; color: {AZUL}; font-size: 14px;">Siempre al cuidado de tu salud</div>
</div>
''', unsafe_allow_html=True)

st.title(f"📊 Corrida Financiera - {modelo}")
st.markdown(
    f"**Escenario:** {escenario} | **Inversión base:** ${inversion:,} | "
    f"**Colchón:** ${colchon_operativo:,} | **Total a recuperar:** ${inversion_total:,}"
)
st.caption(
    f"Clasificación actual: **{clasificacion_retorno}**. "
    f"Meta del escenario: retorno máximo en {meta_escenario_actual['payback_max']:.0f} meses "
    f"y equilibrio a más tardar en el mes {meta_escenario_actual['equilibrio_mes']}."
)

copy_modelo = MODELO_COMERCIAL[modelo]
retorno_hero = retorno_visual["hero"]
retorno_real_texto = retorno_visual["caption"]
banda_objetivo_texto = f"{meta_escenario_actual['payback_min']:.0f}-{meta_escenario_actual['payback_max']:.0f} meses"
retorno_reporte = meses_recuperacion_fmt if cumple_estandar_comercial else f"Meta comercial {banda_objetivo_texto}"
retorno_reporte_detalle = (
    f"Recuperación ya dentro de la banda comercial {banda_objetivo_texto}."
    if cumple_estandar_comercial
    else f"Objetivo comercial del escenario: {banda_objetivo_texto}. Hoy la corrida requiere ajuste para volver a ese rango."
)
meta_ventas_texto = fmt_dinero(meta_comercial["ventas_estables_minimas"]) if meta_comercial["ventas_estables_minimas"] else "N/D"
meta_utilidad_texto = fmt_dinero(meta_comercial["utilidad_estable_minima"]) if meta_comercial["utilidad_estable_minima"] else "N/D"
meta_tickets_texto = f"{meta_comercial['tickets_mes_minimos']:,}" if meta_comercial["tickets_mes_minimos"] else "N/D"
faltante_ventas_texto = fmt_dinero(meta_comercial["faltante_ventas"]) if meta_comercial["faltante_ventas"] else fmt_dinero(0)
faltante_tickets_texto = f"{meta_comercial['faltante_tickets']:,}" if meta_comercial["faltante_tickets"] else "0"
meta_inversion_texto = fmt_dinero(meta_comercial["inversion_maxima_presentable"]) if meta_comercial["inversion_maxima_presentable"] else "N/D"
recorte_inversion_texto = fmt_dinero(meta_comercial["recorte_inversion_requerido"]) if meta_comercial["recorte_inversion_requerido"] else fmt_dinero(0)
gasto_fijo_meta_texto = fmt_dinero(meta_comercial["gasto_fijo_meta"]) if meta_comercial["gasto_fijo_meta"] is not None else "N/D"
reduccion_gf_texto = fmt_dinero(meta_comercial["reduccion_gastos_fijos_requerida"]) if meta_comercial["reduccion_gastos_fijos_requerida"] else fmt_dinero(0)
ticket_blended_meta_texto = fmt_dinero(meta_comercial["ticket_blended_minimo"]) if meta_comercial["ticket_blended_minimo"] else "N/D"
incremento_ticket_texto = fmt_dinero(meta_comercial["incremento_ticket_blended"]) if meta_comercial["incremento_ticket_blended"] else fmt_dinero(0)
retorno_principal_label = "Retorno estimado" if cumple_estandar_comercial else "Banda objetivo Líbano"
accion_ventas = (
    f"Llevar la venta estable hacia {meta_ventas_texto} al mes."
    if meta_comercial["alcanzable"]
    else "Revisar ubicación, mezcla y costos antes de volver a evaluar la sucursal."
)
accion_utilidad = (
    f"Sostener una utilidad estable cercana a {meta_utilidad_texto}."
    if meta_comercial["alcanzable"]
    else "Rearmar la estructura operativa con una base de costos más ligera."
)
accion_tickets = (
    f"Lograr al menos {meta_tickets_texto} tickets mensuales con la mezcla actual."
    if meta_comercial["alcanzable"]
    else "Revalidar tráfico, ticket y horario para construir una base operativa más sólida."
)
palancas_mejora = [
    (
        "Ajustar inversión inicial",
        f"Con el desempeño actual, el total a recuperar debería quedar alrededor de {meta_inversion_texto}. Eso implica recortar cerca de {recorte_inversion_texto} entre CAPEX, inventario inicial o gastos de apertura."
    ),
    (
        "Subir utilidad estabilizada",
        f"El caso necesita acercarse a {meta_utilidad_texto} mensuales. Hoy está en {fmt_dinero(utilidad_mes_estable)}, así que faltan aproximadamente {fmt_dinero(meta_comercial['mejora_utilidad_requerida'])} al mes."
    ),
    (
        "Aligerar gastos fijos",
        f"Si la ruta fuera por estructura, el gasto fijo mensual tendría que bajar hacia {gasto_fijo_meta_texto}. Eso equivale a recortar cerca de {reduccion_gf_texto} al mes."
    ),
]
condiciones_banda = [
    f"Ventas estables objetivo: {meta_ventas_texto} al mes, es decir {faltante_ventas_texto} por encima del nivel actual.",
    f"Tickets objetivo: {meta_tickets_texto} al mes. Con el ticket blended actual de {fmt_dinero(ticket_prom)}, eso implica sumar alrededor de {faltante_tickets_texto} tickets.",
    f"Ticket blended de referencia: {ticket_blended_meta_texto}. Si se prefiere subir ticket en vez de tráfico, haría falta alrededor de {incremento_ticket_texto} adicionales por ticket.",
]

st.markdown(
    f"""
    <div class="sales-hero">
        <h2>{copy_modelo['headline']}</h2>
        <p>{copy_modelo['pitch']}</p>
        <div class="sales-grid">
            <div class="sales-stat">
                <div class="sales-stat-label">{retorno_principal_label}</div>
                <div class="sales-stat-value">{retorno_hero}</div>
                <div class="sales-stat-caption">{retorno_real_texto}</div>
            </div>
            <div class="sales-stat">
                <div class="sales-stat-label">Ventas Estables</div>
                <div class="sales-stat-value">{fmt_dinero(ventas_mes_estable)}</div>
                <div class="sales-stat-caption">Run-rate mensual defendible para la conversación comercial.</div>
            </div>
            <div class="sales-stat">
                <div class="sales-stat-label">Utilidad Estable</div>
                <div class="sales-stat-value">{fmt_dinero(utilidad_mes_estable)}</div>
                <div class="sales-stat-caption">Lo que deja la unidad al estabilizarse, ya considerando costos operativos.</div>
            </div>
            <div class="sales-stat">
                <div class="sales-stat-label">ROI Año 1</div>
                <div class="sales-stat-value">{roi_anual * 100:.0f}%</div>
                <div class="sales-stat-caption">Impacto del arranque, apertura y crecimiento durante el primer año.</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("### 💼 Fortalezas del Formato")
_render_sales_cards(copy_modelo["cards"], eyebrow="Fortaleza del formato")

st.markdown(
    f"""
    <div class="sales-callout">
        <h3>Lectura del Escenario</h3>
        <p><strong>{escenario}:</strong> {ESCENARIO_COMERCIAL[escenario]} {copy_modelo['cierre']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Análisis y narrativa comercial
peatones_dia = flujo * horas
vehiculos_dia = flujo_vehicular * horas
tickets_vehiculares_dia = vehiculos_dia * captacion_vehicular
conversion_rate = conversion * 100
captacion_rate = captacion_vehicular * 100
costo_producto = cogs_total
gastos_extras = gastos_variables
total_gastos = costo_producto + gastos_fijos + gastos_extras

if contribucion <= 0:
    st.warning("⚠️ Los supuestos actuales están fuera del rango comercial sugerido. Ajusta costos o tráfico para mantener una corrida presentable.")
    st.stop()

desglose = {"💊 Farmacia": ventas_farmacia}
if m["consultorio"]:
    desglose["💉 Recetas"] = ventas_recetas
    desglose["🩺 Consultas"] = ingresos_consulta
if m["abarrotes"]:
    desglose["🛒 Abarrotes"] = ventas_abarrotes

margen_farmacia = (1 - cogs) * 100
margen_recetas = (1 - cogs_receta) * 100 if m["consultorio"] else None
margen_abarrotes = (1 - p.get("cogs_abarrotes", 0.9)) * 100 if m["abarrotes"] else None

costo_resurtido_farmacia = ventas_farmacia * cogs
gasto_variable_farmacia = ventas_farmacia * gastos_var
utilidad_productos_raw = ventas_farmacia - costo_resurtido_farmacia - gasto_variable_farmacia - gastos_fijos
utilidad_productos_display = max(utilidad_productos_raw, 0)
capital_trabajo_productos = max(-utilidad_productos_raw, 0)
clientes_dia = clientes_mes / dias if dias else 0
ventas_farmacia_dia = ventas_farmacia / dias if dias else 0
clientes_hora = clientes_dia / horas if horas else 0
ventas_farmacia_hora = ventas_farmacia_dia / horas if horas else 0

ventas_consultas_recetas = ingresos_consulta + ventas_recetas
costo_resurtido_recetas = ventas_recetas * cogs_receta
gasto_variable_consultas_recetas = ventas_consultas_recetas * gastos_var
utilidad_consultas_recetas_raw = ventas_consultas_recetas - costo_resurtido_recetas - gasto_variable_consultas_recetas
utilidad_consultas_recetas_display = max(utilidad_consultas_recetas_raw, 0)
capital_trabajo_consultas_recetas = max(-utilidad_consultas_recetas_raw, 0)
porcentaje_consultas = (consultas_mes / clientes_mes * 100) if clientes_mes else 0
recetas_mes = consultas_mes * surten if m["consultorio"] else 0

costo_resurtido_abarrotes = ventas_abarrotes * cogs_abarrotes if m["abarrotes"] else 0
gasto_variable_abarrotes = ventas_abarrotes * gastos_var if m["abarrotes"] else 0
utilidad_abarrotes_raw = ventas_abarrotes - costo_resurtido_abarrotes - gasto_variable_abarrotes
utilidad_abarrotes_display = max(utilidad_abarrotes_raw, 0)
capital_trabajo_abarrotes = max(-utilidad_abarrotes_raw, 0)
utilidad_operativa_display = max(utilidad_productos_raw + utilidad_consultas_recetas_raw + utilidad_abarrotes_raw, 0)
capital_trabajo_operativo = max(-(utilidad_productos_raw + utilidad_consultas_recetas_raw + utilidad_abarrotes_raw), 0)

productos_operativos_df = pd.DataFrame([{
    "Gastos fijos": fmt_dinero(gastos_fijos),
    "Peatones/hora": f"{flujo:,}",
    "Vehículos/hora": f"{flujo_vehicular:,}",
    "Horas/día": f"{horas:,}",
    "Días/mes": f"{dias:,}",
    "Flujo/mes": f"{round(flujo_peatonal_mes + flujo_vehicular_mes):,}",
    "% conv. peat.": f"{conversion_rate:.1f}%",
    "% capt. veh.": f"{captacion_rate:.1f}%",
    "Clientes/mes": f"{clientes_mes_display:,}",
    "Ticket promedio": fmt_dinero(ticket),
    "Ventas productos": fmt_dinero(ventas_farmacia),
    "Costo resurtido": fmt_dinero(costo_resurtido_farmacia),
    "Utilidad productos": fmt_dinero(utilidad_productos_display),
    "Capital trabajo": fmt_dinero(capital_trabajo_productos),
}])

productos_derivacion_df = pd.DataFrame([{
    "Clientes/día": f"{clientes_dia:,.0f}",
    "Ventas/día": fmt_dinero(ventas_farmacia_dia),
    "Clientes/hora": f"{clientes_hora:,.1f}",
    "Ventas/hora": fmt_dinero(ventas_farmacia_hora),
}])

consultas_recetas_df = pd.DataFrame([{
    "Clientes/mes": f"{clientes_mes_display:,}",
    "% consultas": f"{porcentaje_consultas:.1f}%",
    "Consultas/mes": f"{consultas_mes:,.0f}",
    "Precio consulta": fmt_dinero(ingreso_consulta),
    "Ventas consultas": fmt_dinero(ingresos_consulta),
    "% recetas": f"{surten*100:.1f}%" if m["consultorio"] else "0.0%",
    "Recetas/mes": f"{recetas_mes:,.0f}",
    "Precio receta": fmt_dinero(ticket_receta),
    "Ventas recetas": fmt_dinero(ventas_recetas),
    "Resurtido recetas": fmt_dinero(costo_resurtido_recetas),
    "Utilidad consultas y recetas": fmt_dinero(utilidad_consultas_recetas_display),
    "Capital trabajo": fmt_dinero(capital_trabajo_consultas_recetas),
}])

resumen_operativo_rows = [
    {
        "Línea": "Productos",
        "Ventas/mes": fmt_dinero(ventas_farmacia),
        "Utilidad/mes": fmt_dinero(utilidad_productos_display),
        "Capital trabajo": fmt_dinero(capital_trabajo_productos),
    }
]
if m["consultorio"]:
    resumen_operativo_rows.append({
        "Línea": "Consultas y recetas",
        "Ventas/mes": fmt_dinero(ventas_consultas_recetas),
        "Utilidad/mes": fmt_dinero(utilidad_consultas_recetas_display),
        "Capital trabajo": fmt_dinero(capital_trabajo_consultas_recetas),
    })
if m["abarrotes"]:
    resumen_operativo_rows.append({
        "Línea": "Conveniencia",
        "Ventas/mes": fmt_dinero(ventas_abarrotes),
        "Utilidad/mes": fmt_dinero(utilidad_abarrotes_display),
        "Capital trabajo": fmt_dinero(capital_trabajo_abarrotes),
    })
resumen_operativo_rows.append({
    "Línea": "Total mensual",
    "Ventas/mes": fmt_dinero(ventas_totales),
    "Utilidad/mes": fmt_dinero(utilidad_operativa_display),
    "Capital trabajo": fmt_dinero(capital_trabajo_operativo),
})
resumen_operativo_df = pd.DataFrame(resumen_operativo_rows)

escenario_visual = {
    "Conservador": {
        "titulo": "Lectura prudente para validar la ubicación",
        "descripcion": f"Sirve para mostrar que el proyecto todavía se sostiene aun con una conversión peatonal de {conversion_rate:.1f}% y un arranque más frío.",
        "bullets": [
            "Útil cuando el franquiciatario quiere ver control de riesgo antes de decidir.",
            "Pone la conversación en disciplina operativa, tráfico y curva de maduración.",
            "Si este escenario se defiende, la lectura de viabilidad gana mucha credibilidad.",
        ],
    },
    "Medio": {
        "titulo": "Escenario base para revisar viabilidad",
        "descripcion": f"Combina una conversión peatonal de {conversion_rate:.1f}% con una dinámica de crecimiento razonable para una conversación realista y sólida.",
        "bullets": [
            "Es la mejor base para revisar si la sucursal entra al estándar.",
            "Balancea prudencia financiera con una lectura operativa defendible.",
            "Ayuda a alinear expectativas sin perder tracción comercial.",
        ],
    },
    "Alto": {
        "titulo": "Techo comercial del formato",
        "descripcion": f"Expone el potencial máximo alcanzable con {conversion_rate:.1f}% de conversión peatonal, buena visibilidad y ejecución operativa fuerte.",
        "bullets": [
            "Sirve para enseñar el upside cuando la ubicación es premium.",
            "Muestra la mejor versión operativa del formato bajo buena ejecución.",
            "Debe usarse como marco de potencial, no como promesa automática.",
        ],
    },
}

argumentos_cards = [
    (
        "Caso de inversión",
        f"Con una inversión total de {fmt_dinero(inversion_total)} y una meta de retorno de {meta_escenario_actual['payback_min']:.0f}-{meta_escenario_actual['payback_max']:.0f} meses, la propuesta entra en una conversación de retorno clara y accionable."
    ),
    (
        "Defensa operativa",
        f"El punto de equilibrio exige {porcentaje_equilibrio:.0f}% de la venta estable, lo que deja un margen de seguridad de {margen_seguridad:.0f}% cuando la unidad madura."
    ),
    (
        "Historia de crecimiento",
        f"El arranque parte en {arranque_inicial_efectivo*100:.0f}% y luego escala con una dinámica de crecimiento que permite explicar la maduración del negocio sin prometer magia desde el mes uno."
    ),
]

tabs = st.tabs(["🎯 Cierre Ejecutivo", "👥 Mercado y Demanda", "🧮 Desglose Operativo", "💸 Economía", "📈 Proyección"])

with tabs[0]:
    st.markdown("### 🎯 Cierre Ejecutivo")
    if cumple_estandar_comercial:
        render_insight_panel(
            "Estatus de Viabilidad",
            "Dentro del estándar Líbano",
            f"La corrida ya cae en una banda comercial defendible. Recupera la inversión total en {meses_recuperacion_fmt} y proyecta un ROI del {roi_anual*100:.0f}% en el primer año.",
            [
                f"Mes 1 deja aproximadamente {fmt_dinero(utilidad_mes_1)}.",
                f"La unidad estabilizada deja alrededor de {fmt_dinero(utilidad_mes_estable)} al mes.",
                "La base operativa ya se sostiene con los parámetros actuales.",
            ],
        )
    elif meta_comercial["alcanzable"]:
        render_insight_panel(
            "Estatus de Viabilidad",
            "Ajustable para entrar a estándar",
            "La mezcla actual todavía no entra en la banda objetivo, pero la app ya señala el mínimo operativo para volverla defendible.",
            [
                f"Ventas estables mínimas: {fmt_dinero(meta_comercial['ventas_estables_minimas'])} al mes.",
                f"Utilidad estable mínima: {fmt_dinero(meta_comercial['utilidad_estable_minima'])} al mes.",
                f"Tickets mensuales mínimos: {meta_comercial['tickets_mes_minimos']:,}.",
            ],
        )
    else:
        render_insight_panel(
            "Estatus de Viabilidad",
            "Conviene replantear la base operativa",
            "La estructura actual no da una base suficiente para sostener la sucursal en la banda objetivo. Aquí conviene corregir ubicación, ticket o costos antes de seguir.",
            [
                "Todavía no conviene generar PDF.",
                "Primero hay que reconstruir la base económica de la sucursal.",
                "El objetivo es volver a una banda defendible sin forzar el discurso.",
            ],
        )

    render_summary_strip([
        ("Lectura de retorno", retorno_visual["resumen"]),
        ("Equilibrio operativo", f"Punto de equilibrio en {fmt_dinero(ventas_be)} y meta comercial de equilibrio al mes {mes_equilibrio_objetivo}."),
        ("Ruta de viabilidad", "Primero valida demanda y mezcla, después utilidad estabilizada y al final recuperación dentro del estándar."),
    ])

    st.markdown("### 📊 Números Clave")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("👥 Tickets/mes", f"{clientes_mes_display:,}")
        st.caption("Tickets mensuales estabilizados")
    with c2:
        st.metric("💵 Ventas mes 1", f"${ventas_mes_1:,.0f}")
        st.caption("Ya con rampa de arranque")
    with c3:
        st.metric("💰 Utilidad mes 1", f"${utilidad_mes_1:,.0f}")
        st.caption("Después de apertura y operación")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.metric("📈 Ventas estabilizadas", f"${ventas_mes_estable:,.0f}")
        st.caption("Mes maduro sin rampa")
    with c5:
        st.metric("🎯 Punto de equilibrio", f"${ventas_be:,.0f}")
        st.caption(f"{porcentaje_equilibrio:.0f}% de tus ventas estabilizadas")
    with c6:
        st.metric("📈 ROI Año 1", f"{roi_anual*100:.0f}%")
        st.caption("Ya incluye meses flojos y colchón")

    c7, c8, c9 = st.columns(3)
    with c7:
        st.metric("💼 Utilidad estabilizada", f"${utilidad_mes_estable:,.0f}")
        st.caption("Run-rate operativo esperado")
    with c8:
        st.metric("⏱️ Recuperación" if cumple_estandar_comercial else "🎯 Banda objetivo", retorno_visual["metrica"])
        st.caption(f"Estándar Líbano: {meta_escenario_actual['payback_min']:.0f}-{meta_escenario_actual['payback_max']:.0f} meses")
    with c9:
        st.metric("💸 Recuperado al mes 30", f"${df_num.iloc[-1]['Recuperado']:,.0f}")
        st.caption("Avance acumulado sobre la inversión total")

    if not cumple_estandar_comercial and meta_comercial["alcanzable"]:
        st.markdown("### 🧱 Estándar mínimo operativo")
        render_summary_strip([
            ("Meta ventas/mes", f"{fmt_dinero(meta_comercial['ventas_estables_minimas'])} para volver al estándar."),
            ("Meta utilidad/mes", f"{fmt_dinero(meta_comercial['utilidad_estable_minima'])} como run-rate mínimo."),
            ("Meta tickets/mes", f"{meta_comercial['tickets_mes_minimos']:,} tickets con la mezcla actual."),
        ])
        render_insight_panel(
            "Qué tendría que pasar",
            f"Para entrar a la banda {banda_objetivo_texto}",
            "La sucursal puede acercarse al estándar por desempeño, por estructura o por inversión inicial. La app te deja ver las tres rutas sin cambiar la historia financiera.",
            condiciones_banda,
        )

        st.markdown("### 🔧 Palancas de mejora")
        _render_sales_cards(palancas_mejora, eyebrow="Palanca cuantificada")

    st.markdown("### 🧭 Fortalezas del modelo")
    _render_sales_cards(argumentos_cards, eyebrow="Lectura del modelo")

    st.markdown("### 🤝 Ruta de viabilidad")
    col_cierre1, col_cierre2 = st.columns(2)
    with col_cierre1:
        st.markdown(
            """
            <div class="sales-card">
                <div class="sales-section-title">Lectura compartida</div>
                <h4>Cómo revisar esta sucursal en mesa</h4>
                <p>
                    Empieza por la demanda y la mezcla del formato, sigue con la utilidad estabilizada y cierra con el tiempo de recuperación.
                    La idea es que vendedor y franquiciatario lean la misma historia económica con orden y sin exagerar supuestos.
                </p>
                <ul class="sales-checklist">
                    <li>Primero: demanda local, tráfico y ticket.</li>
                    <li>Segundo: ventas estabilizadas, utilidad y equilibrio.</li>
                    <li>Tercero: inversión total, rampa de arranque y recuperación.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_cierre2:
        cierre_html = (
            f"""
            <div class="sales-card">
                <div class="sales-section-title">Siguiente paso recomendado</div>
                <h4>{'Caso listo para avanzar' if cumple_estandar_comercial else 'Ajustes antes de avanzar'}</h4>
                <p>{'La corrida ya puede usarse como base de decisión porque entra al estándar definido por Líbano.' if cumple_estandar_comercial else 'Todavía conviene ajustar supuestos antes de tomarla como base de decisión.'}</p>
                <ul class="sales-checklist">
                    <li>{'Preparar el PDF y revisar ubicación, inversión y cronograma.' if cumple_estandar_comercial else accion_ventas}</li>
                    <li>{'Validar que el equilibrio esperado sea consistente con la apertura.' if cumple_estandar_comercial else accion_utilidad}</li>
                    <li>{'Confirmar con el franquiciatario la base operativa y el plan de arranque.' if cumple_estandar_comercial else accion_tickets}</li>
                </ul>
            </div>
            """
        )
        st.markdown(cierre_html, unsafe_allow_html=True)

with tabs[1]:
    st.markdown("### 👥 Mercado y Demanda")
    render_summary_strip([
        ("Tráfico peatonal", f"{peatones_dia:,} personas al día con conversión peatonal de {conversion_rate:.1f}%."),
        ("Tráfico vehicular", f"{vehiculos_dia:,} vehículos al día con captación de {captacion_rate:.1f}%."),
        ("Maduración esperada", f"La unidad termina de crecer hacia el mes {mes_tope_operativo or MESES_PROYECCION}, alcanzando un techo operativo de {techo_sobre_estable_pct:.0f}% sobre el nivel estabilizado."),
    ])

    col_flujo1, col_flujo2, col_flujo3, col_flujo4 = st.columns(4)
    with col_flujo1:
        st.metric("🚶 Peatones/día", f"{peatones_dia:,}")
        st.caption("Flujo peatonal diario")
    with col_flujo2:
        st.metric("🚗 Vehículos/día", f"{vehiculos_dia:,}")
        st.caption(f"Captas {captacion_rate:.1f}%")
    with col_flujo3:
        st.metric("🛍️ Tickets desde autos/día", f"{tickets_vehiculares_dia:,.0f}")
        st.caption("Tráfico que sí se convierte")
    with col_flujo4:
        st.metric("💳 Ticket promedio", f"${ticket_prom:,.0f}")
        st.caption("Ticket blended con servicios")

    render_insight_panel(
        "Escenario Seleccionado",
        escenario_visual[escenario]["titulo"],
        escenario_visual[escenario]["descripcion"],
        escenario_visual[escenario]["bullets"],
    )

    col_merc1, col_merc2 = st.columns([1.15, 0.85])
    with col_merc1:
        st.markdown("#### 🧭 Comparativo de escenarios")
        st.dataframe(pd.DataFrame(resumen_escenarios), use_container_width=True, hide_index=True)
    with col_merc2:
        st.markdown("#### 💵 Mezcla de ingresos")
        render_horizontal_bar_chart(desglose, "Participación mensual por línea", VERDE)

with tabs[2]:
    st.markdown("### 🧮 Desglose Operativo")
    render_summary_strip([
        ("Escenario de flujo", f"{escenario}: {flujo:,} peatones/hora, {flujo_vehicular:,} vehículos/hora y {horas} horas abiertas al día."),
        ("Conversión", f"{conversion_rate:.1f}% de peatones y {captacion_rate:.1f}% de vehículos se convierten en tickets."),
        ("Ventas derivadas", f"{clientes_mes_display:,} tickets al mes con ticket promedio blended de {fmt_dinero(ticket_prom)}."),
    ])

    st.markdown("#### Productos")
    st.dataframe(productos_operativos_df, use_container_width=True, hide_index=True)
    st.dataframe(productos_derivacion_df, use_container_width=True, hide_index=True)

    if m["consultorio"]:
        st.markdown("#### Consultas y recetas")
        st.dataframe(consultas_recetas_df, use_container_width=True, hide_index=True)

    st.markdown("#### Ventas totales")
    st.dataframe(resumen_operativo_df, use_container_width=True, hide_index=True)
    st.caption(
        "El capital de trabajo muestra el soporte temporal del arranque cuando una línea todavía no deja utilidad positiva."
    )

with tabs[3]:
    st.markdown("### 💸 Economía del Negocio")
    render_summary_strip([
        ("Punto de equilibrio", f"{fmt_dinero(ventas_be)} al mes para cubrir la estructura fija."),
        ("Margen de seguridad", f"{margen_seguridad:.0f}% de holgura frente a la venta estabilizada."),
        ("Colchón operativo", f"{fmt_dinero(colchon_operativo)} incorporado para una lectura comercial más sólida."),
    ])

    col_mg1, col_mg2, col_mg3 = st.columns(3)
    with col_mg1:
        st.metric("💊 Margen Farmacia", f"{margen_farmacia:.0f}%")
        st.caption("Mix genéricos/patente optimizado")
    with col_mg2:
        if m["consultorio"]:
            st.metric("💉 Margen Recetas", f"{margen_recetas:.0f}%")
            st.caption("Recetas médicas especializadas")
        else:
            st.metric("💉 Recetas", "N/A")
            st.caption("No aplica en este modelo")
    with col_mg3:
        if m["abarrotes"]:
            st.metric("🛒 Margen Abarrotes", f"{margen_abarrotes:.0f}%")
            st.caption("Productos de conveniencia")
        else:
            st.metric("🛒 Abarrotes", "N/A")
            st.caption("No aplica en este modelo")

    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    with col_g1:
        st.metric("📦 Mercancía", f"${costo_producto:,.0f}")
        st.caption("Lo que te cuesta el producto")
    with col_g2:
        st.metric("🏢 Gastos Fijos", f"${gastos_fijos:,}")
        st.caption("Renta, nómina, luz, etc.")
    with col_g3:
        st.metric("📊 Gastos variables", f"${gastos_extras:,.0f}")
        st.caption(f"{gasto_variable_pct:.1f}% de las ventas")
    with col_g4:
        st.metric("📉 Total gastos", f"${total_gastos:,.0f}")
        st.caption("Antes de gastos de apertura")

    col_econ1, col_econ2 = st.columns(2)
    with col_econ1:
        render_horizontal_bar_chart(
            {"Mercancía": costo_producto, "Gastos fijos": gastos_fijos, "Gastos variables": gastos_extras},
            "En qué se va el dinero",
            AZUL,
        )
    with col_econ2:
        render_insight_panel(
            "Lectura Financiera",
            "Lo importante no es solo vender más, sino vender con margen",
            f"La utilidad estable proyectada ronda {fmt_dinero(utilidad_mes_estable)} y el equilibrio exige {porcentaje_equilibrio:.0f}% de la venta estable. Eso permite explicar de forma muy clara cuándo la sucursal empieza a dejar dinero de verdad.",
            [
                f"Mes de equilibrio objetivo: {mes_equilibrio_objetivo}.",
                f"Gasto extra de apertura: {fmt_dinero(gasto_lanzamiento)} por mes durante los primeros 3 meses.",
                f"Total a recuperar: {fmt_dinero(inversion_total)} incluyendo colchón.",
            ],
        )

    with st.expander("📋 Ver detalle de inversión y gastos"):
        col_inv, col_gf, col_gv = st.columns(3)
        with col_inv:
            st.markdown("**💰 Tu Inversión Inicial**")
            st.metric("Monto base", f"${inversion:,.0f}")
            st.caption(f"Colchón operativo automático: ${colchon_operativo:,.0f}")
            st.markdown(f"**Total a recuperar: ${inversion_total:,.0f}**")
        with col_gf:
            st.markdown("**🏢 Tus Gastos Fijos Mensuales**")
            if "gastos_fijos_items" in st.session_state:
                gf_df = pd.DataFrame([
                    {"Concepto": k, "Monto": f"${v:,}"}
                    for k, v in st.session_state.gastos_fijos_items.items()
                ])
                st.dataframe(gf_df, use_container_width=True, hide_index=True)
                st.markdown(f"**Total: ${gastos_fijos:,}/mes**")
        with col_gv:
            st.markdown("**📊 Tu Gasto Variable**")
            st.metric("Porcentaje", f"{gasto_variable_pct:.1f}%")
            st.caption(f"Más ${gasto_lanzamiento:,}/mes de apertura en meses 1-3")
            st.markdown(f"**Equilibrio operativo objetivo: mes {mes_equilibrio_objetivo}**")
            st.markdown(f"**Margen de seguridad: {margen_seguridad:.0f}%**")

with tabs[4]:
    st.markdown("### 📈 Proyección y Recuperación")
    render_summary_strip([
        ("Ventas del año", f"{fmt_dinero(ventas_anual)} proyectadas durante los primeros 12 meses."),
        ("Ganancia del año", f"{fmt_dinero(util_anual)} acumuladas durante el primer año."),
        ("Tope operativo", f"En el mes {mes_tope_operativo or MESES_PROYECCION} la unidad ronda {fmt_dinero(ventas_tope)} en ventas y {fmt_dinero(utilidad_tope)} de utilidad al mes."),
    ])
    st.caption(
        f"Cada mes deriva de un escenario {escenario.lower()} con {flujo:,} peatones/hora, "
        f"{flujo_vehicular:,} vehículos/hora, conversión peatonal de {conversion_rate:.1f}% "
        f"y captación vehicular de {captacion_rate:.1f}%."
    )
    st.caption(
        "La columna `Capital de trabajo` agrupa el soporte temporal del arranque y cualquier faltante del mes mientras la sucursal madura."
    )

    df_simple = pd.DataFrame([{
        "Mes": p["Mes"],
        "Escenario": p["Escenario"],
        "Peatones": p["Peatones"],
        "Vehículos": p["Vehículos"],
        "Conv. peat.": p["Conv. peat."],
        "Capt. veh.": p["Capt. veh."],
        "Tickets": p["Tickets"],
        "Ventas": p["Ventas"],
        "Capital de trabajo": p["Capital de trabajo"],
        "Te queda": p["Util. Neta"],
        "Recuperado": p["Recuperado"],
        "Saldo por recuperar": p["Saldo por recuperar"],
        "ROI acumulado": p["ROI Acum."],
    } for p in proyeccion])
    st.dataframe(df_simple, use_container_width=True, hide_index=True)

    st.markdown("#### Evolución mensual")
    st.line_chart(df_num.set_index("Mes")[["Ventas", "Util. Neta", "Recuperado"]])
    st.caption(
        f"La proyección ya considera un techo operativo. "
        f"A partir del mes {(mes_tope_operativo or MESES_PROYECCION) + 1}, la sucursal deja de crecer y se estabiliza."
    )

    render_insight_panel(
        "Resumen Final",
        f"Cómo leer esta oportunidad en una sola vista para {modelo}",
        f"Con una inversión total de {fmt_dinero(inversion_total)}, la unidad proyecta ventas estabilizadas de {fmt_dinero(ventas_totales)} y una utilidad estable de {fmt_dinero(utilidad_neta)}. La lectura de viabilidad se sostiene porque el proyecto enseña arranque, maduración y recuperación con una secuencia lógica.",
        [
            f"Mes 1 vende {fmt_dinero(ventas_mes_1)} y deja {fmt_dinero(utilidad_mes_1)}.",
            retorno_visual["caption"],
            f"Equilibrio operativo objetivo alrededor del mes {mes_equilibrio_objetivo}.",
        ],
    )

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE REPORTE PDF
# ═══════════════════════════════════════════════════════════════════════════════
def generar_reporte_pdf():
    """Genera un reporte PDF profesional para presentar oportunidad de franquicia"""

    def crear_logo_pdf():
        """Dibuja un logo simple +F para usar en el encabezado del PDF."""
        logo = Drawing(78, 52)
        azul_logo = colors.Color(0.145, 0.31, 0.58)
        verde_logo = colors.Color(0.071, 0.62, 0.267)

        # Símbolo +
        logo.add(Rect(0, 20, 26, 8, fillColor=azul_logo, strokeColor=azul_logo))
        logo.add(Rect(18, 0, 8, 44, fillColor=azul_logo, strokeColor=azul_logo))

        # Letra F
        logo.add(Rect(38, 0, 8, 44, fillColor=verde_logo, strokeColor=verde_logo))
        logo.add(Rect(46, 36, 30, 8, fillColor=verde_logo, strokeColor=verde_logo))
        logo.add(Rect(46, 20, 22, 8, fillColor=verde_logo, strokeColor=verde_logo))

        return logo

    # Obtener datos del franquiciatario
    datos_f = st.session_state.get('datos_franquicia', {})
    modelo_pdf = modelo.replace("🏪 ", "").replace("🩺 ", "").replace("🛒 ", "")
    
    # Buffer para el PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], 
                                fontSize=26, spaceAfter=20, textColor=colors.Color(0, 0.239, 0.478))
    
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], 
                                  fontSize=16, spaceAfter=12, textColor=colors.Color(0, 0.651, 0.318))
    
    subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Normal'], 
                                   fontSize=12, spaceAfter=8, textColor=colors.Color(0, 0.651, 0.318))
    table_header_light_style = ParagraphStyle(
        'TableHeaderLight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.5,
        leading=7.5,
        alignment=1,
        textColor=colors.black,
    )
    table_header_dark_style = ParagraphStyle(
        'TableHeaderDark',
        parent=table_header_light_style,
        textColor=colors.whitesmoke,
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=7,
        leading=8,
        alignment=1,
        wordWrap='CJK',
    )
    table_cell_left_style = ParagraphStyle(
        'TableCellLeft',
        parent=table_cell_style,
        alignment=0,
    )

    def wrap_pdf_table(data, header_style=table_header_light_style, cell_style=table_cell_style, left_first_col=False):
        wrapped = []
        for row_idx, row in enumerate(data):
            wrapped_row = []
            for col_idx, value in enumerate(row):
                style = header_style if row_idx == 0 else cell_style
                if left_first_col and row_idx > 0 and col_idx == 0:
                    style = table_cell_left_style
                wrapped_row.append(Paragraph(escape(str(value)), style))
            wrapped.append(wrapped_row)
        return wrapped
	    
    # Contenido del PDF
    story = []

    # Encabezado profesional con logo
    header_table = Table(
        [[
            Paragraph("<b>+FARMACIA LÍBANO</b>", title_style),
            crear_logo_pdf()
        ]],
        colWidths=[5.25 * inch, 0.9 * inch]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Paragraph("OPORTUNIDAD DE INVERSIÓN - ANÁLISIS FINANCIERO", styles['Heading2']))
    story.append(Paragraph("<i>Siempre al cuidado de tu salud</i>", subtitle_style))
    story.append(Spacer(1, 15))
    
    # Información del franquiciatario
    franquicia_info = f"""
    <b>Preparado para:</b> {datos_f.get('nombre', 'N/A')}<br/>
    <b>Ubicación:</b> {datos_f.get('ubicacion', 'N/A')}<br/>
    <b>Propósito:</b> {datos_f.get('proposito', 'N/A')}<br/>
    """
    story.append(Paragraph(franquicia_info, styles['Normal']))
    story.append(Spacer(1, 10))
    
    # Información del modelo
    conversion_rate = conversion * 100
    modelo_info = f"""
    <b>Modelo de Franquicia:</b> {modelo_pdf}<br/>
    <b>Escenario Analizado:</b> {escenario}<br/>
    <b>Inversión base:</b> ${inversion:,}<br/>
    <b>Colchón operativo:</b> ${colchon_operativo:,}<br/>
    <b>Inversión total a recuperar:</b> ${inversion_total:,}<br/>
    <b>Fecha de Análisis:</b> {pd.Timestamp.now().strftime('%d/%m/%Y')}<br/>
    """
    story.append(Paragraph(modelo_info, styles['Normal']))
    story.append(Spacer(1, 15))

    # Guía para el cliente
    story.append(Paragraph("Cómo leer este reporte", heading_style))
    nivel_trafico = (
        "alto" if flujo_peatonal_dia >= 1200 else
        "medio" if flujo_peatonal_dia >= 700 else
        "moderado"
    )
    lectura_arranque = (
        "prudente" if arranque_inicial_efectivo <= 0.55 else
        "balanceado" if arranque_inicial_efectivo <= 0.68 else
        "fuerte"
    )
    lectura_rentabilidad = (
        "una recuperación rápida" if np.isfinite(meses_recuperacion) and meses_recuperacion <= 24 else
        "una recuperación gradual" if np.isfinite(meses_recuperacion) and meses_recuperacion <= 36 else
        "una recuperación lenta o todavía no visible en el primer horizonte"
    )
    lectura_desc = f"""
    Este documento fue preparado para ayudarte a evaluar de forma clara el potencial financiero de la sucursal propuesta. 
    La corrida traduce tus supuestos de <b>inversión inicial</b>, <b>tráfico</b>, <b>horario de operación</b>, 
    <b>ticket promedio</b> y <b>estructura de costos</b> en una proyección de ventas, utilidad y recuperación de inversión.<br/><br/>

    <b>Con los datos capturados en esta corrida:</b><br/>
    • Se está analizando una sucursal con <b>{horas} horas abiertas por día</b><br/>
    • El flujo estimado es <b>{nivel_trafico}</b>, con aproximadamente <b>{flujo_peatonal_dia:,.0f} peatones</b> y <b>{flujo_vehicular_dia:,.0f} vehículos</b> al día<br/>
    • La conversión estimada es de <b>{conversion_rate:.1f}% peatonal</b> y <b>{captacion_rate:.1f}% vehicular</b><br/>
    • La inversión incorpora un <b>colchón operativo de ${colchon_operativo:,.0f}</b> para mantener una lectura comercial conservadora<br/>
    • El arranque proyectado es <b>{lectura_arranque}</b>, y el análisis sugiere <b>{lectura_rentabilidad}</b><br/><br/>
    
    <b>Qué debes revisar como cliente:</b><br/>
    • <b>Mes 1:</b> muestra el arranque realista, incluyendo el periodo de adaptación y gastos de apertura<br/>
    • <b>Mes estabilizado:</b> muestra cómo se comportaría la sucursal una vez que opere con mayor normalidad<br/>
    • <b>Primer año:</b> resume el impacto total del arranque, el crecimiento y la rentabilidad acumulada<br/>
    • <b>Punto de equilibrio:</b> indica el nivel mínimo de venta mensual necesario para cubrir costos fijos y se acompaña del objetivo de equilibrio operativo en el <b>mes {mes_equilibrio_objetivo}</b><br/><br/>
    
    La intención es que puedas usar este reporte para tomar una decisión más informada, comparar escenarios y detectar 
    qué variables tienen mayor impacto en la rentabilidad del proyecto. Si ajustas tráfico, horario, ticket o inversión, 
    el análisis cambia y el reporte se adapta automáticamente para reflejar ese nuevo escenario.
    """
    story.append(Paragraph(lectura_desc, styles['Normal']))
    story.append(Spacer(1, 18))

    # Resumen sencillo para cliente no técnico
    story.append(Paragraph("Lectura simple del escenario", heading_style))
    resumen_simple = f"""
    <b>En palabras simples:</b><br/>
    Hoy este análisis estima que con una inversión total de <b>${inversion_total:,.0f}</b>, una operación de <b>{horas} horas diarias</b> 
    y un ticket promedio de <b>${ticket:,.0f}</b>, la sucursal puede vender alrededor de <b>${ventas_mes_1:,.0f}</b> en su primer mes 
    y acercarse a <b>${ventas_totales:,.0f}</b> mensuales cuando ya opere de forma estabilizada.<br/><br/>
    
    Esto significa que el negocio no se evalúa solo por “si gana o pierde”, sino por <b>qué tan rápido arranca</b>, 
    <b>cuánto tarda en madurar</b> y <b>cuánto tarda en recuperar la inversión</b>. Por eso este reporte separa claramente 
    el arranque, el punto estable y el resultado del primer año.
    """
    story.append(Paragraph(resumen_simple, styles['Normal']))
    story.append(Spacer(1, 18))
    
    # Explicación del escenario (VENDEDOR)
    story.append(Paragraph("Análisis del Escenario", heading_style))
    
    if escenario == "Conservador":
        escenario_desc = f"""
        <b>Escenario Conservador ({conversion_rate:.1f}% de conversión peatonal):</b><br/>
        Este análisis considera condiciones iniciales prudentes, ideal para inversores que prefieren proyecciones realistas. 
        De cada 100 personas que pasan por tu farmacia, {int(conversion_rate)} realizarán compras. 
        <b>Es el escenario perfecto para comenzar con confianza,</b> ya que cualquier mejora en ubicación o servicio 
        incrementará significativamente estos resultados base.
        """
    elif escenario == "Medio":
        escenario_desc = f"""
        <b>Escenario Medio ({conversion_rate:.1f}% de conversión peatonal):</b><br/>
        Representa las condiciones más probables de operación con ubicación decente y servicio establecido. 
        De cada 100 visitantes, {int(conversion_rate)} se convierten en clientes. 
        <b>Este es nuestro escenario recomendado</b> basado en el desempeño histórico de franquiciados exitosos 
        en ubicaciones similares.
        """
    else:  # Alto
        escenario_desc = f"""
        <b>Escenario Alto ({conversion_rate:.1f}% de conversión peatonal):</b><br/>
        Proyecta resultados en ubicaciones premium con excelente flujo peatonal y mínima competencia. 
        {int(conversion_rate)} de cada 100 personas se convierten en clientes. 
        <b>Representa el potencial máximo alcanzable</b> con ubicación estratégica y operación optimizada.
        """
    
    story.append(Paragraph(escenario_desc, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Potencial del modelo (VENDEDOR)
    story.append(Paragraph("Potencial del Modelo", heading_style))
    
    potencial_desc = f"""
    <b>El modelo {modelo_pdf} está diseñado para maximizar oportunidades:</b><br/>
    """
    
    if modelo == "🏪 Mini":
        potencial_desc += """
        • <b>Inversión accesible</b> con rápido retorno<br/>
        • <b>Operación simple</b> - ideal para emprendedores nuevos<br/>
        • <b>Mercado amplio</b> - todos necesitan medicamentos<br/>
        • <b>Márgenes atractivos</b> en medicamentos genéricos (35-45%)<br/>
        """
    elif modelo == "🩺 Consultorio":
        potencial_desc += """
        • <b>Doble flujo de ingresos:</b> farmacia + consultas médicas<br/>
        • <b>Sinergia perfecta</b> - pacientes surten recetas inmediatamente<br/>
        • <b>Fidelización alta</b> - relación médico-paciente duradera<br/>
        • <b>Márgenes superiores</b> en recetas especializadas (38-42%)<br/>
        """
    else:  # Super
        potencial_desc += """
        • <b>Modelo integral</b> - farmacia, consultorio y conveniencia<br/>
        • <b>Máximo tráfico</b> - abarrotes atraen clientes diarios<br/>
        • <b>Venta cruzada</b> - un cliente, múltiples compras<br/>
        • <b>Diversificación</b> - múltiples fuentes de ingreso<br/>
        """
    
    story.append(Paragraph(potencial_desc, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Resumen ejecutivo (MÁS VENDEDOR)
    story.append(Paragraph("Resultados Proyectados", heading_style))
    
    # Tabla de métricas principales (mejorada)
    metricas_data = [
        ['MÉTRICA CLAVE', 'RESULTADO'],
        ['Tickets mensuales estabilizados', f'{clientes_mes_display:,} tickets'],
        ['Inversión total a recuperar', f'${inversion_total:,.0f}'],
        ['Colchón operativo', f'${colchon_operativo:,.0f}'],
        ['Ingresos mes 1', f'${ventas_mes_1:,.0f}'],
        ['Utilidad neta mes 1', f'${utilidad_mes_1:,.0f}'],
        ['Ingresos estabilizados', f'${ventas_totales:,.0f}'],
        ['Utilidad neta estabilizada', f'${utilidad_neta:,.0f}'],
        ['Margen de utilidad', f'{margen_neto*100:.1f}%'],
        ['ROI primer año', f'{roi_anual*100:.1f}%'],
        ['Período de recuperación', retorno_reporte],
        ['Equilibrio objetivo', f'Mes {mes_equilibrio_objetivo}'],
        ['Techo operativo mensual', f'${ventas_tope:,.0f} en ventas y ${utilidad_tope:,.0f} de utilidad'],
        ['Mes de estabilización', f'Mes {mes_tope_operativo or MESES_PROYECCION}'],
        ['Punto de equilibrio', f'${ventas_be:,.0f}/mes'],
        ['% de equilibrio', f'{porcentaje_equilibrio:.1f}% de la venta estable'],
        ['Ingresos primer año', f'${ventas_anual:,.0f}'],
        ['Utilidad primer año', f'${util_anual:,.0f}'],
    ]
    
    metricas_table = Table(
        wrap_pdf_table(metricas_data, header_style=table_header_dark_style, left_first_col=True),
        colWidths=[3.35*inch, 2.05*inch],
    )
    metricas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.651, 0.318)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.98, 0.95)),
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(metricas_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Cómo se construyen las ventas", heading_style))
    story.append(Paragraph(
        "Este desglose muestra la conversión operativa desde flujo, tickets y ticket promedio hasta ventas y utilidad mensual.",
        styles['Normal']
    ))
    story.append(Spacer(1, 8))

    productos_base_data = [
        ['GASTOS FIJOS', 'PEAT./H', 'VEH./H', 'HORAS/DÍA', 'DÍAS/MES', 'FLUJO/MES', '% CONV.', 'CLIENTES/MES'],
        [
            fmt_dinero(gastos_fijos),
            f'{flujo:,}',
            f'{flujo_vehicular:,}',
            f'{horas:,}',
            f'{dias:,}',
            f'{round(flujo_peatonal_mes + flujo_vehicular_mes):,}',
            f'{conversion_rate:.1f}%',
            f'{clientes_mes_display:,}',
        ],
    ]
    productos_base_table = Table(
        wrap_pdf_table(productos_base_data),
        colWidths=[0.72*inch, 0.55*inch, 0.55*inch, 0.62*inch, 0.58*inch, 0.78*inch, 0.58*inch, 0.72*inch],
    )
    productos_base_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.44, 0.62, 0.65)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.94, 0.97, 0.97)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(productos_base_table)
    story.append(Spacer(1, 6))

    productos_resultado_data = [
        ['TICKET', 'VENTAS PRODUCTOS', 'COSTO RESURTIDO', 'GASTO VARIABLE', 'UTILIDAD PRODUCTOS', 'CAPITAL TRABAJO'],
        [
            fmt_dinero(ticket),
            fmt_dinero(ventas_farmacia),
            fmt_dinero(costo_resurtido_farmacia),
            fmt_dinero(gasto_variable_farmacia),
            fmt_dinero(utilidad_productos_display),
            fmt_dinero(capital_trabajo_productos),
        ],
    ]
    productos_resultado_table = Table(
        wrap_pdf_table(productos_resultado_data),
        colWidths=[0.7*inch, 1.05*inch, 1.02*inch, 0.95*inch, 1.05*inch, 1.0*inch],
    )
    productos_resultado_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.44, 0.62, 0.65)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.94, 0.97, 0.97)),
        ('BACKGROUND', (-1, 1), (-1, 1), colors.Color(0.88, 0.94, 0.86)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(productos_resultado_table)
    story.append(Spacer(1, 10))

    if m["consultorio"]:
        consultas_data = [
            ['CLIENTES/MES', '% CONSULTAS', 'CONSULTAS/MES', 'PRECIO CONSULTA', 'VENTAS CONSULTAS', '% RECETAS', 'RECETAS/MES', 'VENTAS RECETAS'],
            [
                f'{clientes_mes_display:,}',
                f'{porcentaje_consultas:.1f}%',
                f'{consultas_mes:,.0f}',
                fmt_dinero(ingreso_consulta),
                fmt_dinero(ingresos_consulta),
                f'{surten*100:.1f}%',
                f'{recetas_mes:,.0f}',
                fmt_dinero(ventas_recetas),
            ],
        ]
        consultas_table = Table(
            wrap_pdf_table(consultas_data),
            colWidths=[0.7*inch, 0.65*inch, 0.75*inch, 0.78*inch, 0.88*inch, 0.62*inch, 0.7*inch, 0.85*inch],
        )
        consultas_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.44, 0.62, 0.65)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.94, 0.97, 0.97)),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(consultas_table)
        story.append(Spacer(1, 6))

        consultas_resultado_data = [
            ['RESURTIDO RECETAS', 'UTILIDAD CONSULTAS Y RECETAS', 'CAPITAL TRABAJO'],
            [
                fmt_dinero(costo_resurtido_recetas),
                fmt_dinero(utilidad_consultas_recetas_display),
                fmt_dinero(capital_trabajo_consultas_recetas),
            ],
        ]
        consultas_resultado_table = Table(
            wrap_pdf_table(consultas_resultado_data),
            colWidths=[1.35*inch, 1.8*inch, 1.15*inch],
        )
        consultas_resultado_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.44, 0.62, 0.65)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.94, 0.97, 0.97)),
            ('BACKGROUND', (1, 1), (1, 1), colors.Color(0.72, 0.88, 0.65)),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(consultas_resultado_table)
        story.append(Spacer(1, 10))

    resumen_operativo_data = [['LÍNEA', 'VENTAS/MES', 'UTILIDAD/MES', 'CAPITAL TRABAJO']]
    for fila in resumen_operativo_rows:
        resumen_operativo_data.append([
            fila['Línea'],
            fila['Ventas/mes'],
            fila['Utilidad/mes'],
            fila['Capital trabajo'],
        ])
    resumen_operativo_table = Table(
        wrap_pdf_table(resumen_operativo_data, left_first_col=True),
        colWidths=[1.75*inch, 1.15*inch, 1.15*inch, 1.15*inch],
    )
    resumen_operativo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.44, 0.62, 0.65)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.94, 0.97, 0.97)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.88, 0.94, 0.86)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(resumen_operativo_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Los 3 escenarios considerados", heading_style))
    story.append(Paragraph(
        f"Se comparan los escenarios Conservador, Medio y Alto. "
        f"El escenario seleccionado para esta revisión es <b>{escenario}</b>.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    escenarios_data = [[
        'ESCENARIO',
        'SEL.',
        'PERFIL',
        'EQUILIBRIO',
        'META RETORNO',
        'LECTURA RETORNO',
        'ROI AÑO 1',
        'ESTATUS',
    ]]
    for fila in resumen_escenarios:
        escenarios_data.append([
            fila["Escenario"],
            fila["Seleccionado"],
            fila["Perfil"],
            fila["Equilibrio meta"],
            fila["Meta retorno"],
            fila["Lectura retorno"],
            fila["ROI año 1"],
            fila["Estatus"],
        ])

    escenarios_table = Table(
        wrap_pdf_table(escenarios_data, header_style=table_header_dark_style),
        colWidths=[0.78*inch, 0.34*inch, 0.74*inch, 0.64*inch, 0.82*inch, 0.84*inch, 0.62*inch, 0.86*inch],
    )
    escenarios_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.239, 0.478)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.98, 0.98, 1.0)),
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ])
    for idx, fila in enumerate(resumen_escenarios, start=1):
        if fila["Seleccionado"] == "Sí":
            escenarios_style.add('BACKGROUND', (0, idx), (-1, idx), colors.Color(0.90, 0.97, 0.90))
            escenarios_style.add('FONTNAME', (0, idx), (-1, idx), 'Helvetica-Bold')
    escenarios_table.setStyle(escenarios_style)
    story.append(escenarios_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        f"La proyección ya incorpora una maduración con techo operativo. "
        f"Hacia el mes {mes_tope_operativo or MESES_PROYECCION}, la unidad alcanza su techo y a partir del siguiente mes se estabiliza alrededor de "
        f"{fmt_dinero(ventas_tope)} en ventas mensuales.",
        styles['Normal']
    ))
    story.append(Spacer(1, 16))

    if not cumple_estandar_comercial and meta_comercial["alcanzable"]:
        story.append(Paragraph("Ruta para entrar al estándar", heading_style))
        ruta_estandar_html = f"""
        <b>Meta de ventas:</b> {meta_ventas_texto} al mes, equivalente a subir {faltante_ventas_texto} frente al nivel actual.<br/>
        <b>Meta de utilidad:</b> {meta_utilidad_texto} al mes como run-rate estabilizado.<br/>
        <b>Meta de tickets:</b> {meta_tickets_texto} al mes con ticket blended de referencia de {ticket_blended_meta_texto}.<br/>
        <b>Ruta por inversión:</b> bajar el total a recuperar hacia {meta_inversion_texto}, es decir recortar cerca de {recorte_inversion_texto}.<br/>
        <b>Ruta por gastos fijos:</b> bajar la estructura hacia {gasto_fijo_meta_texto} al mes, equivalente a recortar aproximadamente {reduccion_gf_texto}.
        """
        story.append(Paragraph(ruta_estandar_html, styles['Normal']))
        story.append(Spacer(1, 16))
    
    # Estructura de ingresos (MÁS VISUAL)
    story.append(Paragraph("Estructura de Ingresos Mensuales Estabilizados", heading_style))
    
    ventas_data = [['LÍNEA DE NEGOCIO', 'INGRESOS', 'PARTICIPACIÓN']]
    ventas_data.append(['Farmacia', f'${ventas_farmacia:,.0f}', f'{(ventas_farmacia/ventas_totales*100):.1f}%'])
    
    if m["consultorio"]:
        ventas_data.append(['Recetas médicas', f'${ventas_recetas:,.0f}', f'{(ventas_recetas/ventas_totales*100):.1f}%'])
        ventas_data.append(['Consultas', f'${ingresos_consulta:,.0f}', f'{(ingresos_consulta/ventas_totales*100):.1f}%'])
    
    if m["abarrotes"]:
        ventas_data.append(['Conveniencia', f'${ventas_abarrotes:,.0f}', f'{(ventas_abarrotes/ventas_totales*100):.1f}%'])
    
    ventas_data.append(['TOTAL MENSUAL ESTABILIZADO', f'${ventas_totales:,.0f}', '100.0%'])
    
    ventas_table = Table(
        wrap_pdf_table(ventas_data, header_style=table_header_dark_style, left_first_col=True),
        colWidths=[2.6*inch, 1.45*inch, 1.25*inch],
    )
    ventas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.239, 0.478)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.Color(0.98, 0.98, 1.0)),
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(ventas_table)
    story.append(Spacer(1, 20))
    
    # Evolución del negocio (TRIMESTRAL - más atractivo)
    story.append(Paragraph("Evolución Trimestral del Primer Año", heading_style))
    
    proy_data = [['PERÍODO', 'INGRESOS', 'UTILIDAD NETA', 'MARGEN']]
    trimestres = [
        ("Mes 1-3", 0, 2),
        ("Mes 4-6", 3, 5), 
        ("Mes 7-9", 6, 8),
        ("Mes 10-12", 9, 11)
    ]
    
    for nombre, inicio, fin in trimestres:
        ventas_trim = sum([int(proyeccion[i]['Ventas'].replace('$', '').replace(',', '')) for i in range(inicio, fin+1)])
        util_trim = sum([int(proyeccion[i]['Util. Neta'].replace('$', '').replace(',', '')) for i in range(inicio, fin+1)])
        margen_trim = util_trim / ventas_trim * 100 if ventas_trim > 0 else 0
        
        proy_data.append([
            nombre,
            f'${ventas_trim:,}',
            f'${util_trim:,}',
            f'{margen_trim:.1f}%'
        ])
    
    proy_table = Table(
        wrap_pdf_table(proy_data, header_style=table_header_dark_style),
        colWidths=[1.1*inch, 1.35*inch, 1.35*inch, 0.9*inch],
    )
    proy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.651, 0.318)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.98, 0.95)),
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),
    ]))
    
    story.append(proy_table)
    story.append(Spacer(1, 20))
    
    # Evaluación de la oportunidad (MUY VENDEDOR)
    story.append(Paragraph("Evaluación de la Oportunidad", heading_style))
    
    if cumple_estandar_comercial:
        eval_color = colors.Color(0, 0.5, 0)  # Verde
        conclusion = f"""
        <b>OPORTUNIDAD EXCELENTE</b><br/><br/>
        
        <b>Arranque Controlado:</b> El proyecto soporta el periodo inicial y cierra con utilidad positiva en el primer año<br/>
        <b>Recuperación Comercial:</b> {retorno_reporte_detalle}<br/>
        <b>ROI Atractivo:</b> {roi_anual*100:.1f}% en el primer año, ya considerando rampa de arranque<br/>
        <b>Mercado Estable:</b> Sector salud con demanda constante y creciente<br/><br/>
        
        <b>RECOMENDACIÓN:</b> Proceder con la inversión. Los números demuestran 
        una oportunidad sólida con riesgo controlado y potencial de crecimiento.
        """
    elif meta_comercial["alcanzable"]:
        eval_color = colors.Color(0.7, 0.7, 0)  # Amarillo
        conclusion = f"""
        <b>OPORTUNIDAD VIABLE CON CONSIDERACIONES</b><br/><br/>
        
        <b>Meta Comercial:</b> {retorno_reporte_detalle}<br/>
        <b>Ventas Objetivo:</b> Llevar la venta estable hacia {meta_ventas_texto} mensuales<br/>
        <b>Potencial de Mejora:</b> Optimizaciones operativas pueden llevar la unidad de regreso al estándar objetivo<br/><br/>
        
        <b>RECOMENDACIÓN:</b> Evaluar mejoras en ubicación o eficiencias operativas 
        para acelerar la recuperación. Base sólida con oportunidades de optimización.
        """
    else:
        eval_color = colors.Color(0.8, 0.2, 0)  # Rojo suave (no muy negativo)
        conclusion = f"""
        <b>OPORTUNIDAD REQUIERE AJUSTES</b><br/><br/>
        
        <b>Análisis Detallado:</b> Los números actuales sugieren optimizar parámetros<br/>
        <b>Potencial Latente:</b> Ajustes en location/operación pueden mejorar resultados<br/>
        <b>Soporte Líbano:</b> Nuestro equipo puede ayudar a optimizar la propuesta<br/><br/>
        
        <b>RECOMENDACIÓN:</b> Revisar ubicación propuesta y explorar alternativas. 
        El modelo es probadamente exitoso con los parámetros correctos.
        """
    
    conclusion_style = ParagraphStyle('Conclusion', parent=styles['Normal'], 
                                     fontSize=11, textColor=eval_color)
    story.append(Paragraph(conclusion, conclusion_style))
    story.append(Spacer(1, 20))
    
    # Próximos pasos (CALL TO ACTION)
    story.append(Paragraph("Próximos Pasos Recomendados", heading_style))
    
    next_steps = """
    <b>1. VALIDACIÓN DE UBICACIÓN:</b> Confirmar flujo peatonal y análisis de competencia<br/>
    <b>2. FINANCIAMIENTO:</b> Estructurar inversión inicial y capital de trabajo<br/>
    <b>3. CAPACITACIÓN:</b> Programa integral de entrenamiento Farmacia Líbano<br/>
    <b>4. PUESTA EN MARCHA:</b> Plan de lanzamiento y marketing inicial<br/>
    <b>5. SEGUIMIENTO:</b> Monitoreo mensual de KPIs y optimización continua<br/>
    """
    
    story.append(Paragraph(next_steps, styles['Normal']))

    # Disclaimer profesional
    story.append(Spacer(1, 18))
    story.append(Paragraph("Consideraciones Importantes", heading_style))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.Color(0.35, 0.35, 0.35)
    )
    disclaimer_text = """
    <b>Disclaimer:</b> Esta corrida financiera es ilustrativa y fue elaborada como una herramienta de análisis comercial 
    para apoyar tu evaluación. Las proyecciones presentadas no constituyen una garantía de desempeño, rentabilidad, 
    recuperación de inversión ni flujo futuro. Los resultados reales pueden variar de forma material según factores como 
    ubicación, competencia, ejecución operativa, horarios de apertura, mezcla de productos, nivel de servicio, estacionalidad, 
    disponibilidad de personal, condiciones de mercado y cambios regulatorios. Este reporte debe utilizarse como referencia 
    para analizar escenarios y no sustituye una validación en campo, un estudio de mercado, una revisión fiscal, legal u 
    operativa, ni una asesoría financiera independiente antes de tomar una decisión de inversión.
    """
    story.append(Paragraph(disclaimer_text, disclaimer_style))
    
    # Pie de página profesional
    story.append(Spacer(1, 25))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], 
                                 fontSize=9, textColor=colors.gray, alignment=1)
    story.append(Paragraph("Farmacia Líbano - Análisis Financiero Confidencial", footer_style))
    story.append(Paragraph(f"Generado el {pd.Timestamp.now().strftime('%d de %B, %Y')}", footer_style))
    
    # Construir PDF
    doc.build(story)
    
    # Retornar el PDF
    buffer.seek(0)
    return buffer.getvalue()

# Botón de descarga del reporte
st.markdown("---")
st.markdown("### 📄 Descargar Reporte")

col_pdf1, col_pdf2 = st.columns([1, 3])
with col_pdf1:
    if st.button("📥 Generar PDF", type="primary", disabled=not cumple_estandar_comercial):
        with st.spinner("Generando reporte PDF..."):
            pdf_bytes = generar_reporte_pdf()
            st.download_button(
                label="📄 Descargar Reporte PDF", 
                data=pdf_bytes,
                file_name=f"corrida_financiera_{modelo.replace(' ', '_').lower()}_{escenario.lower()}.pdf",
                mime="application/pdf"
            )
with col_pdf2:
    if cumple_estandar_comercial:
        st.caption("Genera un reporte ejecutivo profesional para revisar esta oportunidad con el franquiciatario, socios o para análisis interno.")
    else:
        st.warning(
            "El PDF se habilita solo cuando la corrida entra en el estándar comercial "
            f"del escenario: retorno <= {meta_escenario_actual['payback_max']:.0f} meses "
            f"y equilibrio <= mes {meta_escenario_actual['equilibrio_mes']}."
        )

# Recomendaciones útiles (tono constructivo)
if np.isfinite(meses_recuperacion) and meses_recuperacion > 24:
    st.info("💡 **Oportunidad de optimización:** Con mejoras en ubicación o eficiencias operativas, puedes acelerar la recuperación de tu inversión.")
if clientes_mes < clientes_be:
    st.warning(f"📊 **Análisis de tráfico:** Para alcanzar el punto de equilibrio necesitas {clientes_be_display:,} clientes vs {clientes_mes_display:,} proyectados. Considera estrategias de marketing local.")
if margen_neto < 0.05 and utilidad_neta > 0:
    st.info("🎯 **Potencial de mejora:** Los márgenes pueden optimizarse mejorando la mezcla de productos o negociando mejores condiciones con proveedores.")
