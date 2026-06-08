import streamlit as st
import pandas as pd
from datetime import datetime

# =========================
# CONFIGURACIÓN INICIAL
# =========================

st.set_page_config(
    page_title="Gestor de Torneos de Karate",
    layout="wide"
)

if "graficas" not in st.session_state:
    st.session_state.graficas = []

if "competidores_temp" not in st.session_state:
    st.session_state.competidores_temp = []


# =========================
# FUNCIONES
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


def crear_grafica(nombre_grafica, reglamento, modalidad, categoria_edad, sexo):
    nueva_grafica = {
        "id": len(st.session_state.graficas) + 1,
        "nombre_grafica": nombre_grafica,
        "reglamento": reglamento,
        "modalidad": modalidad,
        "categoria_edad": categoria_edad,
        "sexo": sexo,
        "competidores": st.session_state.competidores_temp.copy(),
        "estatus": "Pendiente",
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
            "Estatus": grafica["estatus"]
        })

    return pd.DataFrame(datos)


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
# ROL: REGISTRO
# =========================

if rol == "Registro":
    st.header("Registro de competidores y creación de gráfica")

    st.subheader("Datos de la gráfica")

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

    st.subheader("Competidores agregados a esta gráfica")

    if st.session_state.competidores_temp:
        st.dataframe(pd.DataFrame(st.session_state.competidores_temp), use_container_width=True)
    else:
        st.info("Todavía no hay competidores agregados.")

    if st.button("Crear gráfica"):
        if nombre_grafica and categoria_edad and len(st.session_state.competidores_temp) > 0:
            crear_grafica(nombre_grafica, reglamento, modalidad, categoria_edad, sexo)
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
# ROL: ÁREA DE COMPETENCIAS
# =========================

elif rol == "Área de competencias":
    st.header("Área de competencias")

    graficas_pendientes = [
        g for g in st.session_state.graficas
        if g["estatus"] in ["Pendiente", "En desarrollo"]
    ]

    if not graficas_pendientes:
        st.info("No hay gráficas pendientes o en desarrollo.")
    else:
        opciones = {
            f'{g["id"]} - {g["nombre_grafica"]} - {g["estatus"]}': g
            for g in graficas_pendientes
        }

        seleccion = st.selectbox("Selecciona una gráfica", list(opciones.keys()))
        grafica = opciones[seleccion]

        st.subheader(grafica["nombre_grafica"])

        st.write(f"Reglamento: **{grafica['reglamento']}**")
        st.write(f"Modalidad: **{grafica['modalidad']}**")
        st.write(f"Categoría: **{grafica['categoria_edad']}**")
        st.write(f"Sexo: **{grafica['sexo']}**")
        st.write(f"Estatus actual: **{grafica['estatus']}**")

        st.subheader("Competidores")

        st.dataframe(pd.DataFrame(grafica["competidores"]), use_container_width=True)

        if st.button("Marcar como En desarrollo"):
            grafica["estatus"] = "En desarrollo"
            st.success("La gráfica ahora está en desarrollo.")
            st.rerun()

        st.divider()

        st.subheader("Registrar ganadores")

        nombres_competidores = [c["nombre"] for c in grafica["competidores"]]

        primer_lugar = st.selectbox("Primer lugar", [""] + nombres_competidores)
        segundo_lugar = st.selectbox("Segundo lugar", [""] + nombres_competidores)
        tercer_lugar = st.selectbox("Tercer lugar", [""] + nombres_competidores)

        if st.button("Finalizar gráfica"):
            if primer_lugar:
                grafica["ganadores"]["primer_lugar"] = primer_lugar
                grafica["ganadores"]["segundo_lugar"] = segundo_lugar
                grafica["ganadores"]["tercer_lugar"] = tercer_lugar
                grafica["estatus"] = "Finalizado"

                st.success("La gráfica fue finalizada correctamente.")
                st.rerun()
            else:
                st.warning("Debes registrar al menos el primer lugar.")


# =========================
# ROL: PREMIACIONES
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

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Primer lugar", grafica["ganadores"]["primer_lugar"])

            with col2:
                st.metric("Segundo lugar", grafica["ganadores"]["segundo_lugar"])

            with col3:
                st.metric("Tercer lugar", grafica["ganadores"]["tercer_lugar"])

            st.write(f"Reglamento: **{grafica['reglamento']}**")
            st.write(f"Modalidad: **{grafica['modalidad']}**")
            st.write(f"Categoría: **{grafica['categoria_edad']}**")
            st.write(f"Sexo: **{grafica['sexo']}**")

            st.divider()

