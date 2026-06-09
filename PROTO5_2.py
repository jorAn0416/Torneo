import streamlit as st
import pandas as pd
from datetime import datetime
import random
import time
from streamlit_autorefresh import st_autorefresh


st.set_page_config(
    page_title="Generador de Gráficas Karate",
    layout="wide"
)

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
            "perdedor": None,
            "finalizado": False
        })

    if len(lista) == 1:
        encuentros.append({
            "competidor_1": lista[0],
            "competidor_2": None,
            "resultado": "BYE",
            "ganador": lista[0],
            "perdedor": None,
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
        ganadores = [
            e["ganador"]
            for e in encuentros
            if e["ganador"] is not None
        ]

        # Si ya solo queda un ganador, terminó la gráfica
        if len(ganadores) == 1:
            grafica["estatus"] = "Finalizado"

            # El primer lugar sale del último resultado real registrado
            if grafica["historial"]:
                ultima_ronda = max(r["ronda"] for r in grafica["historial"])

                resultados_ultima_ronda = [
                    r for r in grafica["historial"]
                    if r["ronda"] == ultima_ronda
                ]

                final = resultados_ultima_ronda[-1]

                grafica["ganadores"]["primer_lugar"] = final.get("ganador", "")
                grafica["ganadores"]["segundo_lugar"] = final.get("perdedor", "")

            else:
                grafica["ganadores"]["primer_lugar"] = ganadores[0]["nombre"]

            return

        grafica["ronda_actual"] += 1
        grafica["encuentros"] = crear_encuentros(ganadores)


def calcular_premiacion(grafica):
    historial = grafica["historial"]

    if not historial:
        return "", "", ""

    ultima_ronda = max(r["ronda"] for r in historial)

    final = [
        r for r in historial
        if r["ronda"] == ultima_ronda
    ][-1]

    primer = final.get("ganador", "")
    segundo = final.get("perdedor", "")

    excluidos = [primer, segundo]

    acumulados = {}

    for competidor in grafica["competidores"]:
        acumulados[competidor["nombre"]] = {
            "banderas": 0,
            "puntos": 0,
            "faltas": 0
        }

    for r in historial:
        c1 = r.get("competidor_1")
        c2 = r.get("competidor_2")

        if c1 and c1 not in acumulados:
            acumulados[c1] = {"banderas": 0, "puntos": 0, "faltas": 0}

        if c2 and c2 not in acumulados:
            acumulados[c2] = {"banderas": 0, "puntos": 0, "faltas": 0}

        if grafica["modalidad"] == "Kata":
            if c1:
                acumulados[c1]["banderas"] += r.get("banderas_rojo", 0)

            if c2:
                acumulados[c2]["banderas"] += r.get("banderas_azul", 0)
                acumulados[c2]["banderas"] += r.get("banderas_blanco", 0)

        elif grafica["modalidad"] == "Kumite":
            if c1:
                acumulados[c1]["puntos"] += r.get("puntos_1", 0)
                acumulados[c1]["faltas"] += r.get("faltas_1", 0)

            if c2:
                acumulados[c2]["puntos"] += r.get("puntos_2", 0)
                acumulados[c2]["faltas"] += r.get("faltas_2", 0)

    candidatos_tercero = {
        nombre: datos
        for nombre, datos in acumulados.items()
        if nombre not in excluidos
    }

    tercero = ""

    if candidatos_tercero:
        if grafica["modalidad"] == "Kata":
            tercero = max(
                candidatos_tercero,
                key=lambda nombre: candidatos_tercero[nombre]["banderas"]
            )

        elif grafica["modalidad"] == "Kumite":
            tercero = sorted(
                candidatos_tercero,
                key=lambda nombre: (
                    -candidatos_tercero[nombre]["puntos"],
                    candidatos_tercero[nombre]["faltas"]
                )
            )[0]

    grafica["ganadores"]["primer_lugar"] = primer
    grafica["ganadores"]["segundo_lugar"] = segundo
    grafica["ganadores"]["tercer_lugar"] = tercero

    return primer, segundo, tercero


# =========================
# CRONÓMETRO
# =========================

def cronometro_streamlit(estado_key, tiempo_inicial_segundos=120):
    timer_key = f"timer_{estado_key}"

    if timer_key not in st.session_state:
        st.session_state[timer_key] = {
            "segundos_restantes": tiempo_inicial_segundos,
            "corriendo": False,
            "ultimo_tick": time.time()
        }

    timer = st.session_state[timer_key]

    if timer["corriendo"]:
        st_autorefresh(interval=1000, key=f"refresh_{estado_key}")

        ahora = time.time()
        diferencia = int(ahora - timer["ultimo_tick"])

        if diferencia >= 1:
            timer["segundos_restantes"] = max(0, timer["segundos_restantes"] - diferencia)
            timer["ultimo_tick"] = ahora

        if timer["segundos_restantes"] == 0:
            timer["corriendo"] = False

    minutos = timer["segundos_restantes"] // 60
    segundos = timer["segundos_restantes"] % 60

    st.markdown(
        f"""
        <div style='background-color:black; color:white; text-align:center; padding:20px; border-radius:12px;'>
            <h1 style='font-size:70px;'>{minutos:02d}:{segundos:02d}</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Iniciar", key=f"iniciar_{estado_key}"):
            timer["corriendo"] = True
            timer["ultimo_tick"] = time.time()
            st.rerun()

    with col2:
        if st.button("Pausar", key=f"pausar_{estado_key}"):
            timer["corriendo"] = False
            st.rerun()

    with col3:
        if st.button("Reiniciar", key=f"reiniciar_{estado_key}"):
            timer["segundos_restantes"] = tiempo_inicial_segundos
            timer["corriendo"] = False
            timer["ultimo_tick"] = time.time()
            st.rerun()

    return timer["segundos_restantes"]


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
        fondo_1 = "#e53935"
        fondo_2 = "#f5f5f5"
        texto_1 = "white"
        texto_2 = "black"

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
        fondo_1 = "#e53935"
        fondo_2 = "#1e88e5"
        texto_1 = "white"
        texto_2 = "white"

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

    st.markdown(f"## Encuentro Kumite {indice + 1}")

    col_rojo, col_centro, col_azul = st.columns([4, 2, 4])

    with col_rojo:
        st.markdown(
            f"""
            <div style='background-color:{fondo_1}; padding:20px; border-radius:12px; text-align:center;'>
                <h1 style='color:{texto_1};'>{color_1}</h1>
                <h2 style='color:{texto_1};'>{c1["nombre"]}</h2>
                <h4 style='color:{texto_1};'>{c1["escuela"]}</h4>
                <h1 style='color:{texto_1}; font-size:90px;'>{estado["puntos_1"]}</h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.subheader("Puntos")

        for nombre_punto, valor in puntos_validos.items():
            col_mas, col_menos = st.columns(2)

            with col_mas:
                if st.button(f"+{valor} {nombre_punto}", key=f"p1_mas_{nombre_punto}_{estado_key}"):
                    estado["puntos_1"] += valor
                    st.rerun()

            with col_menos:
                if st.button(f"-{valor} {nombre_punto}", key=f"p1_menos_{nombre_punto}_{estado_key}"):
                    estado["puntos_1"] = max(0, estado["puntos_1"] - valor)
                    st.rerun()

        st.subheader("Faltas")

        if reglamento == "WUKF":
            st.write(f"Tipo 1: {estado['faltas_tipo1_1']} / 3")
            st.write(f"Tipo 2: {estado['faltas_tipo2_1']} / 4")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("+ Tipo 1", key=f"t1_mas_1_{estado_key}"):
                    if estado["faltas_tipo1_1"] < 3:
                        estado["faltas_tipo1_1"] += 1
                        st.rerun()

                if st.button("- Tipo 1", key=f"t1_menos_1_{estado_key}"):
                    estado["faltas_tipo1_1"] = max(0, estado["faltas_tipo1_1"] - 1)
                    st.rerun()

            with col2:
                if st.button("+ Tipo 2", key=f"t2_mas_1_{estado_key}"):
                    if estado["faltas_tipo2_1"] < 4:
                        estado["faltas_tipo2_1"] += 1
                        st.rerun()

                if st.button("- Tipo 2", key=f"t2_menos_1_{estado_key}"):
                    estado["faltas_tipo2_1"] = max(0, estado["faltas_tipo2_1"] - 1)
                    st.rerun()

            estado["faltas_1"] = estado["faltas_tipo1_1"] + estado["faltas_tipo2_1"]

        else:
            st.write(f"Faltas: {estado['faltas_1']} / 5")

            col_mas, col_menos = st.columns(2)

            with col_mas:
                if st.button("+ Falta", key=f"f1_mas_{estado_key}"):
                    if estado["faltas_1"] < 5:
                        estado["faltas_1"] += 1
                        st.rerun()

            with col_menos:
                if st.button("- Falta", key=f"f1_menos_{estado_key}"):
                    estado["faltas_1"] = max(0, estado["faltas_1"] - 1)
                    st.rerun()

    with col_centro:
        tiempo_config = st.number_input(
            "Tiempo en segundos",
            min_value=30,
            max_value=600,
            value=120,
            step=30,
            key=f"tiempo_config_{estado_key}"
        )

        cronometro_streamlit(estado_key, tiempo_config)

        st.markdown(
            f"""
            <div style='background-color:#222; color:white; text-align:center; padding:20px; border-radius:12px; margin-top:10px;'>
                <h1>{estado["puntos_1"]} - {estado["puntos_2"]}</h1>
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
        st.markdown(
            f"""
            <div style='background-color:{fondo_2}; padding:20px; border-radius:12px; text-align:center; border:2px solid black;'>
                <h1 style='color:{texto_2};'>{color_2}</h1>
                <h2 style='color:{texto_2};'>{c2["nombre"]}</h2>
                <h4 style='color:{texto_2};'>{c2["escuela"]}</h4>
                <h1 style='color:{texto_2}; font-size:90px;'>{estado["puntos_2"]}</h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.subheader("Puntos")

        for nombre_punto, valor in puntos_validos.items():
            col_mas, col_menos = st.columns(2)

            with col_mas:
                if st.button(f"+{valor} {nombre_punto}", key=f"p2_mas_{nombre_punto}_{estado_key}"):
                    estado["puntos_2"] += valor
                    st.rerun()

            with col_menos:
                if st.button(f"-{valor} {nombre_punto}", key=f"p2_menos_{nombre_punto}_{estado_key}"):
                    estado["puntos_2"] = max(0, estado["puntos_2"] - valor)
                    st.rerun()

        st.subheader("Faltas")

        if reglamento == "WUKF":
            st.write(f"Tipo 1: {estado['faltas_tipo1_2']} / 3")
            st.write(f"Tipo 2: {estado['faltas_tipo2_2']} / 4")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("+ Tipo 1", key=f"t1_mas_2_{estado_key}"):
                    if estado["faltas_tipo1_2"] < 3:
                        estado["faltas_tipo1_2"] += 1
                        st.rerun()

                if st.button("- Tipo 1", key=f"t1_menos_2_{estado_key}"):
                    estado["faltas_tipo1_2"] = max(0, estado["faltas_tipo1_2"] - 1)
                    st.rerun()

            with col2:
                if st.button("+ Tipo 2", key=f"t2_mas_2_{estado_key}"):
                    if estado["faltas_tipo2_2"] < 4:
                        estado["faltas_tipo2_2"] += 1
                        st.rerun()

                if st.button("- Tipo 2", key=f"t2_menos_2_{estado_key}"):
                    estado["faltas_tipo2_2"] = max(0, estado["faltas_tipo2_2"] - 1)
                    st.rerun()

            estado["faltas_2"] = estado["faltas_tipo1_2"] + estado["faltas_tipo2_2"]

        else:
            st.write(f"Faltas: {estado['faltas_2']} / 5")

            col_mas, col_menos = st.columns(2)

            with col_mas:
                if st.button("+ Falta", key=f"f2_mas_{estado_key}"):
                    if estado["faltas_2"] < 5:
                        estado["faltas_2"] += 1
                        st.rerun()

            with col_menos:
                if st.button("- Falta", key=f"f2_menos_{estado_key}"):
                    estado["faltas_2"] = max(0, estado["faltas_2"] - 1)
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

    if ganador_automatico:
        ganador_nombre = ganador_automatico["nombre"]
        st.info(f"Ganador detectado: {ganador_nombre}")
    else:
        ganador_nombre = st.selectbox(
            "Selecciona ganador",
            [c1["nombre"], c2["nombre"]],
            key=f"ganador_manual_{estado_key}"
        )

    if st.button("Registrar resultado Kumite", key=f"registrar_kumite_{estado_key}"):
        ganador = c1 if ganador_nombre == c1["nombre"] else c2
        perdedor = c2 if ganador_nombre == c1["nombre"] else c1

        encuentro["resultado"] = {
            "tipo": "Kumite",
            "ronda": grafica["ronda_actual"],
            "competidor_1": c1["nombre"],
            "competidor_2": c2["nombre"],
            "puntos_1": estado["puntos_1"],
            "puntos_2": estado["puntos_2"],
            "faltas_1": estado["faltas_1"],
            "faltas_2": estado["faltas_2"],
            "faltas_tipo1_1": estado["faltas_tipo1_1"],
            "faltas_tipo2_1": estado["faltas_tipo2_1"],
            "faltas_tipo1_2": estado["faltas_tipo1_2"],
            "faltas_tipo2_2": estado["faltas_tipo2_2"],
            "ganador": ganador["nombre"],
            "perdedor": perdedor["nombre"]
        }

        encuentro["ganador"] = ganador
        encuentro["perdedor"] = perdedor
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
    reglamento = grafica["reglamento"]

    color_2_nombre = "Azul" if reglamento == "WKF" else "Blanco"
    color_2_fondo = "#1e88e5" if reglamento == "WKF" else "#f5f5f5"
    color_2_texto = "white" if reglamento == "WKF" else "black"

    estado_key = f"kata_{grafica['id']}_{grafica['ronda_actual']}_{indice}"

    if estado_key not in st.session_state:
        st.session_state[estado_key] = {
            "banderas_1": 0,
            "banderas_2": 0
        }

    estado = st.session_state[estado_key]
    total_banderas_usadas = estado["banderas_1"] + estado["banderas_2"]

    st.markdown(f"## Encuentro Kata {indice + 1}")
    st.info(f"Banderas disponibles: {banderas} | Banderas usadas: {total_banderas_usadas}")

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

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("+ Bandera Rojo", key=f"mas_bandera_1_{estado_key}"):
                if estado["banderas_1"] + estado["banderas_2"] < banderas:
                    estado["banderas_1"] += 1
                    st.rerun()
                else:
                    st.warning("Ya se usaron todas las banderas disponibles.")

        with col_b:
            if st.button("- Bandera Rojo", key=f"menos_bandera_1_{estado_key}"):
                if estado["banderas_1"] > 0:
                    estado["banderas_1"] -= 1
                    st.rerun()

    with col2:
        st.markdown(
            f"""
            <div style='background-color:{color_2_fondo}; padding:20px; border-radius:12px; text-align:center; border:2px solid black;'>
                <h1 style='color:{color_2_texto};'>{color_2_nombre}</h1>
                <h2 style='color:{color_2_texto};'>{c2["nombre"]}</h2>
                <h4 style='color:{color_2_texto};'>{c2["escuela"]}</h4>
                <h1 style='color:{color_2_texto}; font-size:80px;'>{estado["banderas_2"]}</h1>
                <h3 style='color:{color_2_texto};'>Banderas</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button(f"+ Bandera {color_2_nombre}", key=f"mas_bandera_2_{estado_key}"):
                if estado["banderas_1"] + estado["banderas_2"] < banderas:
                    estado["banderas_2"] += 1
                    st.rerun()
                else:
                    st.warning("Ya se usaron todas las banderas disponibles.")

        with col_b:
            if st.button(f"- Bandera {color_2_nombre}", key=f"menos_bandera_2_{estado_key}"):
                if estado["banderas_2"] > 0:
                    estado["banderas_2"] -= 1
                    st.rerun()

    total_banderas_usadas = estado["banderas_1"] + estado["banderas_2"]

    if total_banderas_usadas < banderas:
        st.warning("Todavía faltan banderas por registrar.")

    ganador = None

    if estado["banderas_1"] > estado["banderas_2"]:
        ganador = c1
    elif estado["banderas_2"] > estado["banderas_1"]:
        ganador = c2

    if ganador:
        st.success(f"Ganador provisional: {ganador['nombre']}")

    if st.button("Registrar resultado Kata", key=f"registrar_kata_{estado_key}"):
        if total_banderas_usadas == banderas and ganador:
            perdedor = c2 if ganador == c1 else c1

            encuentro["resultado"] = {
                "tipo": "Kata",
                "ronda": grafica["ronda_actual"],
                "competidor_1": c1["nombre"],
                "competidor_2": c2["nombre"],
                "banderas_rojo": estado["banderas_1"],
                f"banderas_{color_2_nombre.lower()}": estado["banderas_2"],
                "ganador": ganador["nombre"],
                "perdedor": perdedor["nombre"]
            }

            encuentro["ganador"] = ganador
            encuentro["perdedor"] = perdedor
            encuentro["finalizado"] = True
            grafica["historial"].append(encuentro["resultado"])

            st.success("Resultado de kata registrado.")
            avanzar_ronda_si_corresponde(grafica)
            st.rerun()
        else:
            st.warning("Debes registrar exactamente todas las banderas y debe existir un ganador.")


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

    st.subheader("Competidores agregados")

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

            primer, segundo, tercero = calcular_premiacion(grafica)

            escuela_primer = obtener_escuela(grafica, primer) if primer else ""
            escuela_segundo = obtener_escuela(grafica, segundo) if segundo else ""
            escuela_tercero = obtener_escuela(grafica, tercero) if tercero else ""

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Primer lugar", primer if primer else "No definido")
                if escuela_primer:
                    st.caption(f"Escuela: {escuela_primer}")

            with col2:
                st.metric("Segundo lugar", segundo if segundo else "No definido")
                if escuela_segundo:
                    st.caption(f"Escuela: {escuela_segundo}")

            with col3:
                st.metric("Tercer lugar", tercero if tercero else "No definido")
                if escuela_tercero:
                    st.caption(f"Escuela: {escuela_tercero}")

            st.write(f"**Reglamento:** {grafica['reglamento']}")
            st.write(f"**Modalidad:** {grafica['modalidad']}")
            st.write(f"**Categoría:** {grafica['categoria_edad']}")
            st.write(f"**Sexo:** {grafica['sexo']}")





from supabase import create_client
import streamlit as st

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

st.write("Conectado correctamente")
