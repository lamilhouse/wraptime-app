import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬")

conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("Menú WrapTime")
opcion = st.sidebar.radio("Ir a:", ["Fichar Jornada", "Mi Historial", "Configurar Proyecto"])

# --- SECCIÓN: CONFIGURAR PROYECTO ---
if opcion == "Configurar Proyecto":
    st.title("🎬 Configuración de Proyecto")
    df_existente = conn.read(worksheet="Config_Proyectos", ttl=10)
    
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        fecha_inicio_rodaje = st.date_input("Fecha Inicio Rodaje (Lunes de la S1)", datetime.now())
        h_jornada = st.number_input("Horas jornada base", value=8)
        t_comida = st.text_input("Tiempo comida", value="1 hora")
        descanso = st.radio("¿Descanso incluido?", ["Sí", "No"])
        
        if st.form_submit_button("Guardar Proyecto"):
            if nombre_p:
                nuevo_p = pd.DataFrame([{
                    "ID_Usuario": "User1", 
                    "Proyecto": nombre_p, 
                    "Fecha_Inicio": str(fecha_inicio_rodaje),
                    "Horas_Jornada": h_jornada, 
                    "Tiempo_Comida": t_comida, 
                    "Descanso_Incluido": descanso, 
                    "Estado": "Activo"
                }])
                df_final = pd.concat([df_existente, nuevo_p], ignore_index=True)
                conn.update(worksheet="Config_Proyectos", data=df_final)
                st.success(f"Proyecto '{nombre_p}' guardado.")
                st.cache_data.clear()
            else:
                st.error("Escribe un nombre.")

# --- SECCIÓN: FICHAR JORNADA ---
elif opcion == "Fichar Jornada":
    st.title("📝 Registro Diario")
    df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=10)
    df_fichajes_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=10)
    
    if df_proyectos.empty:
        st.warning("⚠️ Crea un proyecto primero.")
    else:
        lista_proyectos = df_proyectos["Proyecto"].dropna().unique().tolist()
        with st.form("fichaje_diario"):
            proyecto_sel = st.selectbox("Selecciona el Proyecto", lista_proyectos)
            fecha = st.date_input("Fecha", datetime.now())
            tipo_dia = st.selectbox("Tipo de día", ["Normal", "Festivo"])
            col1, col2, col3 = st.columns(3)
            with col1: h_ini = st.time_input("Hora Inicio")
            with col2: h_corte = st.time_input("Corte Cámara")
            with col3: h_fin = st.time_input("Fin Jornada")
            comida = st.radio("¿Hubo comida?", ["Sí", "No"], horizontal=True)
            
            if st.form_submit_button("Guardar Fichaje"):
                nuevo_fichaje = pd.DataFrame([{"ID_Usuario": "User1", "Proyecto": proyecto_sel, "Fecha": str(fecha), "Tipo_Dia": tipo_dia, "Hora_Inicio": str(h_ini), "Corte_Camara": str(h_corte), "Hora_Fin_Jornada": str(h_fin), "Comida": comida}])
                df_fichajes_final = pd.concat([df_fichajes_existentes, nuevo_fichaje], ignore_index=True)
                conn.update(worksheet="Fichajes_Diarios", data=df_fichajes_final)
                st.success("¡Jornada guardada!")
                st.balloons()

# --- SECCIÓN: MI HISTORIAL ---
elif opcion == "Mi Historial":
    st.title("📅 Historial de Rodaje")
    df_fichajes = conn.read(worksheet="Fichajes_Diarios", ttl=0)
    df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=0)
    
    if df_fichajes.empty:
        st.info("Aún no tienes jornadas registradas.")
    else:
        df_fichajes['Fecha'] = pd.to_datetime(df_fichajes['Fecha'])
        
        for proyecto in df_fichajes['Proyecto'].unique():
            st.subheader(f"🎥 Proyecto: {proyecto}")
            info_p = df_proyectos[df_proyectos['Proyecto'] == proyecto]
            
            if not info_p.empty:
                # Obtenemos la fecha de inicio configurada
                fecha_inicio = pd.to_datetime(info_p['Fecha_Inicio'].iloc[0])
                
                def calc_semana_rodaje(fecha_actual, fecha_ref):
                    diff_dias = (fecha_actual - fecha_ref).days
                    # Cálculo: días entre 7, redondeado hacia abajo + 1
                    num_sem = math.floor(diff_dias / 7) + 1
                    # Ajuste para que después de la -1 vaya la 1
                    if num_sem <= 0:
                        return num_sem - 1
                    return num_sem

                df_p = df_fichajes[df_fichajes['Proyecto'] == proyecto].copy()
                df_p['Semana_Rodaje'] = df_p['Fecha'].apply(lambda x: calc_semana_rodaje(x, fecha_inicio))
                
                # Ordenar para que la última semana grabada salga arriba
                semanas = sorted(df_p['Semana_Rodaje'].unique(), reverse=True)
                
                for sem in semanas:
                    txt_sem = f"Semana {sem}" if sem > 0 else f"Pre-producción (S{sem})"
                    with st.expander(f"📂 {txt_sem}", expanded=True):
                        datos_sem = df_p[df_p['Semana_Rodaje'] == sem].sort_values("Fecha")
                        datos_sem['Fecha_Bonita'] = datos_sem['Fecha'].dt.strftime('%d/%m/%Y')
                        st.table(datos_sem[["Fecha_Bonita", "Tipo_Dia", "Hora_Inicio", "Corte_Camara", "Hora_Fin_Jornada"]])
            else:
                st.error(f"Configuración no encontrada para {proyecto}")
