import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time, timedelta
import math

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN: CÁLCULO DE DURACIÓN ---
def calcular_duracion(h_ini, h_fin):
    hoy = datetime.today()
    inicio = datetime.combine(hoy, h_ini)
    fin = datetime.combine(hoy, h_fin)
    if fin <= inicio: fin += timedelta(days=1)
    return round((fin - inicio).total_seconds() / 3600, 2)

# --- SINCRONIZACIÓN DE HORAS ---
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
        df_p_all = conn.read(worksheet="Config_Proyectos", ttl=1)
        df_p_user = df_p_all[df_p_all['ID_Usuario'] == user_id] if not df_p_all.empty else pd.DataFrame()
        
        # --- LÓGICA DE EXPORTACIÓN RECUPERADA Y MEJORADA ---
        df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl=1)
        df_f_user = df_f_all[df_f_all['ID_Usuario'] == user_id] if not df_f_all.empty else pd.DataFrame()
        
        if not df_f_user.empty and not df_p_user.empty:
            # Añadimos la columna de semana al CSV
            df_export = df_f_user.copy()
            df_export['Fecha'] = pd.to_datetime(df_export['Fecha'])
            f_ini_p = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio'])
            
            def calc_semana_csv(f):
                d = (f - f_ini_p).days
                return (math.floor(d / 7) + 1) if d >= 0 else math.floor(d / 7)
            
            df_export['Semana'] = df_export['Fecha'].apply(calc_semana_csv)
            df_export = df_export.sort_values("Fecha")
            
            csv = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Descargar CSV (con Semanas)", data=csv, file_name=f"historial_{user_id}.csv", mime="text/csv")
    except:
        df_p_user = pd.DataFrame()
        df_f_user = pd.DataFrame()

# --- 1. PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        st.success(f"Proyecto: **{p['Proyecto']}**")
        st.info(f"Día 1: {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")
        if st.button("🗑️ Resetear mi proyecto"):
            df_p_new = df_p_all[df_p_all['ID_Usuario'] != user_id]
            conn.update(worksheet="Config_Proyectos", data=df_p_new)
            st.cache_data.clear()
            st.rerun()
    else:
        with st.form("nuevo_p"):
            n = st.text_input("Nombre del Rodaje")
            f = st.date_input("Día 1 (Hoy por defecto)", datetime.now(), format="DD/MM/YYYY")
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
    if df_p_user.empty:
        st.warning("Configura tu proyecto primero.")
    else:
        fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
        etiquetas = ["Normal", "Viaje", "Pruebas", "Carga", "Oficina", "Localización", "Chequeo"]
        tags = st.pills("Tipo:", etiquetas, default="Normal")
        
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
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
                "ID_Usuario": user_id, "Proyecto": df_p_user.iloc[0]['Proyecto'], "Fecha": str(fecha),
                "Tipo_Dia": tags, "Hora_Inicio": str(h_ini)[:5], "Corte_Camara": str(h_wrap)[:5],
                "Hora_Fin_Jornada": str(h_fin)[:5], "Horas_Totales": h_totales, 
                "Incidencias": ", ".join(alertas), "Observaciones": obs
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
            st.cache_data.clear()
            st.success(f"Guardado: {h_totales}h")
            st.toast("✅ Registrado")

# --- 3. HISTORIAL POR SEMANAS ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    if not df_f_user.empty and not df_p_user.empty:
        df_f_user['Fecha'] = pd.to_datetime(df_f_user['Fecha'])
        fecha_inicio_rodaje = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio'])
        
        def calc_semana(fecha_jornada):
            dias_dif = (fecha_jornada - fecha_inicio_rodaje).days
            return (math.floor(dias_dif / 7) + 1) if dias_dif >= 0 else math.floor(dias_dif / 7)

        df_f_user['Semana'] = df_f_user['Fecha'].apply(calc_semana)
        st.metric("Total Proyecto", f"{df_f_user['Horas_Totales'].sum()} h")
        st.write("---")

        for sem in sorted(df_f_user['Semana'].unique(), reverse=True):
            df_sem = df_f_user[df_f_user['Semana'] == sem].sort_values("Fecha")
            horas_sem = df_sem['Horas_Totales'].sum()
            titulo_sem = f"📂 Semana {sem}" if sem > 0 else f"📂 Pre-producción (S{sem})"
            with st.expander(f"{titulo_sem} — {horas_sem}h totales"):
                df_print = df_sem.copy()
                df_print['Día'] = df_print['Fecha'].dt.strftime('%d/%m/%Y')
                st.table(df_print[["Día", "Tipo_Dia", "Hora_Inicio", "Corte_Camara", "Hora_Fin_Jornada", "Horas_Totales", "Incidencias"]])
        
        st.markdown("---")
        with st.expander("✏️ Gestionar Jornadas (Editar o Eliminar)"):
            df_f_user['Día_Str'] = df_f_user['Fecha'].dt.strftime('%d/%m/%Y')
            fecha_sel = st.selectbox("Selecciona día:", df_f_user['Día_Str'].unique())
            datos_dia = df_f_user[df_f_user['Día_Str'] == fecha_sel].iloc[0]
            
            col_ed1, col_ed2 = st.columns(2)
            nueva_h_ini = col_ed1.time_input("Nueva Hora Inicio", datetime.strptime(datos_dia['Hora_Inicio'], "%H:%M").time())
            nueva_h_fin = col_ed2.time_input("Nueva Hora Fin", datetime.strptime(datos_dia['Hora_Fin_Jornada'], "%H:%M").time())
            nuevas_obs = st.text_area("Notas / Observaciones", value=datos_dia['Observaciones'])
            
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("💾 Guardar Cambios"):
                f_dt = datetime.strptime(fecha_sel, '%d/%m/%Y').strftime('%Y-%m-%d')
                df_f_new = df_f_all[~((df_f_all['ID_Usuario'] == user_id) & (df_f_all['Fecha'] == f_dt))]
                h_totales_edit = calcular_duracion(nueva_h_ini, nueva_h_fin)
                nueva_fila = pd.DataFrame([{
                    "ID_Usuario": user_id, "Proyecto": datos_dia['Proyecto'], "Fecha": f_dt,
                    "Tipo_Dia": datos_dia['Tipo_Dia'], "Hora_Inicio": str(nueva_h_ini)[:5], 
                    "Corte_Camara": datos_dia['Corte_Camara'], "Hora_Fin_Jornada": str(nueva_h_fin)[:5], 
                    "Horas_Totales": h_totales_edit, "Incidencias": datos_dia['Incidencias'], "Observaciones": nuevas_obs
                }])
                conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_new, nueva_fila], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
                
            if c_btn2.button("🗑️ Eliminar jornada"):
                f_dt = datetime.strptime(fecha_sel, '%d/%m/%Y').strftime('%Y-%m-%d')
                df_f_new = df_f_all[~((df_f_all['ID_Usuario'] == user_id) & (df_f_all['Fecha'] == f_dt))]
                conn.update(worksheet="Fichajes_Diarios", data=df_f_new)
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("No hay datos que mostrar.")
