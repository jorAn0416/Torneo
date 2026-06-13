import streamlit as st
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh
from supabase import create_client


st.set_page_config(
    page_title="Generador de Gráficas Karate",
    layout="wide"
)

if "graficas" not in st.session_state:
    st.session_state.graficas = []

if "competidores_temp" not in st.session_state:
    st.session_state.competidores_temp = []
    
# =========================
# BASE DE DATOS SUPABASE
# =========================

def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = conectar_supabase()


def convertir_grafica_a_fila(grafica):
    return {
        "nombre_grafica": grafica["nombre_grafica"],
        "reglamento": grafica["reglamento"],
        "modalidad": grafica["modalidad"],
        "categoria_edad": grafica["categoria_edad"],
        "sexo": grafica["sexo"],
        "estatus": grafica["estatus"],
        "ronda_actual": grafica["ronda_actual"],
        "competidores_json": grafica["competidores"],
        "encuentros_json": grafica["encuentros"],
        "historial_json": grafica["historial"],
        "ganadores_json": grafica["ganadores"],
        "fecha_creacion": grafica["fecha_creacion"]
    }

###################Grafica copiadora
def copiar_grafica_db(grafica_original, nuevo_nombre):

    nueva = grafica_original.copy()

    nueva["id"] = None

    nueva["nombre_grafica"] = nuevo_nombre

    nueva["estatus"] = "Pendiente"

    nueva["historial"] = []

    nueva["ganadores"] = {
        "primer_lugar": "",
        "segundo_lugar": "",
        "tercer_lugar": ""
    }

    nueva["encuentros"] = crear_encuentros(
        nueva["competidores"]
    )

    nuevo_id = guardar_grafica_db(
        nueva
    )

    nueva["id"] = nuevo_id
###################

#################################Grafica Exterminador
def eliminar_grafica_db(id_grafica):

    (
        supabase
        .table("graficas")
        .delete()
        .eq("id", id_grafica)
        .execute()
    )
#################################


def convertir_fila_a_grafica(fila):
    return {
        "id": fila["id"],
        "nombre_grafica": fila["nombre_grafica"],
        "reglamento": fila["reglamento"],
        "modalidad": fila["modalidad"],
        "categoria_edad": fila["categoria_edad"],
        "sexo": fila["sexo"],
        "estatus": fila["estatus"],
        "ronda_actual": fila["ronda_actual"],
        "competidores": fila["competidores_json"] or [],
        "encuentros": fila["encuentros_json"] or [],
        "historial": fila["historial_json"] or [],
        "ganadores": fila["ganadores_json"] or {
            "primer_lugar": "",
            "segundo_lugar": "",
            "tercer_lugar": ""
        },
        "fecha_creacion": fila["fecha_creacion"]
    }


def cargar_graficas_db():
    respuesta = (
        supabase
        .table("graficas")
        .select("*")
        .order("id", desc=False)
        .execute()
    )

    return [convertir_fila_a_grafica(fila) for fila in respuesta.data]


def guardar_grafica_db(grafica):
    fila = convertir_grafica_a_fila(grafica)

    respuesta = (
        supabase
        .table("graficas")
        .insert(fila)
        .execute()
    )

    return respuesta.data[0]["id"]


def actualizar_grafica_db(grafica):
    fila = convertir_grafica_a_fila(grafica)

    (
        supabase
        .table("graficas")
        .update(fila)
        .eq("id", grafica["id"])
        .execute()
    )
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
# FUNCIONES GENERALES
# =========================

