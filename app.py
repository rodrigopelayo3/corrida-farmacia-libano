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
from reportlab.graphics.shapes import Drawing
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
    st.caption(f"Inversión total para {modelo}")
    
    # Inicializar inversión personalizada
    if "inversion_personalizada" not in st.session_state:
        st.session_state.inversion_personalizada = m["inversion"]
    
    inversion_input = st.number_input(
        f"Inversión Total - {modelo}",
        min_value=100000,
        value=st.session_state.inversion_personalizada,
        step=10000,
        help="Incluye local, inventario, equipo, permisos y capital de trabajo"
    )
    
    st.session_state.inversion_personalizada = inversion_input
    
    # Mostrar comparación con preset
    diferencia = inversion_input - m["inversion"]
    if diferencia > 0:
        st.info(f"📈 +${diferencia:,} sobre precio base")
    elif diferencia < 0:
        st.success(f"📉 ${abs(diferencia):,} menos que precio base")
    else:
        st.info("💰 Precio base estándar")

# Usar inversión personalizada
inversion = st.session_state.inversion_personalizada

# ═══════════════════════════════════════════════════════════════════════════════
# INPUTS SIMPLIFICADOS (Los % técnicos se manejan automáticamente)
# ═══════════════════════════════════════════════════════════════════════════════

# Parámetros técnicos automáticos (según escenario - el usuario NO los ve)
cogs = p["cogs"]  # Costo de mercancía
cogs_receta = p.get("cogs_receta", cogs)
cogs_abarrotes = p.get("cogs_abarrotes", 0.88)
gastos_var = p["gastos_var"]  # Gastos variables

with st.sidebar.expander("👥 ¿Cuánta gente pasa por tu local?", expanded=True):
    st.caption("💡 Cuenta cuántas personas pasan frente a tu local en una hora típica")
    flujo = st.number_input(
        "Personas por hora", 
        10, 300, p["flujo"],
        help="Promedio de gente que pasa caminando frente a tu local"
    )
    
    # Explicación visual
    flujo_dia = flujo * 12  # asumiendo 12 horas
    st.info(f"📊 Eso significa **~{flujo_dia:,} personas/día** pasando por tu local")

with st.sidebar.expander("🛒 ¿Cuánto compra cada cliente?", expanded=True):
    st.caption("💡 El ticket promedio es lo que gasta un cliente típico")
    ticket = st.number_input(
        "Ticket promedio farmacia ($)", 
        40, 300, p["ticket"],
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
            0, 40, p.get("consultas", 0),
            help="¿Cuántas consultas médicas esperas al día?"
        )
        ingreso_consulta = st.number_input(
            "Cobro por consulta ($)", 
            0, 150, p.get("ingreso_consulta", 40),
            help="¿Cuánto cobras por cada consulta?"
        )
        ticket_receta = st.number_input(
            "Compra promedio con receta ($)", 
            50, 400, p.get("ticket_receta", 120),
            help="Los pacientes con receta gastan más"
        )
        
        # Parámetro automático
        surten = p.get("surten", 0.6)
        
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

# Proyección simplificada
with st.sidebar.expander("📈 Crecimiento esperado", expanded=False):
    st.caption("💡 ¿Cuánto esperas crecer cada mes?")
    crec_opcion = st.radio(
        "Expectativa de crecimiento",
        ["🐢 Conservador (1%/mes)", "🚶 Moderado (3%/mes)", "🚀 Agresivo (5%/mes)"],
        index=1
    )
    crec = {"🐢 Conservador (1%/mes)": 0.01, "🚶 Moderado (3%/mes)": 0.03, "🚀 Agresivo (5%/mes)": 0.05}[crec_opcion]
    
    st.info(f"📈 En 12 meses tus ventas crecerían ~{((1+crec)**12 - 1)*100:.0f}%")

# Vector de estacionalidad fijo (simplificado)
est_vector = np.ones(12)

# Valores fijos de operación (simplificados)
horas = 12
dias = 28
conversion = p["conversion"]

