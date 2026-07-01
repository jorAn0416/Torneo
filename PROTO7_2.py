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
        "area": grafica.get("area", "Área 1"),
        "tipo_competencia": grafica.get("tipo_competencia", "eliminacion_directa"),  # ← NUEVO
        "estatus": grafica["estatus"],
        "ronda_actual": grafica["ronda_actual"],
        "competidores_json": grafica["competidores"],
        "encuentros_json": grafica["encuentros"],
        "esperan_json": grafica.get("esperan", []),
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
        "tercero_1": "",
        "tercero_2": ""
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
        "area": fila.get("area", "Área 1"),
        "tipo_competencia": fila.get("tipo_competencia", "eliminacion_directa"),  # ← NUEVO
        "estatus": fila["estatus"],
        "ronda_actual": fila["ronda_actual"],
        "competidores": fila["competidores_json"] or [],
        "encuentros": fila["encuentros_json"] or [],
        "esperan": fila.get("esperan_json", []),
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
    """
    Calcula la premiación según el tipo de competencia.
    - Eliminación directa: busca perdedores de semifinal
    - Round Robin: usa la tabla de posiciones
    """
    # Si es Round Robin, obtener de la tabla de posiciones
    if grafica.get("tipo_competencia") == "Round Robin":
        resultados = grafica.get("resultados_round_robin", {})
        
        if not resultados:
            return "", "", "", ""
        
        # Ordenar por encuentros ganados
        if grafica["modalidad"] == "Kata":
            lista = sorted(
                resultados.values(),
                key=lambda x: (
                    x.get("encuentros_ganados", 0),
                    x.get("banderas_favor", 0),
                    -x.get("banderas_contra", 0)
                ),
                reverse=True
            )
        else:
            lista = sorted(
                resultados.values(),
                key=lambda x: (
                    x.get("encuentros_ganados", 0),
                    x.get("puntos_favor", 0),
                    -(x.get("faltas_totales", 0) + x.get("faltas_tipo1", 0) + x.get("faltas_tipo2", 0))
                ),
                reverse=True
            )
        
        primer = lista[0]["nombre"] if len(lista) > 0 else ""
        segundo = lista[1]["nombre"] if len(lista) > 1 else ""
        tercero_1 = lista[2]["nombre"] if len(lista) > 2 else ""
        tercero_2 = lista[3]["nombre"] if len(lista) > 3 else ""
        
        # Actualizar ganadores en la gráfica
        grafica["ganadores"]["primer_lugar"] = primer
        grafica["ganadores"]["segundo_lugar"] = segundo
        grafica["ganadores"]["tercero_1"] = tercero_1
        grafica["ganadores"]["tercero_2"] = tercero_2
        
        return primer, segundo, tercero_1, tercero_2
    
    # Lógica original para eliminación directa
    historial = grafica["historial"]

    if not historial:
        return "", "", "", ""

    ultima_ronda = max(r["ronda"] for r in historial)

    final = [
        r for r in historial
        if r["ronda"] == ultima_ronda
    ][-1]
    
    semifinal = ultima_ronda - 1

    perdedores_semifinal = [
        r["perdedor"]
        for r in historial
        if r["ronda"] == semifinal
    ]

    primer = final.get("ganador", "")
    segundo = final.get("perdedor", "")
    tercero_1 = perdedores_semifinal[0] if len(perdedores_semifinal) > 0 else ""
    tercero_2 = perdedores_semifinal[1] if len(perdedores_semifinal) > 1 else ""

    grafica["ganadores"]["primer_lugar"] = primer
    grafica["ganadores"]["segundo_lugar"] = segundo
    grafica["ganadores"]["tercero_1"] = tercero_1
    grafica["ganadores"]["tercero_2"] = tercero_2
    
    return primer, segundo, tercero_1, tercero_2



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