def registrar_competidor(nombre, escuela):
    competidor = {
        "nombre": nombre,
        "escuela": escuela
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


def crear_grafica(nombre_grafica, reglamento, modalidad, categoria_edad, sexo):
    competidores = st.session_state.competidores_temp.copy()

    nueva_grafica = {
        "id": None,
        "nombre_grafica": nombre_grafica,
        "reglamento": reglamento,
        "modalidad": modalidad,
        "categoria_edad": categoria_edad,
        "sexo": sexo,
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

    nuevo_id = guardar_grafica_db(nueva_grafica)
    st.session_state.graficas = cargar_graficas_db()
    nueva_grafica["id"] = nuevo_id

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

#################################
def cargar_como_plantilla(grafica):

    st.session_state.competidores_temp = (
        grafica["competidores"].copy()
    )

    st.session_state.plantilla_nombre = (
        grafica["nombre_grafica"] + "_COPIA"
    )

    st.session_state.plantilla_reglamento = (
        grafica["reglamento"]
    )

    st.session_state.plantilla_modalidad = (
        grafica["modalidad"]
    )

    st.session_state.plantilla_categoria = (
        grafica["categoria_edad"]
    )

    st.session_state.plantilla_sexo = (
        grafica["sexo"]
    )

#################################

################################
def guardar_resultados_finales(grafica):

    premiados = [

        (
            grafica["ganadores"]["primer_lugar"],
            1,
            3
        ),

        (
            grafica["ganadores"]["segundo_lugar"],
            2,
            2
        ),

        (
            grafica["ganadores"]["tercer_lugar"],
            3,
            1
        )

    ]

    for nombre, lugar, puntos in premiados:

        if not nombre:
            continue

        escuela = obtener_escuela(
            grafica,
            nombre
        )

        supabase.table(
            "resultados_finales"
        ).insert({

            "competidor": nombre,
            "escuela": escuela,
            "lugar": lugar,
            "grafica": grafica["nombre_grafica"],
            "reglamento": grafica["reglamento"],
            "modalidad": grafica["modalidad"],
            "categoria": grafica["categoria_edad"]

        }).execute()

        actualizar_puntos_escuela(
            escuela,
            puntos
        )
################################

####################################
def actualizar_puntos_escuela(
    escuela,
    puntos
):

    existente = (
        supabase
        .table("puntos_escuelas")
        .select("*")
        .eq("escuela", escuela)
        .execute()
    )

    if existente.data:

        actual = existente.data[0]["puntos"]

        (
            supabase
            .table("puntos_escuelas")
            .update({
                "puntos": actual + puntos
            })
            .eq("escuela", escuela)
            .execute()
        )

    else:

        (
            supabase
            .table("puntos_escuelas")
            .insert({
                "escuela": escuela,
                "puntos": puntos
            })
            .execute()
        )
####################################

####################################
def eliminar_grafica(id_grafica):

    (
        supabase
        .table("graficas")
        .delete()
        .eq("id", id_grafica)
        .execute()
    )
####################################

# =========================
# INTERFAZ PRINCIPAL
# =========================
st.session_state.graficas = cargar_graficas_db()
st.title("Sistema de Organización de Gráficas - Karate")

rol = st.sidebar.selectbox(
    "Selecciona el tipo de usuario",
    [
        "Registro",
        "Premiaciones",
        "Resultados Finales"
    ]
)


# =========================
# REGISTRO
# =========================

if rol == "Registro":
    st.header("Registro de competidores y creación de gráfica")

    col1, col2, col3 = st.columns(3)

    with col1:

        nombre_grafica = st.text_input(
            "Nombre de la gráfica",
            value=st.session_state.get(
                "plantilla_nombre",
                ""
            )
        )
    
        reglamento = st.selectbox(
            "Reglamento",
            ["WUKF", "WKF"],
            index=0 if st.session_state.get(
                "plantilla_reglamento",
                "WUKF"
            ) == "WUKF" else 1
        )

    with col2:

        modalidad = st.selectbox(
            "Modalidad",
            ["Kata", "Kumite"],
            index=0 if st.session_state.get(
                "plantilla_modalidad",
                "Kata"
            ) == "Kata" else 1
        )
    
        sexo = st.selectbox(
            "Sexo",
            ["Masculino", "Femenino", "Mixto"],
            index=[
                "Masculino",
                "Femenino",
                "Mixto"
            ].index(
                st.session_state.get(
                    "plantilla_sexo",
                    "Masculino"
                )
            )
        )

    with col3:
        categoria_edad = st.text_input(
        "Categoría de edad",
        value=st.session_state.get(
            "plantilla_categoria",
            ""
        )
    )

    st.divider()

    st.subheader("Agregar competidor")

    col1, col2, col3 = st.columns(3)

    with col1:
        nombre = st.text_input("Nombre del competidor")

    with col2:
        escuela = st.text_input("Escuela")

    with col3:
        agregar = st.button("Agregar competidor")

    if agregar:
        if nombre and escuela:
            registrar_competidor(nombre, escuela)
            st.success(f"Competidor {nombre} agregado.")
        else:
            st.warning("Completa nombre y escuela.")

    st.subheader("Competidores agregados")

    if st.session_state.competidores_temp:
        st.dataframe(pd.DataFrame(st.session_state.competidores_temp), use_container_width=True)
    else:
        st.info("Todavía no hay competidores agregados.")
    
    ###################Elimina competidores de lista
    if st.session_state.competidores_temp:

        indice_borrar = st.selectbox(
            "Eliminar competidor",
            range(len(st.session_state.competidores_temp)),
            format_func=lambda i:
                st.session_state.competidores_temp[i]["nombre"]
        )
    
        if st.button("Eliminar competidor"):
    
            eliminado = (
                st.session_state
                .competidores_temp
                .pop(indice_borrar)
            )
    
            st.success(
                f'Se eliminó {eliminado["nombre"]}'
            )
    
            st.rerun()
    #####################
    

    if st.button("Crear gráfica"):
        if nombre_grafica and categoria_edad and len(st.session_state.competidores_temp) > 0:
    
            crear_grafica(
                nombre_grafica,
                reglamento,
                modalidad,
                categoria_edad,
                sexo
            )
    
            # LIMPIAR DATOS DE LA PLANTILLA
            for clave in [
                "plantilla_nombre",
                "plantilla_reglamento",
                "plantilla_modalidad",
                "plantilla_categoria",
                "plantilla_sexo",
            ]:
                if clave in st.session_state:
                    del st.session_state[clave]
    
            st.success(
                f"La gráfica {nombre_grafica} fue creada con estatus Pendiente."
            )
    
            st.rerun()
    
        else:
            st.warning(
                "Falta nombre de gráfica, categoría de edad o competidores."
            )

    st.divider()

    st.subheader("Lista general de gráficas")
    
    ##################
    st.divider()

    st.subheader(
        "Usar gráfica existente como plantilla"
    )
    
    if st.session_state.graficas:
    
        opciones = {
            f'{g["id"]} - {g["nombre_grafica"]}': g
            for g in st.session_state.graficas
        }
    
        seleccion = st.selectbox(
            "Selecciona gráfica",
            list(opciones.keys())
        )
    
        if st.button("Cargar plantilla"):
    
            cargar_como_plantilla(
                opciones[seleccion]
            )
    
            st.success(
                "Plantilla cargada."
            )
    
            st.rerun()
    ##################

    if st.session_state.graficas:
        st.dataframe(obtener_dataframe_graficas(), use_container_width=True)
    else:
        st.info("Aún no hay gráficas creadas.")
        
    #################################Copiadora
    st.subheader("Copiar gráfica")

    if st.session_state.graficas:
    
        opciones = {
            g["nombre_grafica"]: g
            for g in st.session_state.graficas
        }
    
        seleccion = st.selectbox(
            "Selecciona gráfica",
            list(opciones.keys())
        )
    
        nuevo_nombre = st.text_input(
            "Nombre de la copia"
        )
    
        if st.button("Copiar gráfica"):
    
            copiar_grafica_db(
                opciones[seleccion],
                nuevo_nombre
            )
    
            st.success(
                "Gráfica copiada"
            )

            st.rerun()
    #################################
    
    #################################ElininarGraficas
    st.subheader("Eliminar gráfica")

    if st.session_state.graficas:
    
        opciones = {
            f'{g["id"]} - {g["nombre_grafica"]}': g
            for g in st.session_state.graficas
        }
    
        seleccion = st.selectbox(
            "Selecciona gráfica a eliminar",
            list(opciones.keys())
        )
    
        if st.button("Eliminar gráfica"):
    
            eliminar_grafica_db(
                opciones[seleccion]["id"]
            )
    
            st.success(
                "Gráfica eliminada"
            )
    
            st.rerun()
    #################################



# =========================
# PREMIACIONES
# =========================

elif rol == "Premiaciones":
    st_autorefresh(interval=3000, key="refresh_general")
    
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
    
    if st.button(
        f"Premiación entregada - {grafica['id']}"
    ):
    
        guardar_resultados_finales(
            grafica
        )
    
        eliminar_grafica(
            grafica["id"]
        )
    
        st.success(
            "Resultados enviados al historial."
        )
    
        st.rerun()
        
#####Resultados Finales#########
    
elif rol == "Resultados Finales":

    st.header(
        "Resultados Finales"
    )

    resultados = (
        supabase
        .table("resultados_finales")
        .select("*")
        .execute()
    )

    escuelas = (
        supabase
        .table("puntos_escuelas")
        .select("*")
        .execute()
    )

    st.subheader(
        "Medallistas"
    )

    st.dataframe(
        pd.DataFrame(
            resultados.data
        ),
        use_container_width=True
    )

    st.subheader(
        "Ranking de Escuelas"
    )

    ranking = pd.DataFrame(
        escuelas.data
    )

    if not ranking.empty:

        ranking = ranking.sort_values(
            "puntos",
            ascending=False
        )

    st.dataframe(
        ranking,
        use_container_width=True
    )
