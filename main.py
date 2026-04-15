import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")

# 1. CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DISEÑO DEL MENÚ LATERAL
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    st.markdown("---")
    opcion_menu = st.selectbox(
        "Navegación",
        ["🏗️ Configurar Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"],
        index=1
    )
    st.markdown("---")
    st.caption("Versión 1.2 - Formato ES")
    if st.button("🆘 Ayuda"):
        st.info("Contacto: soporte@wraptime.app")

# 3. LÓGICA DE NAVEGACIÓN

# --- OPCIÓN A: CONFIGURAR PROYECTO ---
if "Configurar Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    try:
        df_existente = conn.read(worksheet="Config_Proyectos", ttl=10)
    except:
        df_existente = pd.DataFrame()
    
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        fecha_inicio_rodaje = st.date_input("Día 1 / Semana 1", datetime.now(), format="DD/MM/YYYY")
        h_jornada = st.number_input("Horas jornada base", value=8)
        t_comida = st.text_input("Tiempo comida", value="1 hora")
        descanso = st.radio("¿Descanso incluido?", ["Sí", "No"], horizontal=True)
        
        if st.form_submit_button("🚀 Guardar Proyecto"):
            if nombre_p:
                nuevo_p = pd.DataFrame([{
                    "ID_Usuario": "User1", "Proyecto": nombre_p, 
                    "Fecha_Inicio": str(fecha_inicio_rodaje), "Horas_Jornada": h_jornada, 
                    "Tiempo_Comida": t_comida, "Descanso_Incluido": descanso, "Estado": "Activo"
                }])
                df_final = pd.concat([df_existente, nuevo_p], ignore_index=True)
                conn.update(worksheet="Config_Proyectos", data=df_final)
                st.success(f"Proyecto '{nombre_p}' guardado.")
                st.cache_data.clear()
            else:
                st.error("Escribe un nombre.")

# --- OPCIÓN B: FICHAR JORNADA ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje Diario")
    try:
        df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=10)
        df_fichajes_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=10)
    except:
        st.error("Error de conexión.")
        st.stop()
    
    if df_proyectos.empty:
        st.warning("⚠️ Crea un proyecto primero.")
    else:
        lista_proyectos = df_proyectos["Proyecto"].dropna().unique().tolist()
        with st.form("fichaje_diario"):
            proyecto_sel = st.selectbox("🎬 Proyecto", lista_proyectos)
            fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
            
            st.write("📋 **Tipo de jornada:**")
            f1, f2 = st.columns(4), st.columns(4)
            t1 = f1[0].checkbox("Normal", value=True)
            t2 = f1[1].checkbox("Festivo")
            t3 = f1[2].checkbox("Viaje")
            t4 = f1[3].checkbox("Pruebas")
            t5 = f2[0].checkbox("Carga")
            t6 = f2[1].checkbox("Oficina")
            t7 = f2[2].checkbox("Loc.")
            t8 = f2[3].checkbox("Chequeo")

            st.write("---")
            c1, c2, c3 = st.columns(3)
            h_ini = c1.time_input("🕒 Call")
            h_corte = c2.time_input("🎥 Wrap")
            h_fin = c3.time_input("🚚 Fin")
            
            st.write("---")
            st.write("⚠️ **Incidencias:**")
            i1, i2, i3 = st.columns(3)
            inc_com = i1.checkbox("❌ No comida")
            inc_cor = i1.checkbox("⏱️ No 15 min")
            inc_tur = i2.checkbox("📉 Turnaround")
            inc_kms = i2.checkbox("🚗 Kms")
            inc_die = i3.checkbox("🍴 Dietas")
            inc_otr = i3.checkbox("❓ Otros")

            obs = st.text_area("📝 Notas")

            if st.form_submit_button("💾 Guardar"):
                tags = {"Normal":t1,"Festivo":t2,"Viaje":t3,"Pruebas":t4,"Carga":t5,"Oficina":t6,"Loc":t7,"Chequeo":t8}
                tipo_dia_str = ", ".join([k for k, v in tags.items() if v])
                alertas = [k for k, v in {"No comida":inc_com,"No 15min":inc_cor,"Turnaround":inc_tur,"Km":inc_kms,"Dietas":inc_die,"Otros":inc_otr}.items() if v]
                
                nuevo = pd.DataFrame([{"ID_Usuario": "User1", "Proyecto": proyecto_sel, "Fecha": str(fecha), "Tipo_Dia": tipo_dia_str, "Hora_Inicio": str(h_ini), "Corte_Camara": str(h_corte), "Hora_Fin_Jornada": str(h_fin), "Comida": "No" if inc_com, "Incidencias": ", ".join(alertas), "Observaciones": obs}])
                df_final = pd.concat([df_fichajes_existentes, nuevo], ignore_index=True)
                conn.update(worksheet="Fichajes_Diarios", data=df_final)
                st.success("¡Guardado!")
                st.balloons()

# --- OPCIÓN C: MI HISTORIAL ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Historial")
    try:
        df_f = conn.read(worksheet="Fichajes_Diarios", ttl=10)
        df_p = conn.read(worksheet="Config_Proyectos", ttl=10)
    except:
        st.stop()
    
    if df_f.empty:
        st.info("Vacío.")
    else:
        df_f['Fecha'] = pd.to_datetime(df_f['Fecha'])
        for p in df_f['Proyecto'].unique():
            st.subheader(f"🎥 {p}")
            info = df_p[df_p['Proyecto'] == p]
            if not info.empty:
                start = pd.to_datetime(info['Fecha_Inicio'].iloc[0])
                df_proy = df_f[df_f['Proyecto'] == p].copy()
                df_proy['Semana'] = df_proy['Fecha'].apply(lambda x: (math.floor((x-start).days/7)+1) if (x-start).days >=0 else (math.floor((x-start).days/7)))
                
                for s in sorted(df_proy['Semana'].unique(), reverse=True):
                    with st.expander(f"📂 Semana {s}" if s>0 else f"📂 Pre-prod (S{s})"):
                        d_s = df_proy[df_proy['Semana'] == s].sort_values("Fecha")
                        d_s['Fecha'] = d_s['Fecha'].dt.strftime('%d/%m/%Y')
                        st.table(d_s[["Fecha", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Incidencias"]])
