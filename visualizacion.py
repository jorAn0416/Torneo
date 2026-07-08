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
        st.metric("Área", grafica["area"])
    with col2:
        estatus_emoji = {
            "Pendiente": "⚪",
            "En desarrollo": "🟡",
            "Finalizado": "🔴"
        }
        st.metric("Estatus", f"{estatus_emoji.get(grafica['estatus'], '')} {grafica['estatus']}")
    with col3:
        st.metric("Modalidad", grafica["modalidad"])
    with col4:
        st.metric("Reglamento", grafica["reglamento"])
    
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
    st.subheader("Competidores Inscritos")
    
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
        st.subheader("ENCUENTRO EN CURSO")
        
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
    else:
        st.info("No hay encuentros en desarrollo.")
    
    # =========================
    # DIAGRAMA DE LLAVES (BRACKET)
    # =========================
    st.divider()
    st.subheader("Diagrama de Competencia")
    
    if grafica["tipo_competencia"] == "Round Robin":
        st.info("El diagrama de llaves no está disponible para Round Robin. Todos compiten contra todos.")
    else:
        # Construir el bracket basado en el historial y encuentros
        mostrar_bracket_eliminacion(grafica)
    
    # Tabla de resultados (solo si hay historial)
    if grafica["historial"]:
        st.divider()
        st.subheader("Resultados de Rondas Anteriores")
        
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


