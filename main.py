import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time, timedelta
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN: CÁLCULO DE HORAS (Anti-Noche) ---
def calcular_duracion(h_ini, h_fin):
    # Usamos una fecha base para poder restar
    hoy = datetime.today()
    inicio = datetime.combine(hoy, h_ini)
    fin = datetime.combine(hoy, h_fin)
    if fin <= inicio: # Si el fin es antes del inicio, es jornada nocturna
        fin += timedelta(days=1)
    diferencia = fin - inicio
    return round(diferencia.total_seconds() / 3600, 2)

# --- ESTADO DE SESIÓN ---
if 'hora_wrap' not in st.session_state: st.session_state.hora_wrap = time(19, 0)
if 'hora_fin' not in st.session_state: st.session_state.hora_fin = time(19, 0)

def actualizar_fin():
    st.session_state.hora_fin = st.session_state.hora_wrap

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    user_id = st.text_input("📧 Email", value="invitado@correo.com").strip()
    st.markdown("---")
    opcion_menu = st.selectbox("Menú", ["🏗️ Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"], index=1)
    
    # Exportar solo mis datos
    df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
    
    if not df_f_user.empty:
        csv = df_f_user.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", data=csv, file_name=f"rodaje_{user_id}.csv")

# --- LÓGICA: PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Gestión de Proyecto")
    df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
    df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
    
    if not df_p_user.empty:
        st.success(f"Proyecto activo: **{df_p_user.iloc[0]['Proyecto']}**")
        if st.button("🗑️ Borrar mi proyecto y empezar de cero"):
            df_p_new = df_p_all[df_p_all['ID_Usuario'] != user_id]
            conn.update(worksheet="Config_Proyectos", data=df_p_new)
            st.cache_data.clear()
            st.rerun()
    else:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre del Rodaje")
            f = st.date_input("Día 1", datetime.now())
            if st.form_submit_button("Crear"):
                nuevo = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": n, "Fecha_Inicio": str(f), "Estado": "Activo"}])
                conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_all, nuevo], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

# --- LÓGICA: FICHAR ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Nuevo Fichaje")
    df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
    df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
    
    if df_p_user.empty:
        st.warning("Crea un proyecto primero.")
    else:
        with st.form("fichaje_form"):
            fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
            tags = st.pills("Tipo:", ["Normal", "Festivo", "Viaje", "Pruebas", "Carga", "Oficina"], default="Normal")
            c1, c2, c3 = st.columns(3)
            h1 = c1.time_input("🕒 Call", time(8, 0))
            h2 = c2.time_input("🎥 Wrap", time(19, 0))
            h3 = c3.time_input("🚚 Fin", time(19, 0))
            obs = st.text_area("Notas")
            
            if st.form_submit_button("💾 Guardar Jornada"):
                df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
                h_totales = calcular_duracion(h1, h3)
                
                nuevo = pd.DataFrame([{
                    "ID_Usuario": user_id, "Proyecto": df_p_user.iloc[0]['Proyecto'], 
                    "Fecha": str(fecha), "Tipo_Dia": tags, "Hora_Inicio": str(h1)[:5], 
                    "Hora_Fin_Jornada": str(h3)[:5], "Horas_Totales": h_totales, "Observaciones": obs
                }])
                conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
                st.cache_data.clear()
                st.toast("✅ Guardado")

# --- LÓGICA: HISTORIAL Y EDICIÓN ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
    
    if not df_f_user.empty:
        df_f_user['Fecha'] = pd.to_datetime(df_f_user['Fecha'])
        
        # Resumen de horas totales
        total_proyecto = df_f_user['Horas_Totales'].sum()
        st.metric("Total Horas Acumuladas", f"{total_proyecto} h")

        # Mostrar tabla
        df_display = df_f_user.sort_values("Fecha", ascending=False).copy()
        df_display['Día'] = df_display['Fecha'].dt.strftime('%d/%m/%Y')
        st.table(df_display[["Día", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Horas_Totales"]])

        # --- SECCIÓN DE EDICIÓN ---
        st.markdown("---")
        with st.expander("✏️ Editar o Eliminar una Jornada"):
            fecha_edit = st.selectbox("Selecciona el día a modificar:", df_display['Día'].unique())
            opcion_edit = st.radio("Acción:", ["Editar Notas", "Eliminar Jornada"], horizontal=True)
            
            if st.button("Ejecutar Cambio"):
                # Filtramos para quitar esa fila específica
                fecha_dt_str = datetime.strptime(fecha_edit, '%d/%m/%Y').strftime('%Y-%m-%d')
                
                if opcion_edit == "Eliminar Jornada":
                    df_f_new = df_f_all[~((df_f_all['ID_Usuario'] == user_id) & (df_f_all['Fecha'] == fecha_dt_str))]
                    conn.update(worksheet="Fichajes_Diarios", data=df_f_new)
                    st.success("Jornada eliminada.")
                
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("Sin datos registrados.")
