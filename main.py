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
            
            # PREPARAR TABLA ÚNICA (SIN TEXTO EXTRA ARRIBA PARA EVITAR DESPLAZAMIENTOS)
            df_csv = df_f_user.copy()
            df_csv['Fecha_DT'] = pd.to_datetime(df_csv['Fecha'])
            f_ini_p = pd.to_datetime(p_info['Fecha_Inicio'])
            
            # Cálculo de semana: Será la Columna A
            df_csv['Semana'] = df_csv['Fecha_DT'].apply(lambda f: (math.floor((f - f_ini_p).days / 7) + 1))
            df_csv = df_csv.sort_values("Fecha_DT")
            
            # Formateo de columnas
            for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                df_csv[col] = df_csv[col].astype(str).str[:5]
            
            # Selección final: El orden aquí define las columnas A, B, C...
            df_export = df_csv[['Semana', 'Fecha', 'Tipo_Dia', 'Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada', 'Incidencias', 'Observaciones']].copy()
            df_export.columns = ['Semana', 'Fecha', 'Tipo', 'Call', 'Corte', 'Fin', 'Alertas', 'Notas']

            # Generamos el CSV directamente con la tabla
            output = io.StringIO()
            df_export.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
            
            st.download_button(
                label="📥 Descargar Reporte (Tabla Pura)",
                data=output.getvalue().encode('utf-8-sig'),
                file_name=f"reporte_{user_id}_v8.csv",
                mime="text/csv"
            )
    except:
        pass

# --- 1. PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        with st.container(border=True):
            st.subheader(f"🎥 {p['Proyecto']}")
            st.info(f"📅 Inicio Rodaje: {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")

        with st.expander("✏️ Editar"):
            with st.form("edit_p"):
                nuevo_n = st.text_input("Nombre del Rodaje", value=p['Proyecto'])
                nueva_f = st.date_input("Día 1", pd.to_datetime(p['Fecha_Inicio']))
                h_dia = st.number_input("Horas día", value=int(p['Horas_Contrato']))
                h_sem = st.number_input("Horas semana", value=int(p['Horas_Semana']))
                if st.form_submit_button("Actualizar"):
                    df_p_new = df_p_all[df_p_all['ID_Usuario'].str.lower() != user_id]
                    editado = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": nuevo_n, "Fecha_Inicio": str(nueva_f), "Horas_Contrato": h_dia, "Horas_Semana": h_sem, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_new, editado], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()
    else:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre del Rodaje")
            f = st.date_input("Día 1", datetime.now())
            h_d = st.number_input("Horas día", value=9)
            h_s = st.number_input("Horas semana", value=45)
            if st.form_submit_button("Crear Proyecto"):
                if n:
                    nuevo = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": n, "Fecha_Inicio": str(f), "Horas_Contrato": h_d, "Horas_Semana": h_s, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_all, nuevo], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

# --- 2. FICHAR ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    if df_p_user.empty: st.warning("Configura tu proyecto primero.")
    else:
        nombre_p = df_p_user.iloc[0]['Proyecto']
        fecha = st.date_input("📅 Fecha", datetime.now())
        tags = st.pills("Tipo:", ["Normal", "Viaje", "Pruebas", "Carga", "Oficina", "Localización", "Chequeo"], default="Normal")
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_wrap = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin", key="hora_fin")
        col_i = st.columns(2)
        alertas = {
            "No comida": col_i[0].checkbox("❌ No comida"),
            "No 15 min": col_i[0].checkbox("⏱️ No 15 min"),
            "Turnaround": col_i[1].checkbox("📉 Turnaround"),
            "Dietas": col_i[1].checkbox("🍴 Dietas")
        }
        obs = st.text_area("Notas")
        
        if st.button("💾 Guardar Jornada"):
            h_tot = calcular_duracion(h_ini, h_fin)
            inc = [k for k, v in alertas.items() if v]
            nuevo = pd.DataFrame([{
                "ID_Usuario": user_id, "Proyecto": nombre_p, "Fecha": str(fecha),
                "Tipo_Dia": tags, "Hora_Inicio": str(h_ini)[:5], "Corte_Camara": str(h_wrap)[:5],
                "Hora_Fin_Jornada": str(h_fin)[:5], "Horas_Totales": h_tot, 
                "Incidencias": ", ".join(inc), "Observaciones": obs
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

# --- 3. HISTORIAL ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    if not df_f_user.empty and not df_p_user.empty:
        df_f_user['Fecha_DT'] = pd.to_datetime(df_f_user['Fecha'])
        f_ini = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio'])
        df_f_user['Semana'] = df_f_user['Fecha_DT'].apply(lambda fj: (math.floor((fj - f_ini).days / 7) + 1))
        
        for sem in sorted(df_f_user['Semana'].unique(), reverse=True):
            df_sem = df_f_user[df_f_user['Semana'] == sem].sort_values("Fecha_DT").copy()
            with st.expander(f"📂 Semana {sem} — {round(df_sem['Horas_Totales'].sum(), 1)}h"):
                df_tab = df_sem.copy()
                df_tab['Día'] = df_tab['Fecha_DT'].dt.strftime('%d/%m/%Y')
                st.dataframe(df_tab[["Día", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Horas_Totales"]], hide_index=True)
