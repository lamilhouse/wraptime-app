import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬")

# 1. CONEXIÓN (Sin caché para que sea instantáneo)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. MENÚ LATERAL
st.sidebar.title("Menú")
opcion = st.sidebar.radio("Ir a:", ["Fichar Jornada", "Configurar Proyecto"])

# --- SECCIÓN: CONFIGURAR PROYECTO ---
if opcion == "Configurar Proyecto":
    st.title("🎬 Configuración de Proyecto")
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        h_jornada = st.number_input("Horas jornada base", value=8)
        t_comida = st.text_input("Tiempo comida", value="1 hora")
        descanso = st.radio("¿Descanso incluido?", ["Sí", "No"])
        
        if st.form_submit_button("Guardar Proyecto"):
            if nombre_p:
                nuevo_p = pd.DataFrame([{"ID_Usuario": "User1", "Proyecto": nombre_p, "Horas_Jornada": h_jornada, "Tiempo_Comida": t_comida, "Descanso_Incluido": descanso, "Estado": "Activo"}])
                # Actualizamos la hoja
                conn.update(worksheet="Config_Proyectos", data=nuevo_p)
                st.success(f"Proyecto '{nombre_p}' guardado con éxito.")
                # Borramos la caché para que el selector se actualice
                st.cache_data.clear()
                st.info("Ya puedes ir a 'Fichar Jornada' en el menú lateral.")
                st.balloons()
            else:
                st.error("Escribe un nombre para el proyecto.")

# --- SECCIÓN: FICHAR JORNADA ---
elif opcion == "Fichar Jornada":
    st.title("📝 Registro Diario")
    
    # IMPORTANTE: Forzamos la lectura fresca del Excel
    df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=0) # ttl=0 significa "sin espera"
    
    if df_proyectos.empty:
        st.warning("⚠️ No hay proyectos creados. Ve a 'Configurar Proyecto' primero.")
    else:
        # Limpiamos posibles filas vacías y sacamos la lista de nombres
        lista_proyectos = df_proyectos["Proyecto"].dropna().unique().tolist()
        
        with st.form("fichaje_diario"):
            proyecto_sel = st.selectbox("Selecciona el Proyecto", lista_proyectos)
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
                st.success("¡Jornada guardada correctamente!")
                st.balloons()
