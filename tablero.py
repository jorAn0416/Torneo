import streamlit as st
import pandas as pd
from datetime import datetime
import random

st.set_page_config(
    page_title="Generador de Gráficas Karate",
    layout="wide"
)

# =========================
# ESTADOS INICIALES
# =========================

if "graficas" not in st.session_state:
    st.session_state.graficas = []

if "competidores_temp" not in st.session_state:
    st.session_state.competidores_temp = []


# =========================
# FUNCIONES GENERALES
# =========================

def registrar_competidor(nombre, escuela, modalidad, edad, sexo):
    competidor = {
        "nombre": nombre,
        "escuela": escuela,
        "modalidad": modalidad,
        "edad": edad,
        "sexo": sexo
    }
    st.session_state.competidores_temp.append(competidor)


def obtener_escuela(grafica, nombre_competidor):
    for competidor in grafica["competidores"]:
        if competidor["nombre"] == nombre_competidor:
            return competidor["escuela"]
    return "Sin escuela registrada"


def crear_encuentros(competidores):
    lista = competidores.copy()
    random.shuffle(lista)

    encuentros = []

    while len(lista) >= 2:
        c1 = lista.pop(0)
        c2 = lista.pop(0)

        encuentros.append({
            "competidor_1": c1,
            "competidor_2": c2,
            "resultado": None,
            "ganador": None,
            "finalizado": False
        })

    if len(lista) == 1:
        encuentros.append({
            "competidor_1": lista[0],
            "competidor_2": None,
            "resultado": "BYE",
            "ganador": lista[0],
            "finalizado": True
        })

    return encuentros