# ═══════════════════════════════════════════════════════════════════════════════
# CÁLCULOS - MES BASE
# ═══════════════════════════════════════════════════════════════════════════════
flujo_mes = flujo * horas * dias
clientes_mes = int(flujo_mes * conversion)

# Ventas
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

# Break-even
contribucion = 1 - cogs - gastos_var
if contribucion > 0:
    ventas_be = gastos_fijos / contribucion
    clientes_be = ventas_be / ticket if ticket > 0 else 0
else:
    ventas_be, clientes_be = float('inf'), float('inf')

# ROI (inversion ya calculada desde session_state)
roi_anual = (utilidad_neta * 12) / inversion if inversion > 0 else 0
meses_recuperacion = inversion / utilidad_neta if utilidad_neta > 0 else float('inf')

# ═══════════════════════════════════════════════════════════════════════════════
# PROYECCIÓN 12 MESES
# ═══════════════════════════════════════════════════════════════════════════════
proyeccion = []
proyeccion_num = []  # Para gráficas
for t in range(12):
    factor = ((1 + crec) ** t) * est_vector[t]
    vf = ventas_farmacia * factor
    vr = ventas_recetas * factor
    va = ventas_abarrotes * factor
    ic = ingresos_consulta * factor
    vt = vf + vr + va + ic
    
    ct = vf * cogs + vr * cogs_receta + va * cogs_abarrotes
    ub = vt - ct
    gv = vt * gastos_var
    un = ub - gastos_fijos - gv
    mn = un / vt if vt > 0 else 0
    
    # Para tabla (formateado)
    proyeccion.append({
        "Mes": t + 1,
        "Ventas": f"${round(vt):,}",
        "COGS": f"${round(ct):,}",
        "Util. Bruta": f"${round(ub):,}",
        "Gastos Fijos": f"${round(gastos_fijos):,}",
        "Gastos Var.": f"${round(gv):,}",
        "Util. Neta": f"${round(un):,}",
        "Margen %": f"{round(mn * 100, 1)}%",
    })
    
    # Para gráficas (numérico)
    proyeccion_num.append({
        "Mes": t + 1,
        "Ventas": round(vt),
        "Util. Neta": round(un),
        "Margen %": round(mn * 100, 1),
    })

df = pd.DataFrame(proyeccion)
df_num = pd.DataFrame(proyeccion_num)

# Calcular totales
util_anual = df_num["Util. Neta"].sum()
ventas_anual = df_num["Ventas"].sum()

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
st.markdown("### 👥 Análisis de Flujo Peatonal")
personas_dia = flujo
conversion_rate = conversion * 100

col_flujo1, col_flujo2, col_flujo3 = st.columns(3)
with col_flujo1:
    st.metric("🚶 Pasan por día", f"{personas_dia:,}")
    st.caption("Flujo peatonal diario")
    
with col_flujo2:
    st.metric("🛍️ Te compran", f"{clientes_mes:,}/mes")
    st.caption(f"Solo {conversion_rate:.1f}% del flujo compra")
    
with col_flujo3:
    st.metric("💳 Ticket promedio", f"${ticket_prom:,.0f}")
    st.caption("Lo que gasta cada cliente")

# Explicación detallada del % de conversión por escenario
st.markdown("### 🎯 ¿Qué significa tu escenario?")

