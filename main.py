import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬")

# 1. CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. MENÚ LATERAL
st.sidebar.title("Menú")
opcion = st.sidebar.radio("Ir a:", ["Fichar Jornada", "Configurar Proyecto"])

# --- SECCIÓN: CONFIGURAR PROYECTO ---
if opcion == "Configurar Proyecto":
    st.title("🎬 Configuración")
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        h_jornada = st.number_input("Horas jornada base", value=8)
        t_comida = st.text_input("Tiempo comida", value="1 hora")
        descanso = st.radio("¿Descanso incluido?", ["Sí", "No"])
        
        if st.form_submit_button("Guardar Proyecto"):
            nuevo_p = pd.DataFrame([{"ID_Usuario": "User1", "Proyecto": nombre_p, "Horas_Jornada": h_jornada, "Tiempo_Comida": t_comida, "Descanso_Incluido": descanso, "Estado": "Activo"}])
            conn.update(worksheet="Config_Proyectos", data=nuevo_p)
            st.success("Proyecto guardado")

# --- SECCIÓN: FICHAR JORNADA ---
elif opcion == "Fichar Jornada":
    st.title("📝 Fichaje Diario")
    
    # Leemos qué proyectos existen para que el usuario elija uno
    df_proyectos = conn.read(worksheet="Config_Proyectos")
    lista_proyectos = df_proyectos["Proyecto"].tolist() if not df_proyectos.empty else []
    
    if not lista_proyectos:
        st.warning("Primero crea un proyecto en el menú lateral.")
    else:
        with st.form("fichaje_diario"):
            proyecto_sel = st.selectbox("Proyecto", lista_proyectos)
            fecha = st.date_input("Fecha", datetime.now())
            tipo_dia = st.selectbox("Tipo de día", ["Normal", "Festivo"])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                h_ini = st.time_input("Hora Inicio (Call)")
            with col2:
                h_corte = st.time_input("Corte Cámara (Wrap)")
            with col3:
                h_fin = st.time_input("Fin Jornada (Carga)")
                
            comida = st.radio("¿Hubo comida?", ["Sí", "No"], horizontal=True)
            
            if st.form_submit_button("Guardar Fichaje"):
                nuevo_fichaje = pd.DataFrame([{
                    "ID_Usuario": "User1",
                    "Proyecto": proyecto_sel,
                    "Fecha": str(fecha),
                    "Tipo_Dia": tipo_dia,
                    "Hora_Inicio": str(h_ini),
                    "Corte_Camara": str(h_corte),
                    "Hora_Fin_Jornada": str(h_fin),
                    "Comida": comida
                }])
                conn.update(worksheet="Fichajes_Diarios", data=nuevo_fichaje)
                st.success("¡Jornada guardada!")
                st.balloons()