def crear_grafica(nombre_grafica, reglamento, modalidad, categoria_edad, sexo, banderas_kata):
    competidores = st.session_state.competidores_temp.copy()

    nueva_grafica = {
        "id": len(st.session_state.graficas) + 1,
        "nombre_grafica": nombre_grafica,
        "reglamento": reglamento,
        "modalidad": modalidad,
        "categoria_edad": categoria_edad,
        "sexo": sexo,
        "banderas_kata": banderas_kata,
        "competidores": competidores,
        "estatus": "Pendiente",
        "ronda_actual": 1,
        "encuentros": crear_encuentros(competidores),
        "historial": [],
        "ganadores": {
            "primer_lugar": "",
            "segundo_lugar": "",
            "tercer_lugar": ""
        },
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    st.session_state.graficas.append(nueva_grafica)
    st.session_state.competidores_temp = []


def obtener_dataframe_graficas():
    datos = []

    for grafica in st.session_state.graficas:
        datos.append({
            "ID": grafica["id"],
            "Nombre": grafica["nombre_grafica"],
            "Reglamento": grafica["reglamento"],
            "Modalidad": grafica["modalidad"],
            "Edad": grafica["categoria_edad"],
            "Sexo": grafica["sexo"],
            "Competidores": len(grafica["competidores"]),
            "Ronda": grafica["ronda_actual"],
            "Estatus": grafica["estatus"]
        })

    return pd.DataFrame(datos)


def avanzar_ronda_si_corresponde(grafica):
    encuentros = grafica["encuentros"]

    if all(e["finalizado"] for e in encuentros):
        ganadores = [e["ganador"] for e in encuentros if e["ganador"] is not None]

        if len(ganadores) == 1:
            grafica["ganadores"]["primer_lugar"] = ganadores[0]["nombre"]
            grafica["estatus"] = "Finalizado"
            return

        grafica["ronda_actual"] += 1
        grafica["encuentros"] = crear_encuentros(ganadores)


# =========================
# TABLERO KUMITE
# =========================

def tablero_kumite(grafica, encuentro, indice):
    c1 = encuentro["competidor_1"]
    c2 = encuentro["competidor_2"]

    if c2 is None:
        st.success(f'{c1["nombre"]} pasa por BYE.')
        return

    reglamento = grafica["reglamento"]

    if reglamento == "WUKF":
        color_1 = "Rojo"
        color_2 = "Blanco"
        puntos_validos = {
            "WAZA-ARI": 1,
            "IPPON": 2
        }
        limite_sanbon = st.selectbox(
            "Modo WUKF",
            ["Sanbon - 6 puntos", "Nihon - 4 puntos"],
            key=f"modo_wukf_{grafica['id']}_{indice}"
        )
        limite_puntos = 6 if "Sanbon" in limite_sanbon else 4

    else:
        color_1 = "Rojo"
        color_2 = "Azul"
        puntos_validos = {
            "YUKO": 1,
            "WAZA-ARI": 2,
            "IPPON": 3
        }
        limite_puntos = None

    estado_key = f"kumite_{grafica['id']}_{grafica['ronda_actual']}_{indice}"

    if estado_key not in st.session_state:
        st.session_state[estado_key] = {
            "puntos_1": 0,
            "puntos_2": 0,
            "faltas_1": 0,
            "faltas_2": 0,
            "faltas_tipo1_1": 0,
            "faltas_tipo2_1": 0,
            "faltas_tipo1_2": 0,
            "faltas_tipo2_2": 0
        }

    estado = st.session_state[estado_key]

    st.markdown(f"## Encuentro {indice + 1}")

    col_rojo, col_centro, col_azul = st.columns([4, 2, 4])

    with col_rojo:
        st.markdown(
            f"""
            <div style='background-color:#e53935; padding:20px; border-radius:12px; text-align:center;'>
                <h1 style='color:white;'>{color_1}</h1>
                <h2 style='color:white;'>{c1["nombre"]}</h2>
                <h4 style='color:white;'>{c1["escuela"]}</h4>
                <h1 style='color:white; font-size:90px;'>{estado["puntos_1"]}</h1>
                <h3 style='color:white;'>Faltas: {estado["faltas_1"]}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        for nombre_punto, valor in puntos_validos.items():
            if st.button(f"{color_1} +{valor} {nombre_punto}", key=f"p1_{nombre_punto}_{estado_key}"):
                estado["puntos_1"] += valor
                st.rerun()

        if reglamento == "WUKF":
            colf1, colf2 = st.columns(2)

            with colf1:
                if st.button(f"{color_1} Falta Tipo 1", key=f"ft1_1_{estado_key}"):
                    estado["faltas_tipo1_1"] += 1
                    estado["faltas_1"] += 1
                    st.rerun()

            with colf2:
                if st.button(f"{color_1} Falta Tipo 2", key=f"ft2_1_{estado_key}"):
                    estado["faltas_tipo2_1"] += 1
                    estado["faltas_1"] += 1
                    st.rerun()

        else:
            if st.button(f"{color_1} Falta", key=f"f1_{estado_key}"):
                estado["faltas_1"] += 1
                st.rerun()

    with col_centro:
        tiempo = st.text_input(
            "Cronómetro",
            value="02:00",
            key=f"tiempo_{estado_key}"
        )

        st.markdown(
            f"""
            <div style='background-color:black; color:white; text-align:center; padding:20px; border-radius:12px;'>
                <h1>{estado["puntos_1"]} - {estado["puntos_2"]}</h1>
                <h2>{tiempo}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Reiniciar marcador", key=f"reset_{estado_key}"):
            st.session_state[estado_key] = {
                "puntos_1": 0,
                "puntos_2": 0,
                "faltas_1": 0,
                "faltas_2": 0,
                "faltas_tipo1_1": 0,
                "faltas_tipo2_1": 0,
                "faltas_tipo1_2": 0,
                "faltas_tipo2_2": 0
            }
            st.rerun()

    with col_azul:
        color_fondo = "#1e88e5" if reglamento == "WKF" else "#f5f5f5"
        color_texto = "white" if reglamento == "WKF" else "black"

        st.markdown(
            f"""
            <div style='background-color:{color_fondo}; padding:20px; border-radius:12px; text-align:center;'>
                <h1 style='color:{color_texto};'>{color_2}</h1>
                <h2 style='color:{color_texto};'>{c2["nombre"]}</h2>
                <h4 style='color:{color_texto};'>{c2["escuela"]}</h4>
                <h1 style='color:{color_texto}; font-size:90px;'>{estado["puntos_2"]}</h1>
                <h3 style='color:{color_texto};'>Faltas: {estado["faltas_2"]}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        for nombre_punto, valor in puntos_validos.items():
            if st.button(f"{color_2} +{valor} {nombre_punto}", key=f"p2_{nombre_punto}_{estado_key}"):
                estado["puntos_2"] += valor
                st.rerun()

        if reglamento == "WUKF":
            colf1, colf2 = st.columns(2)

            with colf1:
                if st.button(f"{color_2} Falta Tipo 1", key=f"ft1_2_{estado_key}"):
                    estado["faltas_tipo1_2"] += 1
                    estado["faltas_2"] += 1
                    st.rerun()

            with colf2:
                if st.button(f"{color_2} Falta Tipo 2", key=f"ft2_2_{estado_key}"):
                    estado["faltas_tipo2_2"] += 1
                    estado["faltas_2"] += 1
                    st.rerun()

        else:
            if st.button(f"{color_2} Falta", key=f"f2_{estado_key}"):
                estado["faltas_2"] += 1
                st.rerun()

    ganador_automatico = None
    motivo = ""

    if reglamento == "WUKF":
        if estado["puntos_1"] >= limite_puntos:
            ganador_automatico = c1
            motivo = f"{c1['nombre']} gana por llegar a {limite_puntos} puntos."

        elif estado["puntos_2"] >= limite_puntos:
            ganador_automatico = c2
            motivo = f"{c2['nombre']} gana por llegar a {limite_puntos} puntos."

        elif estado["faltas_tipo1_1"] >= 3 or estado["faltas_tipo2_1"] >= 4:
            ganador_automatico = c2
            motivo = f"{c1['nombre']} pierde por acumulación de faltas."

        elif estado["faltas_tipo1_2"] >= 3 or estado["faltas_tipo2_2"] >= 4:
            ganador_automatico = c1
            motivo = f"{c2['nombre']} pierde por acumulación de faltas."

    else:
        if abs(estado["puntos_1"] - estado["puntos_2"]) >= 8:
            ganador_automatico = c1 if estado["puntos_1"] > estado["puntos_2"] else c2
            motivo = "Victoria por diferencia de 8 puntos."

        elif estado["faltas_1"] >= 5:
            ganador_automatico = c2
            motivo = f"{c1['nombre']} pierde por acumulación de 5 faltas."

        elif estado["faltas_2"] >= 5:
            ganador_automatico = c1
            motivo = f"{c2['nombre']} pierde por acumulación de 5 faltas."

    if ganador_automatico:
        st.success(motivo)

    st.divider()

    st.subheader("Finalizar encuentro")

    opciones_ganador = [
        c1["nombre"],
        c2["nombre"]
    ]

    if ganador_automatico:
        ganador_nombre = ganador_automatico["nombre"]
    else:
        ganador_nombre = st.selectbox(
            "Selecciona ganador",
            opciones_ganador,
            key=f"ganador_manual_{estado_key}"
        )

    if st.button("Registrar resultado Kumite", key=f"registrar_kumite_{estado_key}"):
        ganador = c1 if ganador_nombre == c1["nombre"] else c2
        perdedor = c2 if ganador_nombre == c1["nombre"] else c1

        encuentro["resultado"] = {
            "tipo": "Kumite",
            "puntos_1": estado["puntos_1"],
            "puntos_2": estado["puntos_2"],
            "faltas_1": estado["faltas_1"],
            "faltas_2": estado["faltas_2"],
            "ganador": ganador["nombre"],
            "perdedor": perdedor["nombre"]
        }

        encuentro["ganador"] = ganador
        encuentro["finalizado"] = True

        grafica["historial"].append(encuentro["resultado"])

        st.success("Resultado registrado.")
        avanzar_ronda_si_corresponde(grafica)
        st.rerun()


# =========================
# TABLERO KATA
# =========================

def tablero_kata(grafica, encuentro, indice):
    c1 = encuentro["competidor_1"]
    c2 = encuentro["competidor_2"]

    if c2 is None:
        st.success(f'{c1["nombre"]} pasa por BYE.')
        return

    banderas = grafica["banderas_kata"]

    estado_key = f"kata_{grafica['id']}_{grafica['ronda_actual']}_{indice}"

    if estado_key not in st.session_state:
        st.session_state[estado_key] = {
            "banderas_1": 0,
            "banderas_2": 0
        }

    estado = st.session_state[estado_key]

    st.markdown(f"## Encuentro Kata {indice + 1}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div style='background-color:#e53935; padding:20px; border-radius:12px; text-align:center;'>
                <h1 style='color:white;'>Rojo</h1>
                <h2 style='color:white;'>{c1["nombre"]}</h2>
                <h4 style='color:white;'>{c1["escuela"]}</h4>
                <h1 style='color:white; font-size:80px;'>{estado["banderas_1"]}</h1>
                <h3 style='color:white;'>Banderas</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Agregar bandera Rojo", key=f"bandera_1_{estado_key}"):
            if estado["banderas_1"] < banderas:
                estado["banderas_1"] += 1
                st.rerun()

    with col2:
        st.markdown(
            f"""
            <div style='background-color:#f5f5f5; padding:20px; border-radius:12px; text-align:center; border:2px solid black;'>
                <h1 style='color:black;'>Blanco / Azul</h1>
                <h2 style='color:black;'>{c2["nombre"]}</h2>
                <h4 style='color:black;'>{c2["escuela"]}</h4>
                <h1 style='color:black; font-size:80px;'>{estado["banderas_2"]}</h1>
                <h3 style='color:black;'>Banderas</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Agregar bandera Blanco/Azul", key=f"bandera_2_{estado_key}"):
            if estado["banderas_2"] < banderas:
                estado["banderas_2"] += 1
                st.rerun()

    st.info(f"Total de banderas disponibles: {banderas}")

    if estado["banderas_1"] + estado["banderas_2"] != banderas:
        st.warning("Todavía no se han registrado todas las banderas.")

    ganador = None

    if estado["banderas_1"] > estado["banderas_2"]:
        ganador = c1
    elif estado["banderas_2"] > estado["banderas_1"]:
        ganador = c2

    if ganador:
        st.success(f"Ganador provisional: {ganador['nombre']}")

    if st.button("Registrar resultado Kata", key=f"registrar_kata_{estado_key}"):
        if estado["banderas_1"] + estado["banderas_2"] == banderas and ganador:
            perdedor = c2 if ganador == c1 else c1

            encuentro["resultado"] = {
                "tipo": "Kata",
                "banderas_1": estado["banderas_1"],
                "banderas_2": estado["banderas_2"],
                "ganador": ganador["nombre"],
                "perdedor": perdedor["nombre"]
            }

            encuentro["ganador"] = ganador
            encuentro["finalizado"] = True

            grafica["historial"].append(encuentro["resultado"])

            st.success("Resultado de kata registrado.")
            avanzar_ronda_si_corresponde(grafica)
            st.rerun()
        else:
            st.warning("Debes registrar todas las banderas y debe existir un ganador.")


# =========================
# INTERFAZ PRINCIPAL
# =========================

st.title("Sistema de Organización de Gráficas - Karate")

rol = st.sidebar.selectbox(
    "Selecciona el tipo de usuario",
    [
        "Registro",
        "Área de competencias",
        "Premiaciones"
    ]
)


# =========================
# REGISTRO
# =========================

if rol == "Registro":
    st.header("Registro de competidores y creación de gráfica")

    col1, col2, col3 = st.columns(3)

    with col1:
        nombre_grafica = st.text_input("Nombre de la gráfica", placeholder="Ejemplo: Grafica1")
        reglamento = st.selectbox("Reglamento", ["WUKF", "WKF"])

    with col2:
        modalidad = st.selectbox("Modalidad", ["Kata", "Kumite"])
        sexo = st.selectbox("Sexo", ["Masculino", "Femenino", "Mixto"])

    with col3:
        categoria_edad = st.text_input(
            "Categoría de edad",
            placeholder="Ejemplo: 12, 10-12, Adultos 18-34, Master 35+"
        )

        if modalidad == "Kata":
            banderas_kata = st.selectbox("Número de banderas", [3, 5])
        else:
            banderas_kata = None

    st.divider()

    st.subheader("Agregar competidor")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        nombre = st.text_input("Nombre del competidor")

    with col2:
        escuela = st.text_input("Escuela")

    with col3:
        edad = st.text_input("Edad", placeholder="Ejemplo: 12")

    with col4:
        agregar = st.button("Agregar competidor")

    if agregar:
        if nombre and escuela and edad:
            registrar_competidor(nombre, escuela, modalidad, edad, sexo)
            st.success(f"Competidor {nombre} agregado.")
        else:
            st.warning("Completa nombre, escuela y edad.")

    if st.session_state.competidores_temp:
        st.dataframe(pd.DataFrame(st.session_state.competidores_temp), use_container_width=True)
    else:
        st.info("Todavía no hay competidores agregados.")

    if st.button("Crear gráfica"):
        if nombre_grafica and categoria_edad and len(st.session_state.competidores_temp) > 0:
            crear_grafica(
                nombre_grafica,
                reglamento,
                modalidad,
                categoria_edad,
                sexo,
                banderas_kata
            )
            st.success(f"La gráfica {nombre_grafica} fue creada con estatus Pendiente.")
        else:
            st.warning("Falta nombre de gráfica, categoría de edad o competidores.")

    st.divider()

    st.subheader("Lista general de gráficas")

    if st.session_state.graficas:
        st.dataframe(obtener_dataframe_graficas(), use_container_width=True)
    else:
        st.info("Aún no hay gráficas creadas.")


# =========================
# ÁREA DE COMPETENCIAS
# =========================

elif rol == "Área de competencias":
    st.header("Área de competencias")

    graficas_activas = [
        g for g in st.session_state.graficas
        if g["estatus"] in ["Pendiente", "En desarrollo"]
    ]

    if not graficas_activas:
        st.info("No hay gráficas pendientes o en desarrollo.")
    else:
        opciones = {
            f'{g["id"]} - {g["nombre_grafica"]} - {g["estatus"]}': g
            for g in graficas_activas
        }

        seleccion = st.selectbox("Selecciona una gráfica", list(opciones.keys()))
        grafica = opciones[seleccion]

        grafica["estatus"] = "En desarrollo"

        st.subheader(grafica["nombre_grafica"])

        st.write(f"**Reglamento:** {grafica['reglamento']}")
        st.write(f"**Modalidad:** {grafica['modalidad']}")
        st.write(f"**Categoría:** {grafica['categoria_edad']}")
        st.write(f"**Sexo:** {grafica['sexo']}")
        st.write(f"**Ronda actual:** {grafica['ronda_actual']}")

        st.divider()

        encuentros_pendientes = [
            (i, e) for i, e in enumerate(grafica["encuentros"])
            if not e["finalizado"]
        ]

        if not encuentros_pendientes:
            st.success("Todos los encuentros de esta ronda están finalizados.")
            avanzar_ronda_si_corresponde(grafica)
            st.rerun()

        opciones_encuentro = {
            f"Encuentro {i + 1}: {e['competidor_1']['nombre']} vs {e['competidor_2']['nombre'] if e['competidor_2'] else 'BYE'}": (i, e)
            for i, e in encuentros_pendientes
        }

        seleccion_encuentro = st.selectbox(
            "Selecciona encuentro",
            list(opciones_encuentro.keys())
        )

        indice, encuentro = opciones_encuentro[seleccion_encuentro]

        if grafica["modalidad"] == "Kumite":
            tablero_kumite(grafica, encuentro, indice)
        else:
            tablero_kata(grafica, encuentro, indice)

        st.divider()

        st.subheader("Historial de resultados")

        if grafica["historial"]:
            st.dataframe(pd.DataFrame(grafica["historial"]), use_container_width=True)
        else:
            st.info("Aún no hay resultados registrados.")


# =========================
# PREMIACIONES
# =========================

elif rol == "Premiaciones":
    st.header("Área de premiaciones")

    graficas_finalizadas = [
        g for g in st.session_state.graficas
        if g["estatus"] == "Finalizado"
    ]

    if not graficas_finalizadas:
        st.info("Todavía no hay gráficas finalizadas.")
    else:
        for grafica in graficas_finalizadas:
            st.subheader(grafica["nombre_grafica"])

            primer = grafica["ganadores"]["primer_lugar"]
            escuela_primer = obtener_escuela(grafica, primer)

            st.metric("Primer lugar", primer)
            st.caption(f"Escuela: {escuela_primer}")

            st.write(f"**Reglamento:** {grafica['reglamento']}")
            st.write(f"**Modalidad:** {grafica['modalidad']}")
            st.write(f"**Categoría:** {grafica['categoria_edad']}")
            st.write(f"**Sexo:** {grafica['sexo']}")

            st.divider()