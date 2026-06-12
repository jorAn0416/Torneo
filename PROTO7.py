import streamlit as st
import pandas as pd
from datetime import datetime
import random
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

def registrar_competidor(nombre, escuela):
    competidor = {
        "nombre": nombre,
        "escuela": escuela
    }
    st.session_state.competidores_temp.append(competidor)
    
def copiar_grafica(grafica_original, nuevo_nombre):

    nueva = grafica_original.copy()

    nueva["id"] = len(st.session_state.graficas) + 1

    nueva["nombre_grafica"] = nuevo_nombre

    nueva["estatus"] = "Pendiente"

    nueva["ganadores"] = {
        "primer_lugar": "",
        "segundo_lugar": "",
        "tercer_lugar": ""
    }

    st.session_state.graficas.append(nueva)


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
# INTERFAZ PRINCIPAL
# =========================

st.title("TOURNAMENT MANAGER")

rol = st.sidebar.selectbox(
    "Selecciona el tipo de usuario",
    [
        "Registro",
        "Premiaciones"
    ]
)


# =========================
# REGISTRO
# =========================

if rol == "Registro":
    st.header("Registro de competidores y creación de gráfica")

    col1, col2 = st.columns(2)

    with col1:
        nombre_grafica = st.text_input("Nombre de la gráfica", placeholder="Ejemplo: Grafica1")
        reglamento = st.selectbox("Reglamento", ["WUKF", "WKF"])

    with col2:
        modalidad = st.selectbox("Modalidad", ["Kata", "Kumite"])
        sexo = st.selectbox("Sexo", ["Masculino", "Femenino", "Mixto"])
        
    st.divider()

    st.subheader("Agregar competidor")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        nombre = st.text_input("Nombre del competidor")

    with col2:
        escuela = st.text_input("Escuela")

    with col4:
        agregar = st.button("Agregar competidor")
    

    

    if agregar:
        if nombre and escuela:
            registrar_competidor(nombre, escuela)
            st.success(f"Competidor {nombre} agregado.")
        else:
            st.warning("Completa nombre y escuela")

    st.subheader("Competidores agregados")

    if st.session_state.competidores_temp:
        st.dataframe(pd.DataFrame(st.session_state.competidores_temp), use_container_width=True)
    else:
        st.info("Todavía no hay competidores agregados.")
    ###Borra lineas
    if st.session_state.competidores_temp:

        indice_borrar = st.selectbox(
            "Eliminar competidor",
            range(len(st.session_state.competidores_temp)),
            format_func=lambda i:
                st.session_state.competidores_temp[i]["nombre"]
        )

        if st.button("Eliminar seleccionado"):

            eliminado = st.session_state.competidores_temp.pop(indice_borrar)

            st.success(
                f'Se eliminó {eliminado["nombre"]}'
            )

            st.rerun()
    ###
    
    #COPIA GRAFICA
    st.subheader("Copiar gráfica existente")
    if st.session_state.graficas:

        opciones = {
                g["nombre_grafica"]: g
                for g in st.session_state.graficas
        }
        
        seleccion = st.selectbox(
            "Selecciona una gráfica",
            list(opciones.keys())
        )
        
        nuevo_nombre = st.text_input(
            "Nombre de la copia"
            )
        
        if st.button("Copiar gráfica"):
        
            copiar_grafica(
                opciones[seleccion],
                nuevo_nombre
            )
        
            st.success(
                "Gráfica copiada correctamente"
            )
        
            st.rerun()
    ####
    st.subheader("Mandar a Tablero")
    if st.button("Mandar a Tablero"):
        if nombre_grafica and len(st.session_state.competidores_temp) > 0:
            crear_grafica(
                nombre_grafica,
                reglamento,
                modalidad,
                sexo
            )
            st.success(f"La gráfica {nombre_grafica} fue creada con estatus Pendiente.")
        else:
            st.warning("Falta nombre de gráfica, categoría o competidores.")

    st.divider()

    st.subheader("Lista general de gráficas")

    if st.session_state.graficas:
        st.dataframe(obtener_dataframe_graficas(), use_container_width=True)
    else:
        st.info("Aún no hay gráficas creadas.")


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
