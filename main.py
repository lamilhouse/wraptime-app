import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬")

# 1. CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. MENÚ LATERAL
st.sidebar.title("Menú WrapTime")
opcion = st.sidebar.radio("Ir a:", ["Fichar Jornada", "Mi Historial", "Configurar Proyecto"])

# --- SECCIÓN: CONFIGURAR PROYECTO ---
if opcion == "Configurar Proyecto":
    st.title("🎬 Configuración de Proyecto")
    df_existente = conn.read(worksheet="Config_Proyectos", ttl=0)
    
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        h_jornada = st.number_input("Horas jornada base", value=8)
        t_comida = st.text_input("Tiempo comida", value="1 hora")
        descanso = st.radio("¿Descanso incluido?", ["Sí", "No"])
        
        if st.form_submit_button("Guardar Proyecto"):
            if nombre_p:
                nuevo_p = pd.DataFrame([{"ID_Usuario": "User1", "Proyecto": nombre_p, "Horas_Jornada": h_jornada, "Tiempo_Comida": t_comida, "Descanso_Incluido": descanso, "Estado": "Activo"}])
                df_final = pd.concat([df_existente, nuevo_p], ignore_index=True)
                conn.update(worksheet="Config_Proyectos", data=df_final)
                st.success(f"Proyecto '{nombre_p}' guardado.")
                st.cache_data.clear()
            else:
                st.error("Escribe un nombre.")

# --- SECCIÓN: FICHAR JORNADA ---
elif opcion == "Fichar Jornada":
    st.title("📝 Registro Diario")
    df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=0)
    df_fichajes_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=0)
    
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

# --- SECCIÓN: MI HISTORIAL (LA VISTA LITE) ---
elif opcion == "Mi Historial":
    st.title("📅 Mi Historial")
    df_fichajes = conn.read(worksheet="Fichajes_Diarios", ttl=0)
    
    if df_fichajes.empty:
        st.info("Aún no tienes jornadas registradas.")
    else:
        # Mostramos la tabla limpia
        columnas_visibles = ["Proyecto", "Fecha", "Tipo_Dia", "Hora_Inicio", "Corte_Camara", "Hora_Fin_Jornada"]
        st.dataframe(df_fichajes[columnas_visibles], use_container_width=True)
        
        st.write("---")
        # EL GANCHO COMERCIAL (Upselling)
        st.info("💡 **Tip Profesional:** ¿Quieres saber cuánto has acumulado en horas extras y nocturnidad?")
        if st.button("🚀 CALCULAR NÓMINA AHORA"):
            st.write("Copia tus horas y pégalas en nuestra **Calculadora de Nómina** para ver tu sueldo neto.")
            # Aquí pondrías el link real a tu otra calculadora
            st.link_button("Ir a Calculadora Nómina", "https://tu-otra-app.streamlit.app")
