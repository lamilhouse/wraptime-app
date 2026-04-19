import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time, timedelta
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN: CÁLCULO DE HORAS ---
def calcular_duracion(h_ini, h_fin):
    hoy = datetime.today()
    inicio = datetime.combine(hoy, h_ini)
    fin = datetime.combine(hoy, h_fin)
    if fin <= inicio: fin += timedelta(days=1)
    return round((fin - inicio).total_seconds() / 3600, 2)

# --- LÓGICA DE SINCRONIZACIÓN DE HORAS ---
if 'hora_wrap' not in st.session_state: st.session_state.hora_wrap = time(19, 0)
if 'hora_fin' not in st.session_state: st.session_state.hora_fin = time(19, 0)

def actualizar_fin():
    st.session_state.hora_fin = st.session_state.hora_wrap

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    user_id = st.text_input("📧 Email", value="tu_email@correo.com").strip()
    st.markdown("---")
    opcion_menu = st.selectbox("Menú", ["🏗️ Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"], index=1)
    
    try:
        df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
        df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
    except:
        df_f_user = pd.DataFrame()

# --- 1. PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
    df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
    
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        st.success(f"Proyecto: **{p['Proyecto']}**")
        if st.button("🗑️ Borrar mi proyecto"):
            df_p_new = df_p_all[df_p_all['ID_Usuario'] != user_id]
            conn.update(worksheet="Config_Proyectos", data=df_p_new)
            st.cache_data.clear()
            st.rerun()
    else:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre del Rodaje")
            f = st.date_input("Día 1", datetime.now(), format="DD/MM/YYYY")
            c1, c2 = st.columns(2)
            h_dia = c1.number_input("Horas jornada contrato", value=9)
            h_sem = c2.number_input("Horas semana contrato", value=45)
            if st.form_submit_button("Crear Proyecto"):
                if n:
                    nuevo = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": n, "Fecha_Inicio": str(f), "Horas_Contrato": h_dia, "Horas_Semana": h_sem, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_all, nuevo], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

# --- 2. FICHAR ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
    df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
    
    if df_p_user.empty:
        st.warning("Configura tu proyecto primero.")
    else:
        fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
        tags = st.pills("Tipo:", ["Rodaje", "Chequeo", "Viaje", "Pruebas", "Carga", "Localización", "Oficina"], default="Normal")
        
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        # Sincronización activa: al cambiar Wrap se mueve Fin Camión
        h_wrap = c2.time_input("🎥 Wrap (Cámara)", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin (Camión)", key="hora_fin")
        
        st.write("---")
        col_i1, col_i2 = st.columns(2)
        i_comida = col_i1.checkbox("❌ No comida")
        i_15min = col_i1.checkbox("⏱️ No 15 min")
        i_turn = col_i2.checkbox("📉 Turnaround")
        i_dietas = col_i2.checkbox("🍴 Dietas")
        obs = st.text_area("Notas")

        if st.button("💾 Guardar Jornada"):
            df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
            h_totales = calcular_duracion(h_ini, h_fin)
            alertas = [k for k, v in {"No comida":i_comida, "No 15m":i_15min, "Turnaround":i_turn, "Dietas":i_dietas}.items() if v]
            
            nuevo = pd.DataFrame([{
                "ID_Usuario": user_id, 
                "Proyecto": df_p_user.iloc[0]['Proyecto'], 
                "Fecha": str(fecha),
                "Tipo_Dia": tags, 
                "Hora_Inicio": str(h_ini)[:5], 
                "Corte_Camara": str(h_wrap)[:5], # <--- Columna restaurada
                "Hora_Fin_Jornada": str(h_fin)[:5], 
                "Horas_Totales": h_totales, 
                "Incidencias": ", ".join(alertas), 
                "Observaciones": obs
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
            st.cache_data.clear()
            st.success(f"Guardado: {h_totales}h")
            st.toast("✅ Registrado")

# --- 3. HISTORIAL ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
    
    if not df_f_user.empty:
        df_f_user['Fecha'] = pd.to_datetime(df_f_user['Fecha'])
        df_display = df_f_user.sort_values("Fecha", ascending=False).copy()
        df_display['Día'] = df_display['Fecha'].dt.strftime('%d/%m/%Y')
        
        st.metric("Total Horas", f"{df_f_user['Horas_Totales'].sum()} h")
        
        # Tabla con todas las columnas críticas
        st.table(df_display[["Día", "Tipo_Dia", "Hora_Inicio", "Corte_Camara", "Hora_Fin_Jornada", "Horas_Totales", "Incidencias"]])
        
        with st.expander("🗑️ Borrar jornada"):
            fecha_sel = st.selectbox("Día:", df_display['Día'].unique())
            if st.button("Confirmar eliminación"):
                f_dt = datetime.strptime(fecha_sel, '%d/%m/%Y').strftime('%Y-%m-%d')
                df_f_new = df_f_all[~((df_f_all['ID_Usuario'] == user_id) & (df_f_all['Fecha'] == f_dt))]
                conn.update(worksheet="Fichajes_Diarios", data=df_f_new)
                st.cache_data.clear()
                st.rerun()
