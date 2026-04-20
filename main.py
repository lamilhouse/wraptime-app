import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time, timedelta
import math
import re
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

# --- SINCRONIZACIÓN DE HORAS ---
if 'hora_wrap' not in st.session_state: st.session_state.hora_wrap = time(19, 0)
if 'hora_fin' not in st.session_state: st.session_state.hora_fin = time(19, 0)

def actualizar_fin():
    st.session_state.hora_fin = st.session_state.hora_wrap

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🎬 WrapTime Lite")
    user_id = st.text_input("📧 Email", value="tu_email@correo.com").strip().lower()
    st.markdown("---")
    opcion_menu = st.selectbox("Menú", ["🏗️ Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"], index=1)
    
    try:
        # Carga crítica de datos
        df_p_all = conn.read(worksheet="Config_Proyectos", ttl="0s")
        df_p_user = df_p_all[df_p_all['ID_Usuario'].str.lower() == user_id] if not df_p_all.empty else pd.DataFrame()
        
        df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl="0s")
        df_f_user = df_f_all[df_f_all['ID_Usuario'].str.lower() == user_id] if not df_f_all.empty else pd.DataFrame()
        
        # Generación de CSV (Solo si hay datos)
        if not df_f_user.empty and not df_p_user.empty:
            p_info = df_p_user.iloc[0]
            
            # Tabla de datos
            df_csv = df_f_user.copy()
            df_csv['Fecha_DT'] = pd.to_datetime(df_csv['Fecha'])
            f_ini_p = pd.to_datetime(p_info['Fecha_Inicio'])
            df_csv['Semana'] = df_csv['Fecha_DT'].apply(lambda f: (math.floor((f - f_ini_p).days / 7) + 1))
            df_csv = df_csv.sort_values("Fecha_DT")
            
            # Limpieza de horas
            for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                df_csv[col] = df_csv[col].astype(str).str[:5]
            
            df_csv_final = df_csv[['Semana', 'Fecha', 'Tipo_Dia', 'Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada', 'Incidencias', 'Observaciones']].copy()
            df_csv_final.columns = ['Semana', 'Fecha', 'Tipo', 'Call', 'Corte', 'Fin', 'Alertas', 'Notas']

            # Construcción del archivo con tablas separadas
            output = io.StringIO()
            output.write("TABLA 1: DATOS DEL PROYECTO\n")
            output.write(f"PROYECTO;{p_info['Proyecto']}\n")
            output.write(f"USUARIO;{user_id}\n")
            output.write(f"CONTRATO;{p_info['Horas_Contrato']}h dia\n")
            output.write("\n\n")
            output.write("TABLA 2: DETALLE DE JORNADAS\n")
            df_csv_final.to_csv(output, index=False, sep=';', lineterminator='\n', encoding='utf-8-sig')
            
            st.download_button("📥 Descargar Reporte CSV", data=output.getvalue().encode('utf-8-sig'), file_name=f"reporte_{user_id}.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

# --- 1. PROYECTO (Reforzado) ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        with st.container(border=True):
            st.subheader(f"🎥 {p['Proyecto']}")
            c1, c2 = st.columns(2)
            c1.metric("Jornada Contrato", f"{p['Horas_Contrato']} h")
            c2.metric("Semana Contrato", f"{p['Horas_Semana']} h")
            st.info(f"📅 Inicio Rodaje: {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")

        with st.expander("✏️ Editar proyecto"):
            with st.form("edit_p"):
                # IMPORTANTE: Mantener 'Nombre del Rodaje' para que enlace bien
                nuevo_n = st.text_input("Nombre del Rodaje", value=p['Proyecto'])
                nueva_f = st.date_input("Día 1", pd.to_datetime(p['Fecha_Inicio']))
                col_h1, col_h2 = st.columns(2)
                n_h_dia = col_h1.number_input("Horas día", value=int(p['Horas_Contrato']))
                n_h_sem = col_h2.number_input("Horas semana", value=int(p['Horas_Semana']))
                if st.form_submit_button("Actualizar Proyecto"):
                    df_p_new = df_p_all[df_p_all['ID_Usuario'].str.lower() != user_id]
                    editado = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": nuevo_n, "Fecha_Inicio": str(nueva_f), "Horas_Contrato": n_h_dia, "Horas_Semana": n_h_sem, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_new, editado], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()
    else:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre del Rodaje")
            f = st.date_input("Día 1", datetime.now())
            c1, c2 = st.columns(2)
            h_dia = c1.number_input("Horas día", value=9)
            h_sem = c2.number_input("Horas semana", value=45)
            if st.form_submit_button("Crear Proyecto"):
                if n:
                    nuevo = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": n, "Fecha_Inicio": str(f), "Horas_Contrato": h_dia, "Horas_Semana": h_sem, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_all, nuevo], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

# --- 2. FICHAR (Reforzado) ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    if df_p_user.empty: 
        st.warning("⚠️ No hay ningún proyecto configurado para este email.")
    else:
        # Aseguramos que el nombre del proyecto se hereda correctamente aquí
        nombre_proyecto_actual = df_p_user.iloc[0]['Proyecto']
        fecha = st.date_input("📅 Fecha", datetime.now())
        tags = st.pills("Tipo:", ["Normal", "Viaje", "Pruebas", "Carga", "Oficina", "Localización", "Chequeo"], default="Normal")
        
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_wrap = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin", key="hora_fin")
        
        col_i1, col_i2 = st.columns(2)
        alertas_dic = {
            "No comida": col_i1.checkbox("❌ No comida"),
            "No 15 min": col_i1.checkbox("⏱️ No 15 min"),
            "Turnaround": col_i2.checkbox("📉 Turnaround"),
            "Dietas": col_i2.checkbox("🍴 Dietas")
        }
        obs = st.text_area("Notas")
        
        if st.button("💾 Guardar Jornada"):
            h_totales = calcular_duracion(h_ini, h_fin)
            alertas_activas = [k for k, v in alertas_dic.items() if v]
            nuevo_fichaje = pd.DataFrame([{
                "ID_Usuario": user_id, 
                "Proyecto": nombre_proyecto_actual, 
                "Fecha": str(fecha),
                "Tipo_Dia": tags, 
                "Hora_Inicio": str(h_ini)[:5], 
                "Corte_Camara": str(h_wrap)[:5],
                "Hora_Fin_Jornada": str(h_fin)[:5], 
                "Horas_Totales": h_totales, 
                "Incidencias": ", ".join(alertas_activas), 
                "Observaciones": obs
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo_fichaje], ignore_index=True))
            st.cache_data.clear()
            st.success(f"¡Jornada de {h_totales}h guardada en {nombre_proyecto_actual}!")
            st.rerun()

# --- 3. HISTORIAL (Sin cambios) ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    if not df_f_user.empty and not df_p_user.empty:
        # Lógica de visualización de semanas igual que antes...
        df_f_user['Fecha_DT'] = pd.to_datetime(df_f_user['Fecha'])
        f_ini = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio'])
        df_f_user['Semana'] = df_f_user['Fecha_DT'].apply(lambda fj: (math.floor((fj - f_ini).days / 7) + 1))
        
        st.metric("Total Horas Proyecto", f"{round(df_f_user['Horas_Totales'].sum(), 1)} h")
        
        for sem in sorted(df_f_user['Semana'].unique(), reverse=True):
            df_sem = df_f_user[df_f_user['Semana'] == sem].sort_values("Fecha_DT").copy()
            titulo = f"📂 Semana {sem}" if sem > 0 else f"📂 Pre-producción (S{sem})"
            with st.expander(f"{titulo} — {round(df_sem['Horas_Totales'].sum(), 1)}h"):
                df_tab = df_sem.copy()
                df_tab['Día'] = df_tab['Fecha_DT'].dt.strftime('%d/%m/%Y')
                for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                    df_tab[col] = df_tab[col].astype(str).str[:5]
                df_tab = df_tab.rename(columns={"Tipo_Dia": "Tipo", "Hora_Inicio": "Call", "Corte_Camara": "Corte", "Hora_Fin_Jornada": "Fin", "Horas_Totales": "Horas", "Incidencias": "Alertas", "Observaciones": "Notas"})
                st.dataframe(df_tab[["Día", "Tipo", "Call", "Corte", "Fin", "Horas", "Alertas", "Notas"]], hide_index=True, use_container_width=True)