if escenario == "Conservador":
    st.warning(f"""
    **🔴 ESCENARIO CONSERVADOR ({conversion_rate:.1f}% conversión)**
    
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
    **🟡 ESCENARIO MEDIO ({conversion_rate:.1f}% conversión)**
    
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
    **🟢 ESCENARIO ALTO ({conversion_rate:.1f}% conversión)**
    
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
    st.markdown("**🚶 Flujo Peatonal**")
    st.metric("Personas/día", f"{flujo:,}")
    if escenario == "Conservador":
        st.caption("🔴 Ubicación con poco flujo")
    elif escenario == "Medio":
        st.caption("🟡 Flujo normal/regular")
    else:
        st.caption("🟢 Mucho flujo peatonal")

with col_esc2:
    st.markdown("**💳 Ticket Promedio**")
    st.metric("Gasto/cliente", f"${ticket_prom:,.0f}")
    if escenario == "Conservador":
        st.caption("🔴 Clientes más cautelosos")
    elif escenario == "Medio":
        st.caption("🟡 Gasto promedio normal")
    else:
        st.caption("🟢 Clientes gastan más")

with col_esc3:
    st.markdown("**📈 Crecimiento**")
    crec_anual = p.get("crec", 0) * 12 * 100
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

**¿Por qué?** En mejores ubicaciones puedes cobrar un poco más, los clientes compran más cosas, 
y el boca a boca hace que crezcas más rápido. ¡Todo está conectado! 🔗
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
if utilidad_neta > 0 and meses_recuperacion < 24:
    st.success(f"""
    ✅ **¡SÍ ES RENTABLE!**
    
    💰 **Ganarías ${utilidad_neta:,.0f} al mes** (después de pagar todo)
    
    ⏱️ **Recuperas tu inversión en {meses_recuperacion:.1f} meses**
    
    📈 **ROI del {roi_anual*100:.0f}% anual** (tu dinero crece {roi_anual*100:.0f}% cada año)
    """)
elif utilidad_neta > 0:
    st.warning(f"""
    ⚠️ **ES RENTABLE, PERO TARDA**
    
    💰 Ganarías ${utilidad_neta:,.0f} al mes
    
    ⏱️ Pero recuperas inversión en {meses_recuperacion:.0f} meses ({meses_recuperacion/12:.1f} años)
    
    💡 Considera reducir gastos fijos o buscar mejor ubicación
    """)
else:
    st.error(f"""
    ❌ **NO ES RENTABLE**
    
    📉 Perderías ${abs(utilidad_neta):,.0f} al mes
    
    💡 Necesitas: más clientes, subir precios, o reducir gastos
    """)

# KPIs simplificados con explicaciones
st.markdown("### 📊 Los números clave")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("👥 Clientes/mes", f"{clientes_mes:,}")
    st.caption("Personas que te compran al mes")
    
with c2:
    st.metric("💵 Ventas/mes", f"${ventas_totales:,.0f}")
    st.caption("Todo lo que entra de dinero")
    
with c3:
    st.metric("💰 Te queda/mes", f"${utilidad_neta:,.0f}")
    st.caption("Tu ganancia real (después de pagar TODO)")

c4, c5, c6 = st.columns(3)
with c4:
    st.metric("🎯 Punto de equilibrio", f"${ventas_be:,.0f}")
    st.caption("Ventas mínimas para no perder")
    
with c5:
    st.metric("⏱️ Recuperación", f"{meses_recuperacion:.1f} meses" if meses_recuperacion < 100 else "N/A")
    st.caption("Tiempo para recuperar tu inversión")
    
with c6:
    st.metric("📈 ROI Anual", f"{roi_anual*100:.0f}%")
    st.caption("Cuánto crece tu dinero al año")

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
    st.metric("📊 Otros gastos", f"${gastos_extras:,.0f}")
    st.caption("Comisiones, bolsas, etc.")
with col_g4:
    total_gastos = costo_producto + gastos_fijos + gastos_extras
    st.metric("📉 Total gastos", f"${total_gastos:,.0f}")
    st.caption("Todo lo que sale")

# Desglose detallado (colapsable)
with st.expander("📋 Ver detalle de inversión y gastos fijos"):
    col_inv, col_gf = st.columns(2)

    with col_inv:
        st.markdown("**💰 Tu Inversión Inicial**")
        if "inversion_items" in st.session_state:
            inv_df = pd.DataFrame([
                {"Concepto": k, "Monto": f"${v:,}"} 
                for k, v in st.session_state.inversion_items.items()
            ])
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
            st.markdown(f"**Total: ${inversion:,}**")

    with col_gf:
        st.markdown("**🏢 Tus Gastos Fijos Mensuales**")
        if "gastos_fijos_items" in st.session_state:
            gf_df = pd.DataFrame([
                {"Concepto": k, "Monto": f"${v:,}"} 
                for k, v in st.session_state.gastos_fijos_items.items()
            ])
            st.dataframe(gf_df, use_container_width=True, hide_index=True)
            st.markdown(f"**Total: ${gastos_fijos:,}/mes**")

# Proyección 12 meses simplificada
st.markdown("### 📅 ¿Cómo se ve el primer año?")
# Tabla simplificada
df_simple = pd.DataFrame([{
    "Mes": p["Mes"],
    "Ventas": p["Ventas"],
    "Te queda": p["Util. Neta"],
} for p in proyeccion])
st.dataframe(df_simple, use_container_width=True, hide_index=True)

col_anual1, col_anual2 = st.columns(2)
with col_anual1:
    st.metric("💵 Ventas del año", f"${ventas_anual:,.0f}")
with col_anual2:
    st.metric("💰 Ganancia del año", f"${util_anual:,.0f}")

# Gráfica simple
st.markdown("### 📈 Evolución de tu negocio")
st.line_chart(df_num.set_index("Mes")[["Ventas", "Util. Neta"]])

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
- 📈 Vendes **${ventas_totales:,.0f}** al mes y te quedan **${utilidad_neta:,.0f}** de ganancia
- ⏱️ En **{meses_recuperacion:.0f} meses** ({meses_recuperacion/12:.1f} años) recuperas lo que invertiste
- 🎯 Necesitas vender mínimo **${ventas_be:,.0f}/mes** para no perder dinero
""")

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE REPORTE PDF
# ═══════════════════════════════════════════════════════════════════════════════
def generar_reporte_pdf():
    """Genera un reporte PDF profesional con todos los datos financieros"""
    
    # Buffer para el PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], 
                                fontSize=24, spaceAfter=30, textColor=colors.Color(0, 0.239, 0.478))
    
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], 
                                  fontSize=16, spaceAfter=12, textColor=colors.Color(0, 0.651, 0.318))
    
    # Contenido del PDF
    story = []
    
    # Encabezado
    story.append(Paragraph("<b>+FARMACIA LÍBANO</b>", title_style))
    story.append(Paragraph("Corrida Financiera - Reporte Ejecutivo", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    # Información del modelo
    modelo_info = f"""
    <b>Modelo:</b> {modelo}<br/>
    <b>Escenario:</b> {escenario}<br/>
    <b>Fecha:</b> {pd.Timestamp.now().strftime('%d/%m/%Y')}<br/>
    <b>Inversión:</b> ${inversion:,}<br/>
    """
    story.append(Paragraph(modelo_info, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Resumen ejecutivo
    story.append(Paragraph("📊 Resumen Ejecutivo", heading_style))
    
    # Tabla de métricas principales
    metricas_data = [
        ['Métrica', 'Valor'],
        ['Clientes por mes', f'{clientes_mes:,}'],
        ['Ventas mensuales', f'${ventas_totales:,.0f}'],
        ['Utilidad neta mensual', f'${utilidad_neta:,.0f}'],
        ['Margen neto', f'{margen_neto*100:.1f}%'],
        ['ROI anual', f'{roi_anual*100:.1f}%'],
        ['Recuperación (meses)', f'{meses_recuperacion:.1f}'],
        ['Break-even ventas', f'${ventas_be:,.0f}'],
        ['Ventas anuales', f'${ventas_anual:,.0f}'],
        ['Utilidad anual', f'${util_anual:,.0f}'],
    ]
    
    metricas_table = Table(metricas_data, colWidths=[3*inch, 2*inch])
    metricas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.651, 0.318)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(metricas_table)
    story.append(Spacer(1, 20))
    
    # Desglose de ventas
    story.append(Paragraph("💵 Desglose de Ventas Mensuales", heading_style))
    
    ventas_data = [['Concepto', 'Monto', '% del Total']]
    ventas_data.append(['Farmacia', f'${ventas_farmacia:,.0f}', f'{(ventas_farmacia/ventas_totales*100):.1f}%'])
    
    if m["consultorio"]:
        ventas_data.append(['Recetas', f'${ventas_recetas:,.0f}', f'{(ventas_recetas/ventas_totales*100):.1f}%'])
        ventas_data.append(['Consultas', f'${ingresos_consulta:,.0f}', f'{(ingresos_consulta/ventas_totales*100):.1f}%'])
    
    if m["abarrotes"]:
        ventas_data.append(['Abarrotes', f'${ventas_abarrotes:,.0f}', f'{(ventas_abarrotes/ventas_totales*100):.1f}%'])
    
    ventas_data.append(['TOTAL', f'${ventas_totales:,.0f}', '100.0%'])
    
    ventas_table = Table(ventas_data, colWidths=[2*inch, 2*inch, 1*inch])
    ventas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.651, 0.318)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(ventas_table)
    story.append(Spacer(1, 20))
    
    # Proyección 12 meses (resumida - solo alguns meses clave)
    story.append(Paragraph("📅 Proyección 12 Meses (Trimestral)", heading_style))
    
    proy_data = [['Mes', 'Ventas', 'Utilidad Neta', 'Margen %']]
    for i in [0, 2, 5, 8, 11]:  # Meses 1, 3, 6, 9, 12
        proy_data.append([
            f'Mes {i+1}',
            proyeccion[i]['Ventas'],
            proyeccion[i]['Util. Neta'],
            proyeccion[i]['Margen %']
        ])
    
    proy_table = Table(proy_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 1*inch])
    proy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.651, 0.318)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(proy_table)
    story.append(Spacer(1, 20))
    
    # Inversión y gastos fijos
    if "inversion_items" in st.session_state:
        story.append(Paragraph("💰 Desglose de Inversión Inicial", heading_style))
        
        inv_data = [['Concepto', 'Monto']]
        for concepto, monto in st.session_state.inversion_items.items():
            inv_data.append([concepto, f'${monto:,}'])
        inv_data.append(['TOTAL', f'${inversion:,}'])
        
        inv_table = Table(inv_data, colWidths=[3*inch, 2*inch])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.239, 0.478)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(inv_table)
        story.append(Spacer(1, 20))
    
    # Gastos fijos
    if "gastos_fijos_items" in st.session_state:
        story.append(Paragraph("🏢 Gastos Fijos Mensuales", heading_style))
        
        gf_data = [['Concepto', 'Monto']]
        for concepto, monto in st.session_state.gastos_fijos_items.items():
            gf_data.append([concepto, f'${monto:,}'])
        gf_data.append(['TOTAL', f'${gastos_fijos:,}'])
        
        gf_table = Table(gf_data, colWidths=[3*inch, 2*inch])
        gf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0, 0.239, 0.478)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(gf_table)
    
    # Conclusiones
    story.append(Spacer(1, 20))
    story.append(Paragraph("🎯 Conclusiones", heading_style))
    
    if utilidad_neta > 0 and meses_recuperacion < 24:
        conclusion = "✅ <b>NEGOCIO RENTABLE:</b> Genera utilidades positivas con recuperación de inversión en menos de 2 años."
    elif utilidad_neta > 0:
        conclusion = "⚠️ <b>RENTABLE CON RESERVAS:</b> Genera utilidades pero la recuperación de inversión es lenta."
    else:
        conclusion = "❌ <b>NO RENTABLE:</b> El negocio no genera utilidades suficientes con los parámetros actuales."
    
    story.append(Paragraph(conclusion, styles['Normal']))
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph("<i>Reporte generado por Motor de Corrida Financiera - Farmacia Líbano</i>", styles['Normal']))
    
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
    st.caption("Genera un reporte PDF profesional con todos los datos financieros, proyecciones y análisis completo.")

# Advertencias útiles
if meses_recuperacion > 24:
    st.warning("⚠️ **Cuidado:** Tardas más de 2 años en recuperar la inversión. Considera opciones para mejorar.")
if clientes_mes < clientes_be:
    st.error(f"❌ **Problema:** Necesitas {int(clientes_be):,} clientes para no perder, pero solo estás proyectando {clientes_mes:,}")
if margen_neto < 0.05 and utilidad_neta > 0:
    st.warning("⚠️ Margen muy bajo. Cualquier imprevisto te puede poner en números rojos.")