def crear_encuentros(competidores, hacer_preliminar=True, evitar_misma_escuela=True):
    """
    Crea encuentros para una ronda.
    Si hacer_preliminar es True y hay número impar, 
    crea un encuentro preliminar y el resto espera.
    Si evitar_misma_escuela es True, intenta no emparejar 
    competidores de la misma escuela.
    """
    lista = competidores.copy()
    random.shuffle(lista)
    
    encuentros = []
    esperan = []
    
    # -----------------------------
    # SI HAY PRELIMINAR (número impar de competidores)
    # -----------------------------
    if hacer_preliminar and len(lista) % 2 == 1:
        # Buscar dos competidores de DIFERENTE escuela para el preliminar
        c1 = None
        c2 = None
        
        if evitar_misma_escuela:
            # Intentar encontrar dos de diferente escuela
            for i in range(len(lista)):
                for j in range(i + 1, len(lista)):
                    if lista[i]["escuela"] != lista[j]["escuela"]:
                        c1 = lista.pop(j)  # Primero el de mayor índice
                        c2 = lista.pop(i)  # Luego el de menor índice
                        break
                if c1 and c2:
                    break
        
        # Si no se encontró pareja de diferente escuela, tomar los dos primeros
        if not c1 or not c2:
            c1 = lista.pop(0)
            c2 = lista.pop(0)
        
        # Los demás ESPERAN a que termine el preliminar
        esperan = lista.copy()
        
        # Creamos el encuentro preliminar
        encuentros.append({
            "tipo": "preliminar",
            "ronda": 0,
            "nombre_ronda": "Preliminar",
            "competidor_1": c1,
            "competidor_2": c2,
            "resultado": None,
            "ganador": None,
            "perdedor": None,
            "finalizado": False
        })
        
        # Retornamos solo el encuentro preliminar y los que esperan
        return encuentros, esperan
    
    # -----------------------------
    # RONDA NORMAL (cuando ya son pares)
    # -----------------------------
    while len(lista) >= 2:
        c1 = lista.pop(0)
        c2 = None
        
        if evitar_misma_escuela:
            # Buscar un oponente de diferente escuela
            for i, competidor in enumerate(lista):
                if competidor["escuela"] != c1["escuela"]:
                    c2 = lista.pop(i)
                    break
        
        # Si no se encontró oponente de diferente escuela, tomar el primero
        if not c2:
            if lista:
                c2 = lista.pop(0)
            else:
                # Si no hay más competidores, c1 pasa solo
                encuentros.append({
                    "tipo": "normal",
                    "ronda": 1,
                    "nombre_ronda": "Ronda",
                    "competidor_1": c1,
                    "competidor_2": None,
                    "resultado": "BYE",
                    "ganador": c1,
                    "perdedor": None,
                    "finalizado": True
                })
                continue
        
        encuentros.append({
            "tipo": "normal",
            "ronda": 1,
            "nombre_ronda": "Ronda",
            "competidor_1": c1,
            "competidor_2": c2,
            "resultado": None,
            "ganador": None,
            "perdedor": None,
            "finalizado": False
        })
    
    # Si queda uno solo al final
    if len(lista) == 1:
        encuentros.append({
            "tipo": "normal",
            "ronda": 1,
            "nombre_ronda": "Ronda",
            "competidor_1": lista[0],
            "competidor_2": None,
            "resultado": "BYE",
            "ganador": lista[0],
            "perdedor": None,
            "finalizado": True
        })
    
    return encuentros, esperan


def crear_grafica(nombre_grafica, reglamento, modalidad, categoria_edad, sexo, area, tipo_competencia):
    competidores = st.session_state.competidores_temp.copy()
    
    if tipo_competencia == "Round Robin":
        encuentros, esperan = crear_encuentros_round_robin(competidores)
    else:
        encuentros, esperan = crear_encuentros(competidores, evitar_misma_escuela=True)

    nueva_grafica = {
        "id": None,
        "nombre_grafica": nombre_grafica,
        "reglamento": reglamento,
        "modalidad": modalidad,
        "categoria_edad": categoria_edad,
        "sexo": sexo,
        "area": area,
        "tipo_competencia": tipo_competencia,  # ← NUEVO
        "competidores": competidores,
        "estatus": "Pendiente",
        "ronda_actual": 1,
        "encuentros": encuentros,
        "esperan": esperan,
        "historial": [],
        "resultados_round_robin": {},  # ← NUEVO
        "ganadores": {
            "primer_lugar": "",
            "segundo_lugar": "",
            "tercero_1": "",
            "tercero_2": ""
        },
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Inicializar acumuladores para Round Robin
    if tipo_competencia == "Round Robin":
        nueva_grafica = inicializar_resultados_round_robin(nueva_grafica)

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
            "Área": grafica.get("area", "Área 1"),  # ← NUEVO
            "Competidores": len(grafica["competidores"]),
            "Ronda": grafica["ronda_actual"],
            "Estatus": grafica["estatus"]
        })

    return pd.DataFrame(datos)

