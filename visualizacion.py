import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# =========================
# CONFIGURACIÓN
# =========================

st.set_page_config(
    page_title="Visualización de Torneo - Karate",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Auto-refresh cada 5 segundos
st_autorefresh(interval=5000, key="refresh_visualizacion")

# =========================
# CONEXIÓN SUPABASE
# =========================

def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = conectar_supabase()

# =========================
# FUNCIONES DE DATOS
# =========================

@st.cache_data(ttl=3)
def cargar_graficas():
    respuesta = (
        supabase
        .table("graficas")
        .select("*")
        .order("id", desc=False)
        .execute()
    )
    return respuesta.data


def convertir_fila_a_grafica(fila):
    return {
        "id": fila["id"],
        "nombre_grafica": fila["nombre_grafica"],
        "reglamento": fila["reglamento"],
        "modalidad": fila["modalidad"],
        "categoria_edad": fila["categoria_edad"],
        "sexo": fila["sexo"],
        "area": fila.get("area", "Área 1"),
        "tipo_competencia": fila.get("tipo_competencia", "eliminacion_directa"),
        "estatus": fila["estatus"],
        "ronda_actual": fila["ronda_actual"],
        "competidores": fila["competidores_json"] or [],
        "encuentros": fila["encuentros_json"] or [],
        "esperan": fila.get("esperan_json", []),
        "historial": fila["historial_json"] or [],
        "resultados_round_robin": fila.get("resultados_round_robin", {}),
        "ganadores": fila["ganadores_json"] or {
            "primer_lugar": "",
            "segundo_lugar": "",
            "tercero_1": "",
            "tercero_2": ""
        },
        "fecha_creacion": fila["fecha_creacion"]
    }


def obtener_encuentro_actual(grafica):
    """Obtiene el primer encuentro no finalizado"""
    for i, e in enumerate(grafica["encuentros"]):
        if not e.get("finalizado", False):
            return e, i
    return None, -1


def obtener_siguiente_encuentro(grafica, indice_actual):
    """Obtiene el siguiente encuentro no finalizado"""
    for i in range(indice_actual + 1, len(grafica["encuentros"])):
        if not grafica["encuentros"][i].get("finalizado", False):
            return grafica["encuentros"][i]
    return None


def obtener_competidores_estado(grafica):
    """Determina el estado de cada competidor (Activo/Eliminado)"""
    if grafica["tipo_competencia"] == "Round Robin":
        return obtener_estado_round_robin(grafica)
    
    # Para eliminación directa
    competidores_dict = {}
    
    # Inicializar todos como activos
    for c in grafica["competidores"]:
        competidores_dict[c["nombre"]] = {
            "nombre": c["nombre"],
            "escuela": c["escuela"],
            "estado": "🟢 Activo"
        }
    
    # Marcar eliminados
    for resultado in grafica["historial"]:
        perdedor = resultado.get("perdedor", "")
        if perdedor and perdedor in competidores_dict:
            competidores_dict[perdedor]["estado"] = "🔴 Eliminado"
    
    return list(competidores_dict.values())


def obtener_estado_round_robin(grafica):
    """Para Round Robin, todos siguen activos hasta el final"""
    competidores_estado = []
    for c in grafica["competidores"]:
        competidores_estado.append({
            "nombre": c["nombre"],
            "escuela": c["escuela"],
            "estado": "🟡 En competencia"
        })
    return competidores_estado


def formatear_competidor(competidor):
    """Formatea un competidor para mostrar"""
    if isinstance(competidor, dict):
        return competidor
    return {"nombre": competidor, "escuela": "Sin escuela"}


# =========================
# FUNCIONES DE VISUALIZACIÓN
# =========================

def mostrar_detalle_grafica(grafica):
    """Muestra el detalle de una gráfica según su estatus"""
    
    # Encabezado con información general
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📍 Área", grafica["area"])
    with col2:
        estatus_emoji = {
            "Pendiente": "⚪",
            "En desarrollo": "🟡",
            "Finalizado": "🔴"
        }
        st.metric("📊 Estatus", f"{estatus_emoji.get(grafica['estatus'], '')} {grafica['estatus']}")
    with col3:
        st.metric("🥋 Modalidad", grafica["modalidad"])
    with col4:
        st.metric("📋 Reglamento", grafica["reglamento"])
    
    # Información adicional
    st.caption(f"**Categoría:** {grafica['categoria_edad']} | **Sexo:** {grafica['sexo']} | **Tipo:** {grafica['tipo_competencia'].replace('_', ' ').title()}")
    
    st.divider()
    
    # Mostrar según estatus
    if grafica["estatus"] == "Pendiente":
        mostrar_pendiente(grafica)
    elif grafica["estatus"] == "En desarrollo":
        mostrar_en_desarrollo(grafica)
    elif grafica["estatus"] == "Finalizado":
        mostrar_finalizado(grafica)


def mostrar_pendiente(grafica):
    """Muestra la información para gráficas pendientes"""
    st.subheader("📋 Competidores Inscritos")
    
    if grafica["competidores"]:
        df = pd.DataFrame(grafica["competidores"])
        df.index = range(1, len(df) + 1)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay competidores registrados.")


def mostrar_en_desarrollo(grafica):
    """Muestra la información para gráficas en desarrollo"""
    
    # Encuentro actual
    encuentro_actual, indice = obtener_encuentro_actual(grafica)
    
    if encuentro_actual:
        st.subheader("⚡ ENCUENTRO EN CURSO")
        
        c1 = formatear_competidor(encuentro_actual["competidor_1"])
        c2 = formatear_competidor(encuentro_actual.get("competidor_2"))
        
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col1:
            st.markdown(f"""
            <div style="background-color:#e53935; padding:30px; border-radius:15px; text-align:center;">
                <h1 style="color:white; margin:0; font-size:48px;">🔴 {c1['nombre']}</h1>
                <p style="color:white; font-size:24px; margin:10px 0;">{c1['escuela']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="text-align:center; padding:30px;">
                <h1 style="font-size:72px; margin:0;">VS</h1>
                <p style="font-size:20px; color:gray;">Ronda {grafica['ronda_actual']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            if c2:
                color_fondo = "#1e88e5" if grafica["reglamento"] == "WKF" else "#f5f5f5"
                color_texto = "white" if grafica["reglamento"] == "WKF" else "black"
                st.markdown(f"""
                <div style="background-color:{color_fondo}; padding:30px; border-radius:15px; text-align:center;">
                    <h1 style="color:{color_texto}; margin:0; font-size:48px;">🔵 {c2['nombre']}</h1>
                    <p style="color:{color_texto}; font-size:24px; margin:10px 0;">{c2['escuela']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color:#666; padding:30px; border-radius:15px; text-align:center;">
                    <h1 style="color:white; margin:0; font-size:48px;">BYE</h1>
                    <p style="color:white; font-size:24px; margin:10px 0;">Pase directo</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Siguiente encuentro
        st.divider()
        siguiente = obtener_siguiente_encuentro(grafica, indice)
        
        if siguiente:
            st.subheader("⏭️ PRÓXIMO ENCUENTRO")
            
            s1 = formatear_competidor(siguiente["competidor_1"])
            s2 = formatear_competidor(siguiente.get("competidor_2"))
            
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                st.markdown(f"""
                <div style="background-color:#444; padding:15px; border-radius:10px; text-align:center;">
                    <h3 style="color:white; margin:0;">{s1['nombre']}</h3>
                    <p style="color:#CCC; margin:5px 0;">{s1['escuela']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
            
            with col3:
                if s2:
                    st.markdown(f"""
                    <div style="background-color:#444; padding:15px; border-radius:10px; text-align:center;">
                        <h3 style="color:white; margin:0;">{s2['nombre']}</h3>
                        <p style="color:#CCC; margin:5px 0;">{s2['escuela']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background-color:#444; padding:15px; border-radius:10px; text-align:center;">
                        <h3 style="color:white; margin:0;">Por definir</h3>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("⏭️ No hay más encuentros pendientes en esta ronda.")
        
        # Tabla de resultados
        if grafica["historial"]:
            st.divider()
            st.subheader("📜 Resultados de Rondas Anteriores")
            
            resultados_df = []
            for r in grafica["historial"]:
                if grafica["modalidad"] == "Kata":
                    banderas_r1 = r.get("banderas_rojo", 0)
                    banderas_r2 = r.get("banderas_azul", r.get("banderas_blanco", 0))
                    resultados_df.append({
                        "Ronda": r["ronda"],
                        "Competidor 1": r["competidor_1"],
                        "Competidor 2": r["competidor_2"],
                        "Resultado": f"{banderas_r1} - {banderas_r2}",
                        "Ganador": r["ganador"]
                    })
                else:
                    resultados_df.append({
                        "Ronda": r["ronda"],
                        "Competidor 1": r["competidor_1"],
                        "Competidor 2": r["competidor_2"],
                        "Resultado": f"{r.get('puntos_1', 0)} - {r.get('puntos_2', 0)}",
                        "Ganador": r["ganador"]
                    })
            
            if resultados_df:
                st.dataframe(pd.DataFrame(resultados_df), use_container_width=True, hide_index=True)
        
        # Tabla de competidores con estado
        st.divider()
        st.subheader("👥 Estado de Competidores")
        
        competidores_estado = obtener_competidores_estado(grafica)
        if competidores_estado:
            df_estado = pd.DataFrame(competidores_estado)
            st.dataframe(df_estado, use_container_width=True, hide_index=True)
        
    else:
        st.info("No hay encuentros en desarrollo.")


def mostrar_finalizado(grafica):
    """Muestra la información para gráficas finalizadas"""
    
    # Podio de ganadores
    st.subheader("🏆 PODIO DE GANADORES")
    
    ganadores = grafica["ganadores"]
    primer = ganadores.get("primer_lugar", "")
    segundo = ganadores.get("segundo_lugar", "")
    tercero_1 = ganadores.get("tercero_1", "")
    tercero_2 = ganadores.get("tercero_2", "")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if primer:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #FFD700, #FFA000); padding:30px; border-radius:15px; text-align:center;">
                <h1 style="color:white; margin:0; font-size:36px;">🥇 PRIMER LUGAR</h1>
                <h2 style="color:white; margin:10px 0; font-size:48px;">{primer}</h2>
            </div>
            """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if segundo:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #C0C0C0, #808080); padding:20px; border-radius:10px; text-align:center;">
                <h3 style="color:white; margin:0;">🥈 SEGUNDO</h3>
                <h4 style="color:white; margin:10px 0;">{segundo}</h4>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if tercero_1:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #CD7F32, #8B4513); padding:20px; border-radius:10px; text-align:center;">
                <h3 style="color:white; margin:0;">🥉 TERCERO</h3>
                <h4 style="color:white; margin:10px 0;">{tercero_1}</h4>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if tercero_2:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #CD7F32, #8B4513); padding:20px; border-radius:10px; text-align:center;">
                <h3 style="color:white; margin:0;">🥉 TERCERO</h3>
                <h4 style="color:white; margin:10px 0;">{tercero_2}</h4>
            </div>
            """, unsafe_allow_html=True)
    
    # Tabla de competidores ordenados por resultado
    st.divider()
    st.subheader("📋 Clasificación Final")
    
    if grafica["tipo_competencia"] == "Round Robin" and grafica.get("resultados_round_robin"):
        resultados = grafica["resultados_round_robin"]
        lista = list(resultados.values())
        
        if grafica["modalidad"] == "Kata":
            lista.sort(key=lambda x: (x.get("encuentros_ganados", 0), x.get("banderas_favor", 0)), reverse=True)
        else:
            lista.sort(key=lambda x: (x.get("encuentros_ganados", 0), x.get("puntos_favor", 0)), reverse=True)
        
        df_final = pd.DataFrame(lista)
        df_final.index = range(1, len(df_final) + 1)
        st.dataframe(df_final, use_container_width=True)
    else:
        # Mostrar lista de competidores con su posición
        competidores_lista = []
        for c in grafica["competidores"]:
            posicion = ""
            if c["nombre"] == primer:
                posicion = "🥇 1°"
            elif c["nombre"] == segundo:
                posicion = "🥈 2°"
            elif c["nombre"] == tercero_1:
                posicion = "🥉 3°"
            elif c["nombre"] == tercero_2:
                posicion = "🥉 3°"
            
            competidores_lista.append({
                "Posición": posicion,
                "Nombre": c["nombre"],
                "Escuela": c["escuela"]
            })
        
        df_competidores = pd.DataFrame(competidores_lista)
        st.dataframe(df_competidores, use_container_width=True, hide_index=True)
    
    # Historial de resultados
    if grafica["historial"]:
        st.divider()
        st.subheader("📜 Historial de Encuentros")
        
        historial_df = []
        for r in grafica["historial"]:
            if grafica["modalidad"] == "Kata":
                banderas_r1 = r.get("banderas_rojo", 0)
                banderas_r2 = r.get("banderas_azul", r.get("banderas_blanco", 0))
                historial_df.append({
                    "Ronda": r["ronda"],
                    "Competidor 1": r["competidor_1"],
                    "Competidor 2": r["competidor_2"],
                    "Resultado": f"{banderas_r1} - {banderas_r2}",
                    "Ganador": r["ganador"]
                })
            else:
                historial_df.append({
                    "Ronda": r["ronda"],
                    "Competidor 1": r["competidor_1"],
                    "Competidor 2": r["competidor_2"],
                    "Resultado": f"{r.get('puntos_1', 0)} - {r.get('puntos_2', 0)}",
                    "Ganador": r["ganador"]
                })
        
        if historial_df:
            st.dataframe(pd.DataFrame(historial_df), use_container_width=True, hide_index=True)


# =========================
# INTERFAZ PRINCIPAL
# =========================

st.title("🏆 Torneo de Karate - Visualización en Vivo")

# Cargar datos
datos = cargar_graficas()
graficas = [convertir_fila_a_grafica(fila) for fila in datos]

if not graficas:
    st.info("📋 No hay gráficas registradas en el torneo.")
    st.stop()

# =========================
# FILTROS
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    areas_disponibles = list(set(g["area"] for g in graficas))
    area_filtro = st.selectbox(
        "📍 Filtrar por Área",
        ["Todas"] + sorted(areas_disponibles)
    )

with col2:
    estatus_filtro = st.selectbox(
        "📊 Filtrar por Estatus",
        ["Todos", "Pendiente", "En desarrollo", "Finalizado"]
    )

with col3:
    modalidades = list(set(g["modalidad"] for g in graficas))
    modalidad_filtro = st.selectbox(
        "🥋 Filtrar por Modalidad",
        ["Todas"] + sorted(modalidades)
    )

# Aplicar filtros
graficas_filtradas = graficas.copy()

if area_filtro != "Todas":
    graficas_filtradas = [g for g in graficas_filtradas if g["area"] == area_filtro]

if estatus_filtro != "Todos":
    graficas_filtradas = [g for g in graficas_filtradas if g["estatus"] == estatus_filtro]

if modalidad_filtro != "Todas":
    graficas_filtradas = [g for g in graficas_filtradas if g["modalidad"] == modalidad_filtro]

# =========================
# LISTADO DE GRÁFICAS
# =========================

st.divider()

# Crear tabs para cada gráfica
if graficas_filtradas:
    tabs = st.tabs([
        f"{'🔴' if g['estatus'] == 'Finalizado' else '🟡' if g['estatus'] == 'En desarrollo' else '⚪'} "
        f"{g['nombre_grafica']} ({g['modalidad']})"
        for g in graficas_filtradas
    ])
    
    for tab, grafica in zip(tabs, graficas_filtradas):
        with tab:
            mostrar_detalle_grafica(grafica)
else:
    st.info("No hay gráficas que coincidan con los filtros seleccionados.")

# =========================
# PIE DE PÁGINA
# =========================

st.divider()
st.caption("🔄 Esta página se actualiza automáticamente cada 5 segundos")
