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
    """Registra el acceso - local en archivo, producción en session"""
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    registro = f"{fecha_hora} | {codigo} | {nombre}"
    
    # Intentar guardar en archivo local
    try:
        archivo_log = os.path.join(os.path.dirname(__file__), 'accesos.log')
        with open(archivo_log, 'a', encoding='utf-8') as f:
            f.write(registro + "\n")
    except:
        pass
    
    # Guardar en session state para ver en la app
    if 'registro_accesos' not in st.session_state:
        st.session_state['registro_accesos'] = []
    st.session_state['registro_accesos'].append(registro)

def registrar_corrida(datos_franquicia, usuario):
    """Registra cuando se crea una corrida financiera"""
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    registro = f"{fecha_hora} | CORRIDA | {usuario} | {datos_franquicia['nombre']} | {datos_franquicia['ubicacion']} | {datos_franquicia['proposito']}"
    
    # Intentar guardar en archivo local
    try:
        archivo_log = os.path.join(os.path.dirname(__file__), 'accesos.log')
        with open(archivo_log, 'a', encoding='utf-8') as f:
            f.write(registro + "\n")
    except:
        pass
    
    # Guardar en session state
    if 'registro_accesos' not in st.session_state:
        st.session_state['registro_accesos'] = []
    st.session_state['registro_accesos'].append(registro)

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
    <div style="font-size: 14px; color: #666;">
        <strong style="color: #003D7A;">{datos_f['nombre']}</strong> · {datos_f['ubicacion']} · {datos_f['proposito']}
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
    /* Header y títulos */
    .main h1 {{
        color: {AZUL} !important;
    }}
    .main h2, .main h3 {{
        color: {VERDE} !important;
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
    [data-testid="stMetricValue"] {{
        color: {AZUL} !important;
        font-weight: bold;
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
        color: {AZUL};
    }}
    .logo-slogan {{
        font-style: italic;
        color: {AZUL};
        font-size: 14px;
    }}
</style>
""", unsafe_allow_html=True)

# Función para formatear dinero
def fmt_dinero(valor):
    if valor >= 1_000_000:
        return f"${valor:,.0f}"
    return f"${valor:,.0f}"

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
        "Conservador": {"flujo": 30, "conversion": 0.08, "ticket": 75, "cogs": 0.72, "gastos_fijos": 22000, "gastos_var": 0.03, "crec": 0.015},
        "Medio":       {"flujo": 60, "conversion": 0.12, "ticket": 95, "cogs": 0.68, "gastos_fijos": 28000, "gastos_var": 0.05, "crec": 0.03},
        "Alto":        {"flujo": 100, "conversion": 0.16, "ticket": 120, "cogs": 0.65, "gastos_fijos": 35000, "gastos_var": 0.07, "crec": 0.045},
    },
    "🩺 Consultorio": {
        "Conservador": {"flujo": 45, "conversion": 0.09, "ticket": 85, "cogs": 0.70, "gastos_fijos": 35000, "gastos_var": 0.04, "crec": 0.02,
                        "consultas": 8, "surten": 0.60, "ticket_receta": 120, "ingreso_consulta": 40, "cogs_receta": 0.62},
        "Medio":       {"flujo": 80, "conversion": 0.13, "ticket": 110, "cogs": 0.67, "gastos_fijos": 45000, "gastos_var": 0.06, "crec": 0.035,
                        "consultas": 15, "surten": 0.72, "ticket_receta": 180, "ingreso_consulta": 60, "cogs_receta": 0.58},
        "Alto":        {"flujo": 140, "conversion": 0.17, "ticket": 150, "cogs": 0.63, "gastos_fijos": 58000, "gastos_var": 0.08, "crec": 0.05,
                        "consultas": 25, "surten": 0.85, "ticket_receta": 250, "ingreso_consulta": 85, "cogs_receta": 0.55},
    },
    "🛒 Super": {
        "Conservador": {"flujo": 60, "conversion": 0.10, "ticket": 90, "cogs": 0.74, "gastos_fijos": 48000, "gastos_var": 0.04, "crec": 0.025,
                        "consultas": 10, "surten": 0.65, "ticket_receta": 140, "ingreso_consulta": 45, "cogs_receta": 0.62,
                        "abarrotes_pct": 0.15, "cogs_abarrotes": 0.90},
        "Medio":       {"flujo": 110, "conversion": 0.14, "ticket": 120, "cogs": 0.69, "gastos_fijos": 62000, "gastos_var": 0.06, "crec": 0.04,
                        "consultas": 18, "surten": 0.75, "ticket_receta": 200, "ingreso_consulta": 70, "cogs_receta": 0.58,
                        "abarrotes_pct": 0.22, "cogs_abarrotes": 0.88},
        "Alto":        {"flujo": 180, "conversion": 0.18, "ticket": 165, "cogs": 0.65, "gastos_fijos": 78000, "gastos_var": 0.08, "crec": 0.055,
                        "consultas": 30, "surten": 0.88, "ticket_receta": 280, "ingreso_consulta": 100, "cogs_receta": 0.55,
                        "abarrotes_pct": 0.32, "cogs_abarrotes": 0.85},
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
        value=st.session_state["inversion_simple"],
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
conversion_default = {"Conservador": 3.0, "Medio": 3.0, "Alto": 3.0}
captacion_vehicular_default = {"Conservador": 0.3, "Medio": 0.5, "Alto": 0.8}
gastos_variables_default = {"🏪 Mini": 3.0, "🩺 Consultorio": 3.0, "🛒 Super": 3.0}
surten_default = {"Conservador": 50.0, "Medio": 50.0, "Alto": 50.0}

with st.sidebar.expander("👥 Tráfico peatonal y vehicular", expanded=True):
    st.caption("Usa una hora típica y define tu horario real de operación.")
    flujo = st.number_input(
        "Peatones por hora",
        min_value=20,
        max_value=200,
        value=min(max(p["flujo"], 20), 200),
        step=5,
        help="Personas caminando frente al local en una hora normal"
    )
    flujo_vehicular = st.number_input(
        "Vehículos por hora",
        min_value=0,
        max_value=300,
        value=min(max(30, int(p["flujo"] * 1.5)), 300),
        step=10,
        help="Autos o motos que pasan frente al local"
    )
    conversion = st.number_input(
        "Conversión peatonal (%)",
        min_value=0.1,
        value=float(conversion_default[escenario]),
        step=0.5,
        help="Porcentaje de peatones que entra y compra"
    ) / 100
    captacion_vehicular = st.number_input(
        "Captación vehicular (%)",
        min_value=0.0,
        value=float(captacion_vehicular_default[escenario]),
        step=0.1,
        help="Porcentaje de vehículos que sí se detienen a comprar"
    ) / 100
    horas = st.number_input(
        "Horas abiertas por día",
        min_value=8,
        max_value=16,
        value=12,
        step=1,
        help="Horario diario de operación de la sucursal"
    )
    dias = 30

    flujo_peatonal_dia = flujo * horas
    flujo_vehicular_dia = flujo_vehicular * horas
    clientes_vehiculares_dia = flujo_vehicular_dia * captacion_vehicular
    st.info(
        f"📊 Tráfico diario estimado: **{flujo_peatonal_dia:,} peatones** y "
        f"**{flujo_vehicular_dia:,} vehículos**. Con tu captación, "
        f"eso agrega **~{clientes_vehiculares_dia:,.0f} tickets/día** desde autos."
    )

with st.sidebar.expander("🧾 Gasto variable", expanded=False):
    st.caption("Es el porcentaje de ventas que se te va en terminal, mermas, bolsas, promociones y operación variable.")
    if st.session_state.get("modelo_gasto_variable_simple") != modelo:
        st.session_state["gasto_variable_simple"] = float(gastos_variables_default[modelo])
        st.session_state["modelo_gasto_variable_simple"] = modelo

    gasto_variable_pct = st.number_input(
        "Gasto variable sobre ventas (%)",
        min_value=0.0,
        value=st.session_state["gasto_variable_simple"],
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
        min_value=50,
        max_value=220,
        value=min(max(p["ticket"], 50), 220),
        step=5,
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
            value=min(max(p.get("consultas", 0), 0), 30),
            step=1,
            help="¿Cuántas consultas médicas esperas al día?"
        )
        ingreso_consulta = st.number_input(
            "Cobro por consulta ($)", 
            min_value=0,
            max_value=120,
            value=min(max(p.get("ingreso_consulta", 40), 0), 120),
            step=5,
            help="¿Cuánto cobras por cada consulta?"
        )
        ticket_receta = st.number_input(
            "Compra promedio con receta ($)", 
            min_value=80,
            max_value=320,
            value=min(max(p.get("ticket_receta", 120), 80), 320),
            step=10,
            help="Los pacientes con receta gastan más"
        )
        surten = st.number_input(
            "Pacientes que surten en tu farmacia (%)",
            min_value=0.0,
            value=float(surten_default[escenario]),
            step=5.0,
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
    st.caption("Añade o modifica gastos fijos mensuales")
    
    # Presets de gastos fijos por modelo
    gastos_presets = {
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
    
    gf_default = gastos_presets[modelo]
    
    # Inicializar estado
    if "gastos_fijos_items" not in st.session_state or st.session_state.get("modelo_gf_anterior") != modelo:
        st.session_state.gastos_fijos_items = gf_default.copy()
        st.session_state.modelo_gf_anterior = modelo
    
    # Mostrar items de gastos
    gastos_fijos_total = 0
    items_gf = list(st.session_state.gastos_fijos_items.keys())
    
    for item in items_gf:
        col1, col2 = st.columns([3, 1])
        with col1:
            nuevo_valor = st.number_input(
                item,
                min_value=0,
                value=st.session_state.gastos_fijos_items[item],
                step=100,
                key=f"gf_{item}"
            )
            st.session_state.gastos_fijos_items[item] = nuevo_valor
        with col2:
            if st.button("🗑️", key=f"del_gf_{item}"):
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
    arranque_opcion = st.selectbox(
        "Fuerza del arranque",
        ["Normal", "Lento", "Fuerte"],
        index=0,
        help="Qué tan cerca arranca el mes 1 del nivel estabilizado"
    )
    arranque_inicial = {"Lento": 0.45, "Normal": 0.55, "Fuerte": 0.70}[arranque_opcion]
    meses_rampa = st.selectbox(
        "Meses para estabilizar la sucursal",
        [3, 4, 5, 6],
        index=1,
        help="Meses que tardas en llegar al nivel operativo normal"
    )
    crec_opcion = st.selectbox(
        "Crecimiento mensual una vez estabilizado",
        ["🐢 Conservador (1%/mes)", "🚶 Moderado (3%/mes)", "🚀 Agresivo (5%/mes)"],
        index=1
    )
    crec = {"🐢 Conservador (1%/mes)": 0.01, "🚶 Moderado (3%/mes)": 0.03, "🚀 Agresivo (5%/mes)": 0.05}[crec_opcion]
    gasto_lanzamiento = st.number_input(
        "Gasto extra de apertura por mes (meses 1-3)",
        min_value=0,
        max_value=40000,
        value={"🏪 Mini": 12000, "🩺 Consultorio": 18000, "🛒 Super": 25000}[modelo],
        step=1000,
        help="Publicidad de apertura, promociones, contratación y ajustes iniciales"
    )

    st.info(
        f"📈 Tu mes 1 arranca al {arranque_inicial*100:.0f}% del nivel estabilizado. "
        f"Después del mes {meses_rampa}, el negocio crece {crec*100:.0f}% mensual."
    )

# Vector de estacionalidad fijo
est_vector = np.ones(12)

# ═══════════════════════════════════════════════════════════════════════════════
# CÁLCULOS - MES ESTABILIZADO
# ═══════════════════════════════════════════════════════════════════════════════
flujo_peatonal_mes = flujo * horas * dias
flujo_vehicular_mes = flujo_vehicular * horas * dias
clientes_peatonales_mes = int(flujo_peatonal_mes * conversion)
clientes_vehiculares_mes = int(flujo_vehicular_mes * captacion_vehicular)
clientes_mes = clientes_peatonales_mes + clientes_vehiculares_mes

ventas_farmacia = clientes_mes * ticket
consultas_mes = consultas * dias if m["consultorio"] else 0
ventas_recetas = consultas_mes * surten * ticket_receta
ingresos_consulta = consultas_mes * ingreso_consulta
ventas_abarrotes = ventas_farmacia * abarrotes_pct if m["abarrotes"] else 0
ventas_totales = ventas_farmacia + ventas_recetas + ventas_abarrotes + ingresos_consulta

# COGS
cogs_farmacia = ventas_farmacia * cogs
cogs_recetas_t = ventas_recetas * cogs_receta
cogs_abarrotes_t = ventas_abarrotes * cogs_abarrotes
cogs_total = cogs_farmacia + cogs_recetas_t + cogs_abarrotes_t

# Utilidades
utilidad_bruta = ventas_totales - cogs_total
gastos_variables = ventas_totales * gastos_var
utilidad_neta = utilidad_bruta - gastos_fijos - gastos_variables
margen_neto = utilidad_neta / ventas_totales if ventas_totales > 0 else 0

clientes_totales = clientes_mes + (consultas_mes if m["consultorio"] else 0)
ticket_prom = ventas_totales / clientes_totales if clientes_totales > 0 else 0

# Break-even con margen de contribución ponderado real
contribucion = ((ventas_totales - cogs_total - gastos_variables) / ventas_totales) if ventas_totales > 0 else 0
if contribucion > 0 and ticket_prom > 0:
    ventas_be = gastos_fijos / contribucion
    clientes_be = ventas_be / ticket_prom
else:
    ventas_be, clientes_be = float('inf'), float('inf')

rampa = np.linspace(arranque_inicial, 1.0, meses_rampa)

# ═══════════════════════════════════════════════════════════════════════════════
# PROYECCIÓN 12 MESES
# ═══════════════════════════════════════════════════════════════════════════════
proyeccion = []
proyeccion_num = []
utilidades_mensuales = []
caja_acumulada = -inversion
meses_recuperacion = float('inf')

for t in range(12):
    if t < meses_rampa:
        factor = rampa[t]
    else:
        factor = ((1 + crec) ** (t - meses_rampa + 1))
    factor *= est_vector[t]

    vf = ventas_farmacia * factor
    vr = ventas_recetas * factor
    va = ventas_abarrotes * factor
    ic = ingresos_consulta * factor
    vt = vf + vr + va + ic

    ct = vf * cogs + vr * cogs_receta + va * cogs_abarrotes
    ub = vt - ct
    gv = vt * gastos_var
    gasto_extra_t = gasto_lanzamiento if t < 3 else 0
    un = ub - gastos_fijos - gv - gasto_extra_t
    mn = un / vt if vt > 0 else 0

    proyeccion.append({
        "Mes": t + 1,
        "Ventas": f"${round(vt):,}",
        "COGS": f"${round(ct):,}",
        "Util. Bruta": f"${round(ub):,}",
        "Gastos Fijos": f"${round(gastos_fijos):,}",
        "Gastos Var.": f"${round(gv):,}",
        "Apertura": f"${round(gasto_extra_t):,}",
        "Util. Neta": f"${round(un):,}",
        "Margen %": f"{round(mn * 100, 1)}%",
    })

    proyeccion_num.append({
        "Mes": t + 1,
        "Ventas": round(vt),
        "Util. Neta": round(un),
        "Caja Acumulada": round(caja_acumulada + un),
        "Margen %": round(mn * 100, 1),
    })
    utilidades_mensuales.append(un)

    caja_previa = caja_acumulada
    caja_acumulada += un
    if meses_recuperacion == float('inf') and caja_acumulada >= 0 and un > 0:
        faltante = -caja_previa
        meses_recuperacion = t + (faltante / un)

df = pd.DataFrame(proyeccion)
df_num = pd.DataFrame(proyeccion_num)

util_anual = df_num["Util. Neta"].sum()
ventas_anual = df_num["Ventas"].sum()
roi_anual = util_anual / inversion if inversion > 0 else 0

if meses_recuperacion == float('inf'):
    utilidad_run_rate = max(utilidades_mensuales[-1], utilidad_neta, 0)
    remanente = inversion - util_anual
    if utilidad_run_rate > 0 and remanente > 0:
        meses_recuperacion = 12 + (remanente / utilidad_run_rate)

ventas_mes_1 = df_num.iloc[0]["Ventas"]
utilidad_mes_1 = df_num.iloc[0]["Util. Neta"]
ventas_mes_estable = ventas_totales
utilidad_mes_estable = utilidad_neta
meses_recuperacion_fmt = f"{meses_recuperacion:.1f} meses" if np.isfinite(meses_recuperacion) else "N/A"
anios_recuperacion_fmt = f"{meses_recuperacion/12:.1f} años" if np.isfinite(meses_recuperacion) else "N/A"

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
st.markdown(f"**Escenario:** {escenario} | **Inversión:** ${inversion:,}")

# Análisis de flujo y conversión
st.markdown("### 👥 Análisis de Tráfico y Demanda")
peatones_dia = flujo * horas
vehiculos_dia = flujo_vehicular * horas
tickets_vehiculares_dia = vehiculos_dia * captacion_vehicular
conversion_rate = conversion * 100
captacion_rate = captacion_vehicular * 100

col_flujo1, col_flujo2, col_flujo3, col_flujo4 = st.columns(4)
with col_flujo1:
    st.metric("🚶 Peatones/día", f"{peatones_dia:,}")
    st.caption("Flujo peatonal diario")
with col_flujo2:
    st.metric("🚗 Vehículos/día", f"{vehiculos_dia:,}")
    st.caption(f"Captas {captacion_rate:.1f}%")
with col_flujo3:
    st.metric("🛍️ Tickets/mes", f"{clientes_mes:,}")
    st.caption(f"Conversión peatonal de {conversion_rate:.1f}%")
with col_flujo4:
    st.metric("💳 Ticket promedio", f"${ticket_prom:,.0f}")
    st.caption("Ticket blended con servicios")

# Explicación detallada del % de conversión por escenario
st.markdown("### 🎯 ¿Qué significa tu escenario?")

if escenario == "Conservador":
    st.warning(f"""
    **🔴 ESCENARIO CONSERVADOR ({conversion_rate:.1f}% conversión peatonal)**
    
    **¿Qué significa?**
    - De cada 100 personas que pasan frente a tu farmacia, solo **{int(conversion_rate)} entran y compran**
    - Es como estar en una calle con competencia o ser nuevo en la zona
    
    **¿Cuándo pasa esto?**
    - 🏪 Acabas de abrir y la gente no te conoce
    - 🏬 Hay otras farmacias muy cerca (competencia fuerte)
    - 🚶 La ubicación tiene poco flujo peatonal
    - 💸 Los precios son altos comparado con la competencia
    
    **¿Es bueno o malo?**
    - 👍 Es **realista** para empezar - mejor ser precavido
    - 👍 Si los números salen bien aquí, ¡seguro tendrás éxito!
    - ⚠️ Pero necesitas trabajar en atraer más clientes
    """)
elif escenario == "Medio":
    st.info(f"""
    **🟡 ESCENARIO MEDIO ({conversion_rate:.1f}% conversión peatonal)**
    
    **¿Qué significa?**
    - De cada 100 personas que pasan, **{int(conversion_rate)} entran y compran**
    - Es el escenario "normal" - ni muy bueno ni muy malo
    
    **¿Cuándo pasa esto?**
    - 🏪 Ya llevas algunos meses funcionando
    - 🏬 Hay competencia pero también tienes tus clientes fieles
    - 🚶 Ubicación decente con flujo regular de gente
    - 💊 Ofreces buen servicio y precios competitivos
    
    **¿Es bueno o malo?**
    - 👍 Es el escenario **más realista** en la mayoría de casos
    - 👍 Balanceado - ni muy optimista ni muy pesimista
    - 📈 Con esfuerzo puedes llegar al escenario "Alto"
    """)
else:  # Alto
    st.success(f"""
    **🟢 ESCENARIO ALTO ({conversion_rate:.1f}% conversión peatonal)**
    
    **¿Qué significa?**
    - De cada 100 personas que pasan, **{int(conversion_rate)} entran y compran**
    - ¡Es el "sueño dorado" de cualquier farmacia!
    
    **¿Cuándo pasa esto?**
    - 🏪 Excelente ubicación (esquina, cerca de hospitales, etc.)
    - 🏬 Poca o nula competencia cerca
    - 🚶 Mucho flujo peatonal (zonas comerciales, plazas)
    - 💊 Servicio excepcional y clientes que te recomiendan
    
    **¿Es bueno o malo?**
    - 👍 ¡Es el **mejor escenario posible**!
    - ⚠️ Pero también el más **optimista** - difícil de lograr
    - 💡 Si logras esto, tendrás un negocio muy exitoso
    """)

# ¿Cómo afectan los escenarios a todos los números?
st.markdown("### 📊 ¿Cómo afecta tu escenario a TODOS los números?")

col_esc1, col_esc2, col_esc3 = st.columns(3)

with col_esc1:
    st.markdown("**🚶 Tráfico Peatonal**")
    st.metric("Peatones/día", f"{peatones_dia:,}")
    if escenario == "Conservador":
        st.caption("🔴 Ubicación con poco flujo")
    elif escenario == "Medio":
        st.caption("🟡 Flujo normal/regular")
    else:
        st.caption("🟢 Mucho flujo peatonal")

with col_esc2:
    st.markdown("**🚗 Tráfico Vehicular**")
    st.metric("Tickets desde autos/día", f"{tickets_vehiculares_dia:,.0f}")
    if escenario == "Conservador":
        st.caption("🔴 Baja captura por visibilidad")
    elif escenario == "Medio":
        st.caption("🟡 Captura razonable")
    else:
        st.caption("🟢 Buena accesibilidad")

with col_esc3:
    st.markdown("**📈 Crecimiento**")
    crec_anual = ((1 + crec) ** 12 - 1) * 100
    st.metric("Crecimiento anual", f"{crec_anual:.1f}%")
    if escenario == "Conservador":
        st.caption("🔴 Crecimiento lento")
    elif escenario == "Medio":
        st.caption("🟡 Crecimiento moderado")
    else:
        st.caption("🟢 Crecimiento acelerado")

st.info(f"""
**💡 En resumen:** El escenario **{escenario}** no solo afecta cuántos clientes te compran, 
sino también cuánto gastan, qué tan rápido crece tu negocio, y qué márgenes puedes obtener.

**Modelo de arranque:** El mes 1 arranca en **{arranque_inicial*100:.0f}%** del nivel estabilizado
y cargas **${gasto_lanzamiento:,}** por mes de apertura durante los primeros 3 meses.
""")

st.markdown("---")

# Validaciones claras
if contribucion <= 0:
    st.error("❌ Los números no cuadran. Los costos son muy altos para generar ganancia.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# RESUMEN EJECUTIVO (Lo más importante arriba)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🎯 ¿Es rentable este negocio?")

# Semáforo de rentabilidad
if util_anual > 0 and meses_recuperacion < 30:
    st.success(f"""
    ✅ **¡SÍ ES RENTABLE!**
    
    💰 **Mes 1: ${utilidad_mes_1:,.0f}** y luego estabilizas en **${utilidad_mes_estable:,.0f}/mes**
    
    ⏱️ **Recuperas tu inversión en {meses_recuperacion_fmt}**
    
    📈 **ROI del {roi_anual*100:.0f}% en el primer año** (ya considera rampa y apertura)
    """)
elif util_anual > 0:
    st.warning(f"""
    ⚠️ **ES RENTABLE, PERO TARDA**
    
    💰 **Mes 1: ${utilidad_mes_1:,.0f}** y estabilizas en **${utilidad_mes_estable:,.0f}/mes**
    
    ⏱️ Pero recuperas inversión en {meses_recuperacion_fmt} ({anios_recuperacion_fmt})
    
    💡 Conviene optimizar renta, mezcla de producto o tráfico antes de invertir
    """)
else:
    st.error(f"""
    ❌ **NO ES RENTABLE**
    
    📉 El primer año cerraría con **${abs(util_anual):,.0f}** de pérdida acumulada
    
    💡 Necesitas más tráfico, mejor conversión, más margen o una estructura de costos más ligera
    """)

# KPIs simplificados con explicaciones
st.markdown("### 📊 Los números clave")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("👥 Tickets/mes", f"{clientes_mes:,}")
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
    st.caption("Ventas mínimas para cubrir costos fijos")
    
with c6:
    st.metric("📈 ROI Año 1", f"{roi_anual*100:.0f}%")
    st.caption("Ya incluye meses flojos")

c7, c8, c9 = st.columns(3)
with c7:
    st.metric("💼 Utilidad estabilizada", f"${utilidad_mes_estable:,.0f}")
    st.caption("Run-rate operativo esperado")
with c8:
    st.metric("⏱️ Recuperación", f"{meses_recuperacion:.1f} meses" if meses_recuperacion < 120 else "N/A")
    st.caption("Tiempo para recuperar tu inversión")
with c9:
    st.metric("💸 Caja al mes 12", f"${df_num.iloc[-1]['Caja Acumulada']:,.0f}")
    st.caption("Caja acumulada neta")

# ¿De dónde vienen las ventas?
st.markdown("### 💵 ¿De dónde viene el dinero?")
desglose = {"💊 Farmacia": ventas_farmacia}
if m["consultorio"]:
    desglose["💉 Recetas"] = ventas_recetas
    desglose["🩺 Consultas"] = ingresos_consulta
if m["abarrotes"]:
    desglose["🛒 Abarrotes"] = ventas_abarrotes

col_desg = st.columns(len(desglose))
for i, (k, v) in enumerate(desglose.items()):
    pct = v / ventas_totales * 100 if ventas_totales > 0 else 0
    with col_desg[i]:
        st.metric(k, f"${v:,.0f}")
        st.caption(f"{pct:.0f}% de tus ventas")

# Análisis de márgenes por categoría (como analista financiero)
st.markdown("### 📈 Análisis de Márgenes por Categoría")
st.markdown("""
**Como analista financiero especializado en farmacias, estos son los márgenes optimizados:**

- **💊 Medicamentos Genéricos**: 35-45% margen (Mayor volumen, competencia alta)
- **💉 Medicamentos Patente**: 15-25% margen (Precios controlados, menor flexibilidad)  
- **🛒 Abarrotes**: 8-15% margen (Atrae tráfico, pero rentabilidad baja)
- **🩺 Consultas Médicas**: 75-80% margen (Solo costos de insumos básicos)

**Tu mix actual considera:**""")

col_mg1, col_mg2, col_mg3 = st.columns(3)
with col_mg1:
    margen_farmacia = (1 - cogs) * 100
    st.metric("💊 Margen Farmacia", f"{margen_farmacia:.0f}%")
    st.caption("Mix genéricos/patente optimizado")

with col_mg2:
    if m["consultorio"]:
        margen_recetas = (1 - cogs_receta) * 100
        st.metric("💉 Margen Recetas", f"{margen_recetas:.0f}%")
        st.caption("Recetas médicas especializadas")
    else:
        st.metric("💉 Recetas", "N/A")
        st.caption("No aplica en este modelo")

with col_mg3:
    if m["abarrotes"]:
        margen_abarrotes = (1 - p.get("cogs_abarrotes", 0.9)) * 100
        st.metric("🛒 Margen Abarrotes", f"{margen_abarrotes:.0f}%")
        st.caption("Productos de conveniencia")
    else:
        st.metric("🛒 Abarrotes", "N/A")
        st.caption("No aplica en este modelo")

# ¿En qué se va el dinero?
st.markdown("### 💸 ¿En qué se va el dinero?")

# Calcular gastos para mostrar
costo_producto = cogs_total
gastos_extras = gastos_variables

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
    total_gastos = costo_producto + gastos_fijos + gastos_extras
    st.metric("📉 Total gastos", f"${total_gastos:,.0f}")
    st.caption("Antes de gastos de apertura")

# Desglose detallado (colapsable)
with st.expander("📋 Ver detalle de inversión y gastos"):
    col_inv, col_gf, col_gv = st.columns(3)

    with col_inv:
        st.markdown("**💰 Tu Inversión Inicial**")
        st.metric("Monto total", f"${inversion:,.0f}")
        st.caption("Editable desde el panel lateral")

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

# Proyección 12 meses simplificada
st.markdown("### 📅 ¿Cómo se ve el primer año?")
# Tabla simplificada
df_simple = pd.DataFrame([{
    "Mes": p["Mes"],
    "Ventas": p["Ventas"],
    "Apertura": p["Apertura"],
    "Te queda": p["Util. Neta"],
    "Caja acumulada": f"${df_num.iloc[p['Mes'] - 1]['Caja Acumulada']:,.0f}",
} for p in proyeccion])
st.dataframe(df_simple, use_container_width=True, hide_index=True)

col_anual1, col_anual2 = st.columns(2)
with col_anual1:
    st.metric("💵 Ventas del año", f"${ventas_anual:,.0f}")
with col_anual2:
    st.metric("💰 Ganancia del año", f"${util_anual:,.0f}")

# Gráfica simple
st.markdown("### 📈 Evolución de tu negocio")
st.line_chart(df_num.set_index("Mes")[["Ventas", "Util. Neta", "Caja Acumulada"]])

# Resumen final claro
st.markdown("---")
st.markdown(f"""
### 🎯 Resumen para {modelo}

| Lo que inviertes | Lo que pagas cada mes | Lo que vendes al año | Lo que te queda |
|------------------|----------------------|---------------------|-----------------|
| **${inversion:,}** | **${gastos_fijos:,}** | **${ventas_anual:,.0f}** | **${util_anual:,.0f}** |

**En palabras simples:**
- 💰 Inviertes **${inversion:,}** una sola vez para abrir
- 🏢 Pagas **${gastos_fijos:,}** cada mes de gastos fijos (renta, luz, sueldos...)
- 📈 En el **mes 1** vendes **${ventas_mes_1:,.0f}**; ya estabilizado vendes **${ventas_totales:,.0f}** al mes
- 💵 El **mes 1** puedes ganar o perder **${utilidad_mes_1:,.0f}**; estabilizado te quedan **${utilidad_neta:,.0f}**
- ⏱️ Recuperas lo invertido en **{meses_recuperacion_fmt}** ({anios_recuperacion_fmt})
- 🎯 Necesitas vender mínimo **${ventas_be:,.0f}/mes** para no perder dinero
""")

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
    
    # Contenido del PDF
    story = []

    # Encabezado profesional con logo
    header_table = Table(
        [[
            Paragraph("<b>+FARMACIA LÍBANO</b>", title_style),
            crear_logo_pdf()
        ]],
        colWidths=[5.6 * inch, 1.0 * inch]
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
    <b>Modelo de Franquicia:</b> {modelo}<br/>
    <b>Escenario Analizado:</b> {escenario}<br/>
    <b>Inversión Requerida:</b> ${inversion:,}<br/>
    <b>Fecha de Análisis:</b> {pd.Timestamp.now().strftime('%d/%m/%Y')}<br/>
    """
    story.append(Paragraph(modelo_info, styles['Normal']))
    story.append(Spacer(1, 15))

    # Guía para el cliente
    story.append(Paragraph("📘 ¿Cómo leer este reporte?", heading_style))
    nivel_trafico = (
        "alto" if flujo_peatonal_dia >= 1200 else
        "medio" if flujo_peatonal_dia >= 700 else
        "moderado"
    )
    lectura_arranque = (
        "prudente" if arranque_inicial <= 0.45 else
        "balanceado" if arranque_inicial <= 0.60 else
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
    • El arranque proyectado es <b>{lectura_arranque}</b>, y el análisis sugiere <b>{lectura_rentabilidad}</b><br/><br/>
    
    <b>Qué debes revisar como cliente:</b><br/>
    • <b>Mes 1:</b> muestra el arranque realista, incluyendo el periodo de adaptación y gastos de apertura<br/>
    • <b>Mes estabilizado:</b> muestra cómo se comportaría la sucursal una vez que opere con mayor normalidad<br/>
    • <b>Primer año:</b> resume el impacto total del arranque, el crecimiento y la rentabilidad acumulada<br/>
    • <b>Punto de equilibrio:</b> indica el nivel mínimo de venta mensual necesario para cubrir costos fijos<br/><br/>
    
    La intención es que puedas usar este reporte para tomar una decisión más informada, comparar escenarios y detectar 
    qué variables tienen mayor impacto en la rentabilidad del proyecto. Si ajustas tráfico, horario, ticket o inversión, 
    el análisis cambia y el reporte se adapta automáticamente para reflejar ese nuevo escenario.
    """
    story.append(Paragraph(lectura_desc, styles['Normal']))
    story.append(Spacer(1, 18))

    # Resumen sencillo para cliente no técnico
    story.append(Paragraph("🧭 Lectura simple del escenario", heading_style))
    resumen_simple = f"""
    <b>En palabras simples:</b><br/>
    Hoy este análisis estima que con una inversión de <b>${inversion:,.0f}</b>, una operación de <b>{horas} horas diarias</b> 
    y un ticket promedio de <b>${ticket:,.0f}</b>, la sucursal puede vender alrededor de <b>${ventas_mes_1:,.0f}</b> en su primer mes 
    y acercarse a <b>${ventas_totales:,.0f}</b> mensuales cuando ya opere de forma estabilizada.<br/><br/>
    
    Esto significa que el negocio no se evalúa solo por “si gana o pierde”, sino por <b>qué tan rápido arranca</b>, 
    <b>cuánto tarda en madurar</b> y <b>cuánto tarda en recuperar la inversión</b>. Por eso este reporte separa claramente 
    el arranque, el punto estable y el resultado del primer año.
    """
    story.append(Paragraph(resumen_simple, styles['Normal']))
    story.append(Spacer(1, 18))
    
    # Explicación del escenario (VENDEDOR)
    story.append(Paragraph("🎯 Análisis del Escenario", heading_style))
    
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
    story.append(Paragraph("💡 Potencial del Modelo", heading_style))
    
    potencial_desc = f"""
    <b>El modelo {modelo} está diseñado para maximizar oportunidades:</b><br/>
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
    story.append(Paragraph("📊 Resultados Proyectados", heading_style))
    
    # Tabla de métricas principales (mejorada)
    metricas_data = [
        ['MÉTRICA CLAVE', 'RESULTADO'],
        ['Tickets mensuales estabilizados', f'{clientes_mes:,} tickets'],
        ['Ingresos mes 1', f'${ventas_mes_1:,.0f}'],
        ['Utilidad neta mes 1', f'${utilidad_mes_1:,.0f}'],
        ['Ingresos estabilizados', f'${ventas_totales:,.0f}'],
        ['Utilidad neta estabilizada', f'${utilidad_neta:,.0f}'],
        ['Margen de utilidad', f'{margen_neto*100:.1f}%'],
        ['ROI primer año', f'{roi_anual*100:.1f}%'],
        ['Período de recuperación', meses_recuperacion_fmt],
        ['Punto de equilibrio', f'${ventas_be:,.0f}/mes'],
        ['Ingresos primer año', f'${ventas_anual:,.0f}'],
        ['Utilidad primer año', f'${util_anual:,.0f}'],
    ]
    
    metricas_table = Table(metricas_data, colWidths=[3.2*inch, 2.3*inch])
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
    
    # Estructura de ingresos (MÁS VISUAL)
    story.append(Paragraph("💰 Estructura de Ingresos Mensuales Estabilizados", heading_style))
    
    ventas_data = [['LÍNEA DE NEGOCIO', 'INGRESOS', 'PARTICIPACIÓN']]
    ventas_data.append(['💊 Farmacia', f'${ventas_farmacia:,.0f}', f'{(ventas_farmacia/ventas_totales*100):.1f}%'])
    
    if m["consultorio"]:
        ventas_data.append(['💉 Recetas médicas', f'${ventas_recetas:,.0f}', f'{(ventas_recetas/ventas_totales*100):.1f}%'])
        ventas_data.append(['🩺 Consultas', f'${ingresos_consulta:,.0f}', f'{(ingresos_consulta/ventas_totales*100):.1f}%'])
    
    if m["abarrotes"]:
        ventas_data.append(['🛒 Conveniencia', f'${ventas_abarrotes:,.0f}', f'{(ventas_abarrotes/ventas_totales*100):.1f}%'])
    
    ventas_data.append(['🎯 TOTAL MENSUAL ESTABILIZADO', f'${ventas_totales:,.0f}', '100.0%'])
    
    ventas_table = Table(ventas_data, colWidths=[2.2*inch, 1.8*inch, 1.5*inch])
    ventas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.239, 0.478)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.Color(0.98, 0.98, 1.0)),
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),
    ]))
    
    story.append(ventas_table)
    story.append(Spacer(1, 20))
    
    # Evolución del negocio (TRIMESTRAL - más atractivo)
    story.append(Paragraph("📈 Evolución Trimestral del Primer Año", heading_style))
    
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
    
    proy_table = Table(proy_data, colWidths=[1.3*inch, 1.7*inch, 1.7*inch, 1.0*inch])
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
    story.append(Paragraph("🏆 Evaluación de la Oportunidad", heading_style))
    
    if util_anual > 0 and meses_recuperacion < 30:
        eval_color = colors.Color(0, 0.5, 0)  # Verde
        conclusion = f"""
        <b>✅ OPORTUNIDAD EXCELENTE</b><br/><br/>
        
        <b>Arranque Controlado:</b> El proyecto soporta el periodo inicial y cierra con utilidad positiva en el primer año<br/>
        <b>Recuperación Rápida:</b> Inversión recuperada en {meses_recuperacion_fmt}<br/>
        <b>ROI Atractivo:</b> {roi_anual*100:.1f}% en el primer año, ya considerando rampa de arranque<br/>
        <b>Mercado Estable:</b> Sector salud con demanda constante y creciente<br/><br/>
        
        <b>RECOMENDACIÓN:</b> Proceder con la inversión. Los números demuestran 
        una oportunidad sólida con riesgo controlado y potencial de crecimiento.
        """
    elif util_anual > 0:
        eval_color = colors.Color(0.7, 0.7, 0)  # Amarillo
        conclusion = f"""
        <b>⚠️ OPORTUNIDAD VIABLE CON CONSIDERACIONES</b><br/><br/>
        
        <b>Rentabilidad Positiva:</b> El primer año es positivo, pero con recuperación más lenta<br/>
        <b>Recuperación Moderada:</b> {meses_recuperacion_fmt} para recuperar inversión<br/>
        <b>Potencial de Mejora:</b> Optimizaciones operativas pueden acelerar retornos<br/><br/>
        
        <b>RECOMENDACIÓN:</b> Evaluar mejoras en ubicación o eficiencias operativas 
        para acelerar la recuperación. Base sólida con oportunidades de optimización.
        """
    else:
        eval_color = colors.Color(0.8, 0.2, 0)  # Rojo suave (no muy negativo)
        conclusion = f"""
        <b>📊 OPORTUNIDAD REQUIERE AJUSTES</b><br/><br/>
        
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
    story.append(Paragraph("🚀 Próximos Pasos Recomendados", heading_style))
    
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
    story.append(Paragraph("⚖️ Consideraciones Importantes", heading_style))
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
    if st.button("📥 Generar PDF", type="primary"):
        with st.spinner("Generando reporte PDF..."):
            pdf_bytes = generar_reporte_pdf()
            st.download_button(
                label="📄 Descargar Reporte PDF", 
                data=pdf_bytes,
                file_name=f"corrida_financiera_{modelo.replace(' ', '_').lower()}_{escenario.lower()}.pdf",
                mime="application/pdf"
            )
with col_pdf2:
    st.caption("Genera un reporte ejecutivo profesional para presentar esta oportunidad de inversión a socios, inversionistas o para tu análisis detallado.")

# Recomendaciones útiles (tono constructivo)
if meses_recuperacion > 24:
    st.info("💡 **Oportunidad de optimización:** Con mejoras en ubicación o eficiencias operativas, puedes acelerar la recuperación de tu inversión.")
if clientes_mes < clientes_be:
    st.warning(f"📊 **Análisis de tráfico:** Para alcanzar el punto de equilibrio necesitas {int(clientes_be):,} clientes vs {clientes_mes:,} proyectados. Considera estrategias de marketing local.")
if margen_neto < 0.05 and utilidad_neta > 0:
    st.info("🎯 **Potencial de mejora:** Los márgenes pueden optimizarse mejorando la mezcla de productos o negociando mejores condiciones con proveedores.")