def avanzar_ronda_si_corresponde(grafica):
    encuentros = grafica["encuentros"]
    
    # Verificar si todos los encuentros están finalizados
    if not all(e["finalizado"] for e in encuentros):
        return
    
    # Recoger ganadores de esta ronda
    ganadores = [
        e["ganador"]
        for e in encuentros
        if e["ganador"] is not None
    ]
    
    # Añadir los que estaban esperando
    ganadores.extend(grafica.get("esperan", []))
    grafica["esperan"] = []
    
    # Si ya solo queda un ganador, terminó la gráfica
    if len(ganadores) == 1:
        grafica["estatus"] = "Finalizado"
        
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
    
    # Si hay 2 ganadores, es la final - no necesita preliminar
    if len(ganadores) == 2:
        hacer_preliminar = False
    else:
        # Si son más de 2, verificar si necesitamos preliminar
        hacer_preliminar = len(ganadores) % 2 == 1
    
    grafica["ronda_actual"] += 1
    
    # Crear nuevos encuentros con la posibilidad de preliminar
    # RONDAS POSTERIORES: NO evitar misma escuela
    nuevos_encuentros, nuevos_esperan = crear_encuentros(
        ganadores,
        hacer_preliminar=hacer_preliminar,
        evitar_misma_escuela=False  # ← Solo primera ronda evita misma escuela
        
    )
    
    # Actualizar el número de ronda en los nuevos encuentros
    for encuentro in nuevos_encuentros:
        if encuentro["tipo"] == "normal":
            encuentro["ronda"] = grafica["ronda_actual"]
        encuentro["nombre_ronda"] = f"Ronda {grafica['ronda_actual']}"
    
    grafica["encuentros"] = nuevos_encuentros
    grafica["esperan"] = nuevos_esperan
    
        

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
            grafica["ganadores"]["tercero_1"],
            3,
            1
        ),
        
        (
            grafica["ganadores"]["tercero_2"],
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

####################################
def finalizar_torneo():

    (
        supabase
        .table("resultados_finales")
        .delete()
        .neq("id", 0)
        .execute()
    )

    (
        supabase
        .table("puntos_escuelas")
        .delete()
        .neq("id", 0)
        .execute()
    )

    (
        supabase
        .table("graficas")
        .delete()
        .neq("id", 0)
        .execute()
    )
####################################

######################ROUND_ROBIN#############################################
def crear_encuentros_round_robin(competidores):
    """
    Crea todos los encuentros para un sistema Round Robin.
    Cada competidor se enfrenta a todos los demás exactamente una vez.
    """
    n = len(competidores)
    encuentros = []
    
    # Generar todos los pares únicos (todos contra todos)
    for i in range(n):
        for j in range(i + 1, n):
            encuentros.append({
                "tipo": "round_robin",
                "ronda": 1,  # Se actualizará después
                "nombre_ronda": "Round Robin",
                "competidor_1": competidores[i],
                "competidor_2": competidores[j],
                "resultado": None,
                "ganador": None,
                "perdedor": None,
                "finalizado": False
            })
    
    # Organizar en rondas (opcional: algoritmo de calendarización)
    random.shuffle(encuentros)
    
    return encuentros, []


def inicializar_resultados_round_robin(grafica):
    """
    Inicializa los acumuladores de resultados para Round Robin.
    """
    resultados = {}
    for competidor in grafica["competidores"]:
        resultados[competidor["nombre"]] = {
            "nombre": competidor["nombre"],
            "escuela": competidor["escuela"],
            "puntos_favor": 0,
            "puntos_contra": 0,
            "banderas_favor": 0,
            "banderas_contra": 0,
            "faltas_tipo1": 0,
            "faltas_tipo2": 0,
            "encuentros_ganados": 0,
            "encuentros_perdidos": 0,
            "encuentros_empatados": 0
        }
    
    grafica["resultados_round_robin"] = resultados
    return grafica


def actualizar_acumulados_round_robin(grafica, resultado):
    """
    Actualiza los acumulados después de cada encuentro de Round Robin.
    """
    resultados = grafica.get("resultados_round_robin", {})
    
    c1_nombre = resultado["competidor_1"]
    c2_nombre = resultado["competidor_2"]
    ganador = resultado["ganador"]
    
    # Inicializar si no existen
    if c1_nombre not in resultados:
        resultados[c1_nombre] = crear_acumulador_vacio()
    if c2_nombre not in resultados:
        resultados[c2_nombre] = crear_acumulador_vacio()
    
    # Actualizar según tipo de competencia
    if grafica["modalidad"] == "Kata":
        banderas_1 = resultado.get("banderas_rojo", 0)
        banderas_2 = resultado.get("banderas_azul", resultado.get("banderas_blanco", 0))
        
        resultados[c1_nombre]["banderas_favor"] += banderas_1
        resultados[c1_nombre]["banderas_contra"] += banderas_2
        resultados[c2_nombre]["banderas_favor"] += banderas_2
        resultados[c2_nombre]["banderas_contra"] += banderas_1
        
        if ganador == c1_nombre:
            resultados[c1_nombre]["encuentros_ganados"] += 1
            resultados[c2_nombre]["encuentros_perdidos"] += 1
        elif ganador == c2_nombre:
            resultados[c2_nombre]["encuentros_ganados"] += 1
            resultados[c1_nombre]["encuentros_perdidos"] += 1
        else:
            resultados[c1_nombre]["encuentros_empatados"] += 1
            resultados[c2_nombre]["encuentros_empatados"] += 1
            
    else:  # Kumite
        puntos_1 = resultado.get("puntos_1", 0)
        puntos_2 = resultado.get("puntos_2", 0)
        
        # Faltas totales (WKF)
        faltas_1 = resultado.get("faltas_1", 0)
        faltas_2 = resultado.get("faltas_2", 0)
        
        # Faltas por tipo (WUKF)
        faltas_t1_1 = resultado.get("faltas_tipo1_1", 0)
        faltas_t1_2 = resultado.get("faltas_tipo1_2", 0)
        faltas_t2_1 = resultado.get("faltas_tipo2_1", 0)
        faltas_t2_2 = resultado.get("faltas_tipo2_2", 0)
        
        # Actualizar puntos
        resultados[c1_nombre]["puntos_favor"] += puntos_1
        resultados[c1_nombre]["puntos_contra"] += puntos_2
        resultados[c2_nombre]["puntos_favor"] += puntos_2
        resultados[c2_nombre]["puntos_contra"] += puntos_1
        
        # Actualizar faltas totales
        resultados[c1_nombre]["faltas_totales"] = resultados[c1_nombre].get("faltas_totales", 0) + faltas_1
        resultados[c2_nombre]["faltas_totales"] = resultados[c2_nombre].get("faltas_totales", 0) + faltas_2
        
        # Actualizar faltas por tipo
        resultados[c1_nombre]["faltas_tipo1"] += faltas_t1_1
        resultados[c1_nombre]["faltas_tipo2"] += faltas_t2_1
        resultados[c2_nombre]["faltas_tipo1"] += faltas_t1_2
        resultados[c2_nombre]["faltas_tipo2"] += faltas_t2_2
        
        # Actualizar encuentros ganados/perdidos/empatados
        if ganador == c1_nombre:
            resultados[c1_nombre]["encuentros_ganados"] += 1
            resultados[c2_nombre]["encuentros_perdidos"] += 1
        elif ganador == c2_nombre:
            resultados[c2_nombre]["encuentros_ganados"] += 1
            resultados[c1_nombre]["encuentros_perdidos"] += 1
        else:
            resultados[c1_nombre]["encuentros_empatados"] += 1
            resultados[c2_nombre]["encuentros_empatados"] += 1
    
    grafica["resultados_round_robin"] = resultados
    return grafica

def crear_acumulador_vacio():
    """Crea un acumulador vacío para un competidor."""
    return {
        "puntos_favor": 0,
        "puntos_contra": 0,
        "banderas_favor": 0,
        "banderas_contra": 0,
        "faltas_totales": 0,  # ← NUEVO: Para WKF
        "faltas_tipo1": 0,
        "faltas_tipo2": 0,
        "encuentros_ganados": 0,
        "encuentros_perdidos": 0,
        "encuentros_empatados": 0
    }


def determinar_ganadores_round_robin(grafica):
    """
    Determina los ganadores al finalizar un Round Robin.
    Criterios de desempate:
    1. Más encuentros ganados
    2. Más puntos/banderas a favor
    3. Menos faltas totales
    4. Menos faltas tipo 1
    5. Menos faltas tipo 2
    """
    resultados = grafica.get("resultados_round_robin", {})
    
    if not resultados:
        return grafica
    
    # Convertir a lista para ordenar
    lista_resultados = list(resultados.values())
    
    if grafica["modalidad"] == "Kata":
        # Ordenar por: ganados, banderas favor, menos banderas contra
        lista_resultados.sort(
            key=lambda x: (
                x.get("encuentros_ganados", 0),
                x.get("banderas_favor", 0),
                -x.get("banderas_contra", 0)
            ),
            reverse=True
        )
    else:
        # Ordenar por: ganados, puntos favor, menos faltas
        lista_resultados.sort(
            key=lambda x: (
                x.get("encuentros_ganados", 0),
                x.get("puntos_favor", 0),
                -(x.get("faltas_totales", 0)),  # Menos faltas totales (WKF)
                -(x.get("faltas_tipo1", 0)),    # Menos faltas tipo 1 (WUKF)
                -(x.get("faltas_tipo2", 0))     # Menos faltas tipo 2 (WUKF)
            ),
            reverse=True
        )
    
    # Asignar lugares según la posición en la tabla
    grafica["ganadores"]["primer_lugar"] = lista_resultados[0]["nombre"] if len(lista_resultados) > 0 else ""
    grafica["ganadores"]["segundo_lugar"] = lista_resultados[1]["nombre"] if len(lista_resultados) > 1 else ""
    grafica["ganadores"]["tercero_1"] = lista_resultados[2]["nombre"] if len(lista_resultados) > 2 else ""
    grafica["ganadores"]["tercero_2"] = lista_resultados[3]["nombre"] if len(lista_resultados) > 3 else ""
    
    return grafica
############################FIN_ROUND_ROBIN####################################

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
        "Resultados Finales",
        "Finalizar Torneo"
    ]
)


