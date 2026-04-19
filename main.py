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

# --- LÓGICA DE SINCRONIZACIÓN DE HORAS (RESTAURADA) ---
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
    
    df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
    
    if not df_f_user.empty:
        csv = df_f_user.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", data=csv, file_name=f"rodaje_{user_id}.csv")

# --- 1. PROYECTO (CON HORAS DE CONTRATO) ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración del Proyecto")
    df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
    df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
    
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        st.success(f"Proyecto: **{p['Proyecto']}**")
        st.write(f"📅 Inicio: {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")
        st.write(f"⏰ Jornada: {p['Horas_Contrato']}h diarias / {p['Horas_Semana']}h semanales")
        
        if st.button("🗑️ Resetear mi proyecto"):
            df_p_new = df_p_all[df_p_all['ID_Usuario'] != user_id]
            conn.update(worksheet="Config_Proyectos", data=df_p_new)
            st.cache_data.clear()
            st.rerun()
    else:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre del Rodaje")
            f = st.date_input("Día 1", datetime.now(), format="DD/MM/YYYY")
            col1, col2 = st.columns(2)
            h_dia = col1.number_input("Horas/jornada (ej: 8 o 9)", value=9)
            h_sem = col2.number_input("Horas/semana (ej: 40 o 45)", value=45)
            
            if st.form_submit_button("Crear Proyecto"):
                if n:
                    nuevo = pd.DataFrame([{
                        "ID_Usuario": user_id, "Proyecto": n, "Fecha_Inicio": str(f), 
                        "Horas_Contrato": h_dia, "Horas_Semana": h_sem, "Estado": "Activo"
                    }])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_all, nuevo], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

# --- 2. FICHAR (CON CHECKBOXES RESTAURADOS) ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
    df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
    
    if df_p_user.empty:
        st.warning("Configura tu proyecto primero.")
    else:
        fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
        tags = st.pills("Tipo:", ["Normal", "Festivo", "Viaje", "Pruebas", "Carga", "Oficina"], default="Normal")
        
        c1, c2, c3 = st.columns(3)
        h1 = c1.time_input("🕒 Call", time(8, 0))
        # Recuperada sincronización Wrap -> Fin
        h2 = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h3 = c3.time_input("🚚 Fin", key="hora_fin")
        
        st.write("---")
        # Restaurados los Checkboxes de incidencias
        st.markdown("**Incidencias / Avisos:**")
        col_i1, col_i2 = st.columns(2)
        i_comida = col_i1.checkbox("❌ No comida")
        i_15min = col_i1.checkbox("⏱️ No 15 min")
        i_turn = col_i2.checkbox("📉 Turnaround")
        i_dietas = col_i2.checkbox("🍴 Dietas")
        obs = st.text_area("Notas / Observaciones")

        if st.button("💾 Guardar Jornada"):
            df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
            alertas = [k for k, v in {"No comida":i_comida, "No 15m":i_15min, "Turnaround":i_turn, "Dietas":i_dietas}.items() if v]
            h_totales = calcular_duracion(h1, h3)
            
            nuevo = pd.DataFrame([{
                "ID_Usuario": user_id, "Proyecto": df_p_user.iloc[0]['Proyecto'], "Fecha": str(fecha),
                "Tipo_Dia": tags, "Hora_Inicio": str(h1)[:5], "Hora_Fin_Jornada": str(h3)[:5],
                "Horas_Totales": h_totales, "Incidencias": ", ".join(alertas), "Observaciones": obs
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
            st.cache_data.clear()
            st.toast("✅ Guardado")
            st.success(f"Jornada de {h_totales}h registrada.")

# --- 3. HISTORIAL ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
    df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
    
    if not df_f_user.empty:
        df_f_user['Fecha'] = pd.to_datetime(df_f_user['Fecha'])
        df_display = df_f_user.sort_values("Fecha", ascending=False).copy()
        df_display['Día'] = df_display['Fecha'].dt.strftime('%d/%m/%Y')
        
        st.metric("Total Horas Proyecto", f"{df_f_user['Horas_Totales'].sum()} h")
        st.table(df_display[["Día", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Horas_Totales", "Incidencias"]])
        
        with st.expander("✏️ Gestionar Jornadas"):
            fecha_sel = st.selectbox("Selecciona día:", df_display['Día'].unique())
            if st.button("Eliminar esta jornada"):
                f_dt = datetime.strptime(fecha_sel, '%d/%m/%Y').strftime('%Y-%m-%d')
                df_f_new = df_f_all[~((df_f_all['ID_Usuario'] == user_id) & (df_f_all['Fecha'] == f_dt))]
                conn.update(worksheet="Fichajes_Diarios", data=df_f_new)
                st.cache_data.clear()
                st.rerun()
