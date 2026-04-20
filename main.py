import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time, timedelta
import math
import io

# Configuración inicial
st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN: CÁLCULO DE DURACIÓN ---
def calcular_duracion(h_ini, h_fin):
    hoy = datetime.today()
    inicio = datetime.combine(hoy, h_ini)
    fin = datetime.combine(hoy, h_fin)
    if fin <= inicio: fin += timedelta(days=1)
    return round((fin - inicio).total_seconds() / 3600, 1)

def actualizar_fin():
    st.session_state.hora_fin = st.session_state.hora_wrap

# --- LÓGICA DE SEMANAS (UNIFICADA) ---
def obtener_semana_prod(fecha_fichaje, fecha_inicio_rodaje):
    delta_days = (fecha_fichaje - fecha_inicio_rodaje).days
    if delta_days >= 0:
        return (delta_days // 7) + 1
    else:
        return (delta_days // 7)

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    user_id = st.text_input("📧 Email", value="tu_email@correo.com").strip().lower()
    st.markdown("---")
    opcion_menu = st.selectbox("Menú", ["🏗️ Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"], index=1)
    
    try:
        df_p_all = conn.read(worksheet="Config_Proyectos", ttl="0s")
        df_p_user = df_p_all[df_p_all['ID_Usuario'].str.lower() == user_id] if not df_p_all.empty else pd.DataFrame()
        
        df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl="0s")
        df_f_user = df_f_all[df_f_all['ID_Usuario'].str.lower() == user_id] if not df_f_all.empty else pd.DataFrame()
        
        if not df_f_user.empty and not df_p_user.empty:
            p_info = df_p_user.iloc[0]
            f_ini_p = pd.to_datetime(p_info['Fecha_Inicio']).date()
            
            # EXPORTACIÓN CSV
            df_csv = df_f_user.copy()
            df_csv['Fecha_DT'] = pd.to_datetime(df_csv['Fecha']).dt.date
            df_csv['Semana'] = df_csv['Fecha_DT'].apply(lambda x: obtener_semana_prod(x, f_ini_p))
            df_csv = df_csv.sort_values("Fecha_DT")
            
            # Limpieza estricta de horas para CSV (HH:MM)
            for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                df_csv[col] = df_csv[col].astype(str).str.strip().str[:5]
            
            df_export = df_csv[['Semana', 'Fecha', 'Tipo_Dia', 'Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada', 'Incidencias', 'Observaciones']].copy()
            df_export.columns = ['Semana', 'Fecha', 'Tipo', 'Call', 'Corte', 'Fin', 'Alertas', 'Notas']

            output = io.StringIO()
            df_export.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
            
            st.download_button(
                label="📥 Descargar Reporte CSV",
                data=output.getvalue().encode('utf-8-sig'),
                file_name=f"reporte_{user_id}.csv",
                mime="text/csv"
            )
    except:
        pass

# --- 1. PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        st.subheader(f"🎥 {p['Proyecto']}")
        st.info(f"📅 Inicio Rodaje: {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")

# --- 2. FICHAR ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    if df_p_user.empty: st.warning("Configura tu proyecto.")
    else:
        fecha = st.date_input("📅 Fecha", datetime.now())
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_wrap = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin", key="hora_fin")
        
        if st.button("💾 Guardar"):
            h_tot = calcular_duracion(h_ini, h_fin)
            nuevo = pd.DataFrame([{
                "ID_Usuario": user_id, "Proyecto": df_p_user.iloc[0]['Proyecto'], "Fecha": str(fecha),
                "Tipo_Dia": "Normal", "Hora_Inicio": str(h_ini)[:5], "Corte_Camara": str(h_wrap)[:5],
                "Hora_Fin_Jornada": str(h_fin)[:5], "Horas_Totales": h_tot, 
                "Incidencias": "", "Observaciones": ""
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
            st.cache_data.clear()
            st.success("¡Guardado!")
            st.rerun()

# --- 3. HISTORIAL (REPARADO SIN SEGUNDOS) ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    if not df_f_user.empty and not df_p_user.empty:
        df_f_user['Fecha_DT'] = pd.to_datetime(df_f_user['Fecha']).dt.date
        f_ini = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio']).date()
        df_f_user['Semana'] = df_f_user['Fecha_DT'].apply(lambda x: obtener_semana_prod(x, f_ini))
        
        for sem in sorted(df_f_user['Semana'].unique(), reverse=True):
            df_sem = df_f_user[df_f_user['Semana'] == sem].sort_values("Fecha_DT").copy()
            
            # Limpiar segundos para la visualización en la app
            for c in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                df_sem[c] = df_sem[c].astype(str).str.strip().str[:5]
            
            txt = f"Semana {sem}" if sem > 0 else f"Pre-producción (S{sem})"
            with st.expander(f"📂 {txt} — Total: {round(df_sem['Horas_Totales'].sum(), 1)}h"):
                df_visual = df_sem.rename(columns={
                    "Fecha": "Día", "Hora_Inicio": "Call", 
                    "Hora_Fin_Jornada": "Fin", "Horas_Totales": "H"
                })
                st.dataframe(df_visual[["Día", "Call", "Fin", "H"]], hide_index=True)
