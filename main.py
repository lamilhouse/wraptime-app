import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time, timedelta
import math
import io

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="WrapTime Lite", page_icon="🎬", layout="centered")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONES DE APOYO ---
def calcular_duracion(h_ini, h_fin):
    hoy = datetime.today()
    inicio = datetime.combine(hoy, h_ini)
    fin = datetime.combine(hoy, h_fin)
    if fin <= inicio: fin += timedelta(days=1)
    return round((fin - inicio).total_seconds() / 3600, 1)

def obtener_semana_prod(fecha_fichaje, fecha_inicio_rodaje):
    delta_days = (fecha_fichaje - fecha_inicio_rodaje).days
    return (delta_days // 7) + 1 if delta_days >= 0 else (delta_days // 7)

def format_hhmm(val):
    s = str(val).strip()
    return s[:5] if len(s) >= 5 else s

def actualizar_fin():
    st.session_state.hora_fin = st.session_state.hora_wrap

# --- MENÚ LATERAL Y EXPORTACIÓN ---
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
            df_csv = df_f_user.copy()
            df_csv['Fecha_DT'] = pd.to_datetime(df_csv['Fecha']).dt.date
            df_csv['Semana'] = df_csv['Fecha_DT'].apply(lambda x: obtener_semana_prod(x, f_ini_p))
            df_csv['Fecha_Export'] = pd.to_datetime(df_csv['Fecha']).dt.strftime('%d/%m/%Y')
            for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                df_csv[col] = df_csv[col].apply(format_hhmm)
            
            df_export = df_csv[['Semana', 'Fecha_Export', 'Tipo_Dia', 'Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada', 'Incidencias', 'Observaciones']].copy()
            df_export.columns = ['Semana', 'Fecha', 'Tipo', 'Call', 'Corte', 'Fin', 'Alertas', 'Notas']
            output = io.StringIO()
            df_export.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
            st.download_button("📥 Descargar Reporte CSV", data=output.getvalue().encode('utf-8-sig'), file_name=f"reporte_{user_id}.csv", mime="text/csv")
    except: pass

# --- 1. PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        with st.container(border=True):
            st.subheader(f"🎥 {p['Proyecto']}")
            st.write(f"⏱️ **Contrato:** {p['Horas_Contrato']}h día / {p['Horas_Semana']}h semana")
            st.info(f"📅 **Día 1 de rodaje:** {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")

        with st.expander("✏️ Editar Datos del Proyecto"):
            with st.form("edit_p"):
                nuevo_n = st.text_input("Nombre", value=p['Proyecto'])
                nueva_f = st.date_input("Inicio", pd.to_datetime(p['Fecha_Inicio']))
                h_dia = st.number_input("Horas/Día", value=int(p['Horas_Contrato']))
                h_sem = st.number_input("Horas/Semana", value=int(p['Horas_Semana']))
                if st.form_submit_button("Actualizar Proyecto"):
                    df_p_new = df_p_all[df_p_all['ID_Usuario'].str.lower() != user_id]
                    editado = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": nuevo_n, "Fecha_Inicio": str(nueva_f), "Horas_Contrato": h_dia, "Horas_Semana": h_sem, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_new, editado], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

# --- 2. FICHAR ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    if df_p_user.empty: st.warning("Configura tu proyecto.")
    else:
        fecha = st.date_input("📅 Fecha", datetime.now())
        tags = st.pills("Tipo:", ["Normal", "Viaje", "Pruebas", "Carga", "Oficina", "Localización", "Chequeo"], default="Normal")
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_wrap = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin", key="hora_fin")
        col_i = st.columns(2)
        i_com = col_i[0].checkbox("❌ No comida")
        i_15 = col_i[0].checkbox("⏱️ No 15 min")
        i_turn = col_i[1].checkbox("📉 Turnaround")
        i_diet = col_i[1].checkbox("🍴 Dietas")
        obs = st.text_area("Notas")
        
        if st.button("💾 Guardar Jornada"):
            h_tot = calcular_duracion(h_ini, h_fin)
            inc = [k for k, v in {"No comida":i_com, "No 15m":i_15, "Turnaround":i_turn, "Dietas":i_diet}.items() if v]
            nuevo = pd.DataFrame([{
                "ID_Usuario": user_id, "Proyecto": df_p_user.iloc[0]['Proyecto'], "Fecha": str(fecha),
                "Tipo_Dia": tags, "Hora_Inicio": h_ini.strftime("%H:%M"), "Corte_Camara": h_wrap.strftime("%H:%M"),
                "Hora_Fin_Jornada": h_fin.strftime("%H:%M"), "Horas_Totales": h_tot, 
                "Incidencias": ", ".join(inc), "Observaciones": obs
            }])
            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_all, nuevo], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