# =========================
# REGISTRO
# =========================

if rol == "Registro":
    st.header("Registro de competidores y creación de gráfica")

    col1, col2, col3 = st.columns(3)

    with col1:
        
        tipo_competencia = st.selectbox(
            "Tipo de competencia",
            ["Eliminación directa", "Round Robin"],
            index=0
        )

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
            value=st.session_state.get("plantilla_categoria", "")
        )
        
        # NUEVO: Selector de área
        area = st.selectbox(
            "Área",
            ["Área 1", "Área 2", "Área 3", "Área 4", "Área 5", "Área 6", "Área 7", "Área 8"],
            index=0
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
                sexo,
                area,
                tipo_competencia
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

            primer, segundo, tercero_1, tercero_2 = calcular_premiacion(grafica)

            escuela_primer = obtener_escuela(grafica, primer) if primer else ""
            escuela_segundo = obtener_escuela(grafica, segundo) if segundo else ""
            escuela_tercero1 = obtener_escuela(grafica, tercero_1) if tercero_1 else ""
            escuela_tercero2 = obtener_escuela(grafica, tercero_2) if tercero_2 else ""
            

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Primer lugar", primer if primer else "No definido")
                if escuela_primer:
                    st.caption(f"Escuela: {escuela_primer}")

            with col2:
                st.metric("Segundo lugar", segundo if segundo else "No definido")
                if escuela_segundo:
                    st.caption(f"Escuela: {escuela_segundo}")

            with col3:
                st.metric("Tercer lugar", tercero_1 if tercero_1 else "No definido")
                if escuela_tercero1:
                    st.caption(f"Escuela: {escuela_tercero1}")
            
            with col4:
                 st.metric("Tercer lugar", tercero_2 if tercero_2 else "No definido")
                 if escuela_tercero2:
                     st.caption(f"Escuela: {escuela_tercero2}")

            st.write(f"**Reglamento:** {grafica['reglamento']}")
            st.write(f"**Modalidad:** {grafica['modalidad']}")
            st.write(f"**Categoría:** {grafica['categoria_edad']}")
            st.write(f"**Sexo:** {grafica['sexo']}")
    
            st.divider()
    
            st.subheader("Competidores de la categoría")
            
            df = pd.DataFrame(grafica["competidores"])
            
            df.index = df.index + 1
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=False
            )
            
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


#############Finalizat torneo##################
elif rol == "Finalizar Torneo":

    st.header("Finalizar Torneo")

    st.warning(
        "Esta acción eliminará TODOS los resultados "
        "finales y TODOS los puntos acumulados por escuelas."
    )
    
    password = st.text_input(
        "Ingrese la contraseña de administrador",
        type="password"
    )
    
    if st.button("BORRAR RESULTADOS DEL TORNEO"):
    
        if password == "CHARRO_ME_LA_PELA":
            finalizar_torneo()
            st.success("El torneo fue reiniciado correctamente.")
            st.rerun()
    
        else:
            st.error("Contraseña incorrecta.")
