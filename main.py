import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- LÓGICA DE SINCRONIZACIÓN DE HORAS ---
if 'hora_wrap' not in st.session_state:
    st.session_state.hora_wrap = time(19, 0)
if 'hora_fin' not in st.session_state:
    st.session_state.hora_fin = time(19, 0)

def actualizar_fin():
    st.session_state.hora_fin = st.session_state.hora_wrap

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    st.markdown("---")
    opcion_menu = st.selectbox("Navegación", ["🏗️ Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"], index=1)
    st.markdown("---")
    
    # --- BOTÓN DE DESCARGA CSV ---
    df_f_descarga = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    if not df_f_descarga.empty:
        csv = df_f_descarga.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar CSV para Excel",
            data=csv,
            file_name=f"historial_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    st.caption("Versión 2.2 - Clean Interface")

# --- SECCIÓN: PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Gestión del Proyecto")
    df_p = conn.read(worksheet="Config_Proyectos", ttl=1)
    
    if not df_p.empty:
        nombre_actual = df_p.iloc[0]['Proyecto']
        st.info(f"🚀 **Proyecto activo:** {nombre_actual}")
        
        st.write("---")
        with st.expander("⚠️ Zona de Peligro"):
            st.write("Borrar todos los datos para empezar un rodaje nuevo.")
            if st.button("Confirmar: Borrar todo"):
                df_vacio_p = pd.DataFrame(columns=["ID_Usuario", "Proyecto", "Fecha_Inicio", "Estado"])
                df_vacio_f = pd.DataFrame(columns=["ID_Usuario", "Proyecto", "Fecha", "Tipo_Dia", "Hora_Inicio", "Corte_Camara", "Hora_Fin_Jornada", "Comida", "Incidencias", "Observaciones"])
                conn.update(worksheet="Config_Proyectos", data=df_vacio_p)
                conn.update(worksheet="Fichajes_Diarios", data=df_vacio_f)
                st.cache_data.clear()
                st.rerun()
    else:
        with st.form("nuevo_proyecto"):
            nombre_p = st.text_input("Nombre del Rodaje")
            fecha_ini = st.date_input("Día 1 / S1", datetime.now())
            if st.form_submit_button("🚀 Iniciar Proyecto"):
                if nombre_p:
                    nuevo_p = pd.DataFrame([{"ID_Usuario":"User1","Proyecto":nombre_p,"Fecha_Inicio":str(fecha_ini),"Estado":"Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=nuevo_p)
                    st.cache_data.clear()
                    st.rerun()

# --- SECCIÓN: FICHAR JORNADA ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje Diario")
    df_p = conn.read(worksheet="Config_Proyectos", ttl=1)
    
    if df_p.empty:
        st.warning("⚠️ Configura un proyecto primero.")
    else:
        proyecto_sel = df_p.iloc[0]['Proyecto']
        st.caption(f"Rodaje: {proyecto_sel}")
        
        fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
        opciones = ["Normal", "Festivo", "Viaje", "Pruebas", "Carga", "Oficina", "Loc.", "Chequeo"]
        tipo_dia_lista = st.pills("Tipo de jornada:", opciones, selection_mode="multi", default="Normal")

        st.write("---")
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_corte = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin Jornada", key="hora_fin")
        
        st.write("---")
        i1, i2, i3 = st.columns(3)
        inc_com = i1.checkbox("❌ No comida")
        inc_cor = i1.checkbox("⏱️ No 15 min")
        inc_tur = i2.checkbox("📉 Turnaround")
        inc_kms = i2.checkbox("🚗 Kms")
        inc_die = i3.checkbox("🍴 Dietas")
        inc_otr = i3.checkbox("❓ Otros")
        obs = st.text_area("📝 Notas")

        if st.button("💾 Guardar Fichaje"):
            if not tipo_dia_lista:
                st.error("Selecciona al menos una etiqueta.")
            else:
                df_f_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=1)
                t_str = ", ".join(tipo_dia_lista)
                alertas = [k for k, v in {"No comida":inc_com,"No 15m":inc_cor,"Turnaround":inc_tur,"Km":inc_kms,"Dietas":inc_die,"Otros":inc_otr}.items() if v]
                
                nuevo = pd.DataFrame([{
                    "ID_Usuario": "User1", "Proyecto": proyecto_sel, "Fecha": str(fecha),
                    "Tipo_Dia": t_str, "Hora_Inicio": str(h_ini)[:5], "Corte_Camara": str(h_corte)[:5],
                    "Hora_Fin_Jornada": str(h_fin)[:5], "Comida": "No" if inc_com else "Sí",
                    "Incidencias": ", ".join(alertas), "Observaciones": obs
                }])
                
                conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_existentes, nuevo], ignore_index=True))
                st.cache_data.clear()
                st.toast("✅ Datos guardados correctamente") # Aviso discreto en la esquina
                st.success("Jornada registrada.")

# --- SECCIÓN: HISTORIAL ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    df_f = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    df_p = conn.read(worksheet="Config_Proyectos", ttl=1)
    
    if df_p.empty:
        st.info("No hay proyecto activo.")
    elif df_f.empty:
        st.info(f"Proyecto: {df_p.iloc[0]['Proyecto']}. Sin jornadas todavía.")
    else:
        proyecto_info = df_p.iloc[0]
        st.subheader(f"🎥 {proyecto_info['Proyecto']}")
        
        df_f['Fecha'] = pd.to_datetime(df_f['Fecha'])
        start = pd.to_datetime(proyecto_info['Fecha_Inicio'])
        df_f['Semana'] = df_f['Fecha'].apply(lambda x: (math.floor((x-start).days/7)+1) if (x-start).days >=0 else (math.floor((x-start).days/7)))
        
        for s in sorted(df_f['Semana'].unique(), reverse=True):
            titulo = f"📂 Semana {s}" if s > 0 else f"📂 Pre-prod (S{s})"
            with st.expander(titulo, expanded=True):
                d_s = df_f[df_f['Semana'] == s].sort_values("Fecha")
                d_s['Día'] = d_s['Fecha'].dt.strftime('%d/%m/%Y')
                st.table(d_s[["Día", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Incidencias"]])
