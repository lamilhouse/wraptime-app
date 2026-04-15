import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬")

# 1. CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DISEÑO DEL MENÚ LATERAL (Jerarquía: Proyecto > Día > Historial)
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    st.markdown("---")
    
    opcion_menu = st.selectbox(
        "Navegación",
        ["🏗️ Configurar Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"],
        index=1  # Abre por defecto en Fichar Jornada
    )
    
    st.markdown("---")
    st.caption("Versión 1.0 - El diario del técnico")
    if st.button("🆘 Ayuda"):
        st.info("Contacto: soporte@wraptime.app")

# 3. LÓGICA DE NAVEGACIÓN
if "Configurar Proyecto" in opcion_menu:
    st.title("🏗️ Configuración de Proyecto")
    try:
        df_existente = conn.read(worksheet="Config_Proyectos", ttl=10)
    except:
        df_existente = pd.DataFrame()
    
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        fecha_inicio_rodaje = st.date_input("Fecha Inicio Rodaje (Día 1 / S1)", datetime.now())
        h_jornada = st.number_input("Horas jornada base", value=8)
        t_comida = st.text_input("Tiempo comida", value="1 hora")
        descanso = st.radio("¿Descanso incluido?", ["Sí", "No"])
        
        if st.form_submit_button("🚀 Guardar Proyecto"):
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
                st.balloons()
            else:
                st.error("Por favor, introduce un nombre.")

elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Registro Diario")
    try:
        df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=10)
        df_fichajes_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=10)
    except:
        st.error("Error al conectar con Google Sheets.")
        st.stop()
    
    if df_proyectos.empty:
        st.warning("⚠️ Primero configura un proyecto en el menú lateral.")
    else:
        lista_proyectos = df_proyectos["Proyecto"].dropna().unique().tolist()
        with st.form("fichaje_diario"):
            proyecto_sel = st.selectbox("🎬 Proyecto", lista_proyectos)
            fecha = st.date_input("📅 Fecha", datetime.now())
            
            opciones_dia = ["Normal", "Festivo", "Viaje", "Pruebas", "Carga", "Oficina", "Localización", "Chequeo"]
            tipo_dia_lista = st.multiselect("📋 Tipo de jornada", opciones_dia, default=["Normal"])
            
            st.write("---")
            col1, col2, col3 = st.columns(3)
            with col1: h_ini = st.time_input("🕒 Citación (Call)")
            with col2: h_corte = st.time_input("🎥 Wrap Cámara")
            with col3: h_fin = st.time_input("🚚 Fin Jornada")
            
            st.write("---")
            st.write("⚠️ **Incidencias / Extras:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                inc_comida = st.checkbox("❌ No comida")
                inc_corte = st.checkbox("⏱️ No corte 15 min")
            with c2:
                inc_turn = st.checkbox("📉 Salto Turnaround")
                inc_km = st.checkbox("🚗 Kilometraje")
            with c3:
                inc_dietas = st.checkbox("🍴 Dietas")
                inc_otros = st.checkbox("❓ Otras")

            obs = st.text_area("📝 Notas / Observaciones")

            if st.form_submit_button("💾 Guardar Jornada"):
                tipo_dia_str = ", ".join(tipo_dia_lista)
                alertas = [k for k, v in {"No comida": inc_comida, "No corte 15min": inc_corte, "Salto Turnaround": inc_turn, "Kilometraje": inc_km, "Dietas": inc_dietas, "Otros": inc_otros}.items() if v]
                
                nuevo_fichaje = pd.DataFrame([{
                    "ID_Usuario": "User1", "Proyecto": proyecto_sel, "Fecha": str(fecha),
                    "Tipo_Dia": tipo_dia_str, "Hora_Inicio": str(h_ini), "Corte_Camara": str(h_corte),
                    "Hora_Fin_Jornada": str(h_fin), "Comida": "No" if inc_comida else "Sí",
                    "Incidencias": ", ".join(alertas), "Observaciones": obs
                }])
                
                df_final_f = pd.concat([df_fichajes_existentes, nuevo_fichaje], ignore_index=True)
                conn.update(worksheet="Fichajes_Diarios", data=df_final_f)
                st.success("¡Jornada guardada!")
                st.balloons()

elif "Mi Historial" in opcion_menu:
    st.title("📅 Historial de Rodaje")
    try:
        df_fichajes = conn.read(worksheet="Fichajes_Diarios", ttl=10)
        df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=10)
    except:
        st.error("No se pudo leer el historial.")
        st.stop()
    
    if df_fichajes.empty:
        st.info("Aún no hay registros.")
    else:
        df_fichajes['Fecha'] = pd.to_datetime(df_fichajes['Fecha'])
        for proyecto in df_fichajes['Proyecto'].unique():
            st.subheader(f"🎥 {proyecto}")
            info_p = df_proyectos[df_proyectos['Proyecto'] == proyecto]
            if not info_p.empty:
                f_inicio = pd.to_datetime(info_p['Fecha_Inicio'].iloc[0])
                df_p = df_fichajes[df_fichajes['Proyecto'] == proyecto].copy()
                
                def get_sem(f, start):
                    d = (f - start).days
                    s = math.floor(d / 7) + 1
                    return s if s > 0 else s - 1
                
                df_p['Semana'] = df_p['Fecha'].apply(lambda x: get_sem(x, f_inicio))
                semanas = sorted(df_p['Semana'].unique(), reverse=True)
                
                for s in semanas:
                    txt = f"Semana {s}" if s > 0 else f"Pre-prod (S{s})"
                    with st.expander(f"📂 {txt}"):
                        d_sem = df_p[df_p['Semana'] == s].sort_values("Fecha")
                        d_sem['Fecha'] = d_sem['Fecha'].dt.strftime('%d/%m/%Y')
                        st.table(d_sem[["Fecha", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Incidencias"]])
            st.write("---")