def mostrar_bracket_eliminacion(grafica):
    """
    Muestra un diagrama de llaves (bracket) para eliminación directa.
    Omite las rondas preliminares (ronda 0) del diagrama principal.
    """
    # Separar encuentros por rondas, excluyendo preliminar (ronda 0)
    encuentros_por_ronda = {}
    hay_preliminar = False
    
    # Revisar si hay ronda preliminar en curso
    for e in grafica["encuentros"]:
        ronda = e.get("ronda", 1)
        
        # Detectar ronda preliminar
        if ronda == 0:
            hay_preliminar = True
            continue  # No incluir en el bracket
        
        if ronda not in encuentros_por_ronda:
            encuentros_por_ronda[ronda] = []
        encuentros_por_ronda[ronda].append(e)
    
    # También considerar historial para rondas pasadas (excluyendo ronda 0)
    for r in grafica["historial"]:
        ronda = r.get("ronda", 1)
        
        # Saltar rondas preliminares
        if ronda == 0:
            continue
        
        if ronda not in encuentros_por_ronda:
            encuentros_por_ronda[ronda] = []
        
        # Evitar duplicados
        c1_nombre = r.get("competidor_1", "?")
        c2_nombre = r.get("competidor_2", "?")
        ya_existe = False
        
        for e in encuentros_por_ronda[ronda]:
            e_c1 = e.get("competidor_1", {})
            e_c2 = e.get("competidor_2", {})
            e_c1_nombre = e_c1.get("nombre", "") if isinstance(e_c1, dict) else str(e_c1)
            e_c2_nombre = e_c2.get("nombre", "") if isinstance(e_c2, dict) else str(e_c2)
            
            if e_c1_nombre == c1_nombre and e_c2_nombre == c2_nombre:
                ya_existe = True
                break
        
        if not ya_existe:
            encuentros_por_ronda[ronda].append({
                "competidor_1": {"nombre": c1_nombre},
                "competidor_2": {"nombre": c2_nombre} if c2_nombre else None,
                "ganador": {"nombre": r.get("ganador", "")} if r.get("ganador") else None,
                "finalizado": True,
                "ronda": ronda
            })
    
    # Mostrar aviso de ronda preliminar si existe
    if hay_preliminar:
        # Buscar el encuentro preliminar actual
        encuentro_preliminar = None
        for e in grafica["encuentros"]:
            if e.get("ronda") == 0 and not e.get("finalizado", False):
                encuentro_preliminar = e
                break
        
        if encuentro_preliminar:
            c1 = encuentro_preliminar.get("competidor_1", {})
            c2 = encuentro_preliminar.get("competidor_2", {})
            c1_nombre = c1.get("nombre", "?") if isinstance(c1, dict) else str(c1)
            c2_nombre = c2.get("nombre", "?") if isinstance(c2, dict) else str(c2) if c2 else "?"
            
            st.warning(f"""
            **RONDA PRELIMINAR EN CURSO** 
            
            Se está realizando un encuentro preliminar para igualar el número de competidores.
            
            **{c1_nombre}** ▌ **{c2_nombre}**
            
            El ganador se integrará a la primera ronda. El diagrama de llaves se mostrará cuando inicien las rondas normales.
            """)
        else:
            # Preliminar ya finalizado
            st.info("""
            Se realizó una ronda preliminar para igualar el número de competidores.
            El resultado se encuentra en el historial de encuentros.
            El diagrama muestra solo las rondas normales.
            """)
    
    # Si no hay rondas normales todavía
    if not encuentros_por_ronda:
        if hay_preliminar:
            # Mostrar mensaje de espera
            st.markdown("""
            <div style="text-align:center; padding:40px; background-color:#222; border-radius:10px;">
                <h3 style="color:#FFD700;"> Diagrama de Competencia</h3>
                <p style="color:#CCC; font-size:18px;">El bracket se generará cuando finalice la ronda preliminar y comiencen las rondas normales.</p>
                <p style="color:#999;">Mientras tanto, puedes ver el encuentro preliminar en la parte superior.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No hay encuentros para mostrar en el diagrama.")
        return
    
    # Ordenar rondas (solo rondas normales: 1, 2, 3, ...)
    rondas_ordenadas = sorted(encuentros_por_ronda.keys())
    
    # Verificar que tengamos rondas válidas
    if not rondas_ordenadas:
        st.info("Esperando a que se definan los encuentros de la primera ronda...")
        return
    
    # Título del bracket
    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <h3 style="color:#FFD700;"> Llaves de Eliminación</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Crear columnas para cada ronda
    num_rondas = len(rondas_ordenadas)
    columnas = st.columns(num_rondas)
    
    for idx, ronda in enumerate(rondas_ordenadas):
        with columnas[idx]:
            # Determinar nombre de la ronda de forma segura
            es_ultima_ronda = (idx == num_rondas - 1)
            es_penultima_ronda = (idx == num_rondas - 2)
            
            # Determinar si esta ronda es la final (última ronda con 1 solo encuentro)
            es_final = es_ultima_ronda and len(encuentros_por_ronda[ronda]) == 1
            
            # Determinar si esta ronda es semifinal (penúltima cuando la última tiene 1 encuentro)
            if es_penultima_ronda and num_rondas >= 2:
                ultima_ronda_key = rondas_ordenadas[-1]
                es_semifinal = len(encuentros_por_ronda.get(ultima_ronda_key, [])) == 1
            else:
                es_semifinal = False
            
            # Asignar nombre
            if es_final:
                nombre_ronda = "FINAL"
            elif es_semifinal:
                nombre_ronda = "SEMIFINAL"
            else:
                nombre_ronda = f"RONDA {ronda}"
            
            st.markdown(f"""
            <div style="text-align:center; background-color:#1a1a2e; padding:10px; border-radius:5px; margin-bottom:15px; border:1px solid #FFD700;">
                <strong style="color:#FFD700; font-size:16px;">{nombre_ronda}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            encuentros_ronda = encuentros_por_ronda[ronda]
            
            for e in encuentros_ronda:
                c1 = e.get("competidor_1", {})
                c2 = e.get("competidor_2", {})
                ganador = e.get("ganador", {})
                
                c1_nombre = c1.get("nombre", "?") if isinstance(c1, dict) else str(c1)
                c2_nombre = c2.get("nombre", "BYE") if isinstance(c2, dict) else str(c2) if c2 else "BYE"
                ganador_nombre = ganador.get("nombre", "") if isinstance(ganador, dict) else str(ganador) if ganador else ""
                
                # Determinar colores según estado
                if e.get("finalizado", False):
                    if ganador_nombre:
                        bg_c1 = "#2E7D32" if c1_nombre == ganador_nombre else "#555"
                        bg_c2 = "#2E7D32" if c2_nombre == ganador_nombre else "#555"
                        bg_c1 = "#C62828" if c1_nombre != ganador_nombre and ganador_nombre else bg_c1
                        bg_c2 = "#C62828" if c2_nombre != ganador_nombre and ganador_nombre else bg_c2
                    else:
                        bg_c1 = "#555"
                        bg_c2 = "#555"
                else:
                    bg_c1 = "#444"
                    bg_c2 = "#444"
                
                # Emoji para ganador
                emoji_c1 = "" if c1_nombre == ganador_nombre and ganador_nombre else ""
                emoji_c2 = "" if c2_nombre == ganador_nombre and ganador_nombre else ""
                
                # Si es BYE
                if c2_nombre == "BYE" and not e.get("finalizado", False):
                    bg_c2 = "#1a1a2e"
                    c2_nombre = "Por definir"
                
                st.markdown(f"""
                <div style="background-color:#1a1a2e; padding:12px; border-radius:8px; margin:3px 0; border-left:4px solid {bg_c1}; border-right:1px solid #333;">
                    <div style="color:white; font-size:13px; font-weight:bold;">
                        {emoji_c1}{c1_nombre[:25]}
                    </div>
                </div>
                <div style="text-align:center; color:#666; font-size:10px; margin:1px 0;"> ▌ </div>
                <div style="background-color:#1a1a2e; padding:12px; border-radius:8px; margin:3px 0; border-left:4px solid {bg_c2}; border-right:1px solid #333;">
                    <div style="color:white; font-size:13px; font-weight:bold;">
                        {emoji_c2}{c2_nombre[:25]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Espacio entre encuentros
                if len(encuentros_ronda) > 1:
                    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    
    # Leyenda
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("🟢 **Verde** = Ganador")
    with col2:
        st.markdown("🔴 **Rojo** = Eliminado")
    with col3:
        st.markdown("⚫ **Gris** = Pendiente")
    with col4:
        st.markdown(" = Campeón")
    
    # Mostrar total de rondas
    st.caption(f"Total de rondas normales: {num_rondas} | Ronda actual: {grafica['ronda_actual']}")


def mostrar_finalizado(grafica):
    """Muestra la información para gráficas finalizadas"""
    
    # Podio de ganadores
    st.subheader("PODIO DE GANADORES")
    
    ganadores = grafica["ganadores"]
    primer = ganadores.get("primer_lugar", "")
    segundo = ganadores.get("segundo_lugar", "")
    tercero_1 = ganadores.get("tercero_1", "")
    tercero_2 = ganadores.get("tercero_2", "")
    
    # Mostrar debug para verificar datos
    st.caption(f"Debug - 1°: {primer}, 2°: {segundo}, 3°_1: {tercero_1}, 3°_2: {tercero_2}")
    
    # PRIMER LUGAR - Centrado y grande
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if primer:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #FFD700, #FFA000); padding:30px; border-radius:15px; text-align:center; margin-bottom:20px;">
                <h1 style="color:white; margin:0; font-size:36px;">🥇 PRIMER LUGAR</h1>
                <h2 style="color:white; margin:10px 0; font-size:48px;">{primer}</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #FFD700, #FFA000); padding:30px; border-radius:15px; text-align:center; margin-bottom:20px;">
                <h1 style="color:white; margin:0; font-size:36px;">🥇 PRIMER LUGAR</h1>
                <h2 style="color:white; margin:10px 0; font-size:36px;">Por definir</h2>
            </div>
            """, unsafe_allow_html=True)
    
    # SEGUNDO Y TERCEROS - En fila
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Determinar cuántos terceros lugares hay
    num_terceros = (1 if tercero_1 else 0) + (1 if tercero_2 else 0)
    
    if num_terceros == 2:
        # 4 columnas: segundo, tercero_1, tercero_2, vacío
        col1, col2, col3, col4 = st.columns(4)
    elif num_terceros == 1:
        # 3 columnas: segundo, tercero_1, vacío
        col1, col2, col3 = st.columns(3)
    else:
        # 2 columnas: segundo, vacío
        col1, col2 = st.columns(2)
    
    with col1:
        if segundo:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #C0C0C0, #808080); padding:20px; border-radius:10px; text-align:center;">
                <h3 style="color:white; margin:0;">🥈 SEGUNDO LUGAR</h3>
                <h4 style="color:white; margin:10px 0; font-size:28px;">{segundo}</h4>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #C0C0C0, #808080); padding:20px; border-radius:10px; text-align:center;">
                <h3 style="color:white; margin:0;">🥈 SEGUNDO LUGAR</h3>
                <h4 style="color:white; margin:10px 0; font-size:24px;">Por definir</h4>
            </div>
            """, unsafe_allow_html=True)
    
    if num_terceros >= 1:
        with col2:
            if tercero_1:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #CD7F32, #8B4513); padding:20px; border-radius:10px; text-align:center;">
                    <h3 style="color:white; margin:0;">🥉 TERCER LUGAR</h3>
                    <h4 style="color:white; margin:10px 0; font-size:28px;">{tercero_1}</h4>
                </div>
                """, unsafe_allow_html=True)
    
    if num_terceros == 2:
        with col3:
            if tercero_2:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #CD7F32, #8B4513); padding:20px; border-radius:10px; text-align:center;">
                    <h3 style="color:white; margin:0;">🥉 TERCER LUGAR</h3>
                    <h4 style="color:white; margin:10px 0; font-size:28px;">{tercero_2}</h4>
                </div>
                """, unsafe_allow_html=True)

    # Tabla de clasificación final
    st.divider()
    st.subheader("Clasificación Final")
    
    if grafica["tipo_competencia"] == "Round Robin" and grafica.get("resultados_round_robin"):
        resultados = grafica["resultados_round_robin"]
        lista = list(resultados.values())
        
        if grafica["modalidad"] == "Kata":
            lista.sort(key=lambda x: (x.get("encuentros_ganados", 0), x.get("banderas_favor", 0)), reverse=True)
        else:
            lista.sort(key=lambda x: (x.get("encuentros_ganados", 0), x.get("puntos_favor", 0)), reverse=True)
        
        if lista:
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
                "Posición": posicion if posicion else "-",
                "Nombre": c["nombre"],
                "Escuela": c["escuela"]
            })
        
        if competidores_lista:
            df_competidores = pd.DataFrame(competidores_lista)
            st.dataframe(df_competidores, use_container_width=True, hide_index=True)
    
    # Historial de resultados
    if grafica["historial"]:
        st.divider()
        st.subheader("Historial de Encuentros")
        
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

st.title("Copa Okinawa - Visualización en Vivo")

# Cargar datos
datos = cargar_graficas()
graficas = [convertir_fila_a_grafica(fila) for fila in datos]

if not graficas:
    st.info("Aun no hay gráficas registradas en el torneo.")
    st.stop()

# =========================
# FILTROS
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    areas_disponibles = list(set(g["area"] for g in graficas))
    area_filtro = st.selectbox(
        "Filtrar por Área",
        ["Todas"] + sorted(areas_disponibles)
    )

with col2:
    estatus_filtro = st.selectbox(
        "Filtrar por Estatus",
        ["Todos", "Pendiente", "En desarrollo", "Finalizado"]
    )

with col3:
    modalidades = list(set(g["modalidad"] for g in graficas))
    modalidad_filtro = st.selectbox(
        "Filtrar por Modalidad",
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
st.caption("Esta página se actualiza automáticamente cada 5 segundos")