# --- 3. HISTORIAL (CON EDICIÓN Y BORRADO POR JORNADA) ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    if not df_f_user.empty and not df_p_user.empty:
        df_f_user['Fecha_DT'] = pd.to_datetime(df_f_user['Fecha']).dt.date
        f_ini = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio']).date()
        df_f_user['Semana'] = df_f_user['Fecha_DT'].apply(lambda x: obtener_semana_prod(x, f_ini))
        
        for sem in sorted(df_f_user['Semana'].unique(), reverse=True):
            df_sem = df_f_user[df_f_user['Semana'] == sem].sort_values("Fecha_DT").copy()
            df_sem['Día_Vis'] = pd.to_datetime(df_sem['Fecha']).dt.strftime('%d/%m/%Y')
            for c in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                df_sem[c] = df_sem[c].apply(format_hhmm)
            
            lbl = f"Semana {sem}" if sem > 0 else f"Pre-producción (S{sem})"
            with st.expander(f"📂 {lbl} — Total: {round(df_sem['Horas_Totales'].sum(), 1)}h"):
                df_tab = df_sem.rename(columns={"Tipo_Dia": "Tipo", "Hora_Inicio": "Call", "Hora_Fin_Jornada": "Fin", "Horas_Totales": "H", "Incidencias": "Alertas", "Observaciones": "Notas"})
                st.dataframe(df_tab[["Día_Vis", "Tipo", "Call", "Fin", "H", "Alertas", "Notas"]], hide_index=True)
                
                # SECCIÓN EDITAR / BORRAR JORNADA
                col_ed1, col_ed2 = st.columns([2, 1])
                jornada_sel = col_ed1.selectbox("Seleccionar día para gestionar:", df_sem['Día_Vis'], key=f"sel_{sem}")
                
                if col_ed2.button("🗑️ Borrar", key=f"btn_del_{sem}"):
                    fecha_borrar = df_sem[df_sem['Día_Vis'] == jornada_sel]['Fecha'].values[0]
                    df_f_rest = df_f_all[~((df_f_all['ID_Usuario'].str.lower() == user_id) & (df_f_all['Fecha'] == str(fecha_borrar)))]
                    conn.update(worksheet="Fichajes_Diarios", data=df_f_rest)
                    st.cache_data.clear()
                    st.rerun()
                
                with st.popover("✏️ Editar Jornada"):
                    row = df_sem[df_sem['Día_Vis'] == jornada_sel].iloc[0]
                    with st.form(f"form_ed_{jornada_sel}"):
                        new_h_ini = st.time_input("Nuevo Call", datetime.strptime(row['Hora_Inicio'], "%H:%M").time())
                        new_h_fin = st.time_input("Nuevo Fin", datetime.strptime(row['Hora_Fin_Jornada'], "%H:%M").time())
                        new_obs = st.text_area("Notas", value=row['Observaciones'])
                        if st.form_submit_button("Guardar Cambios"):
                            df_f_rest = df_f_all[~((df_f_all['ID_Usuario'].str.lower() == user_id) & (df_f_all['Fecha'] == str(row['Fecha'])))]
                            new_h_tot = calcular_duracion(new_h_ini, new_h_fin)
                            editado = pd.DataFrame([{
                                "ID_Usuario": user_id, "Proyecto": row['Proyecto'], "Fecha": row['Fecha'],
                                "Tipo_Dia": row['Tipo_Dia'], "Hora_Inicio": new_h_ini.strftime("%H:%M"), "Corte_Camara": row['Corte_Camara'],
                                "Hora_Fin_Jornada": new_h_fin.strftime("%H:%M"), "Horas_Totales": new_h_tot, 
                                "Incidencias": row['Incidencias'], "Observaciones": new_obs
                            }])
                            conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_f_rest, editado], ignore_index=True))
                            st.cache_data.clear()
                            st.rerun()
