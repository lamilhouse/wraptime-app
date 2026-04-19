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
        df_p_all = conn.read(worksheet="Config_Proyectos", ttl="0s")
        df_p_user = df_p_all[df_p_all['ID_Usuario'].str.lower() == user_id] if not df_p_all.empty else pd.DataFrame()
        
        df_f_all = conn.read(worksheet="Fichajes_Diarios", ttl="0s")
        df_f_user = df_f_all[df_f_all['ID_Usuario'].str.lower() == user_id] if not df_f_all.empty else pd.DataFrame()
        
        if not df_f_user.empty and not df_p_user.empty:
            p_info = df_p_user.iloc[0]
            
            # Preparación CSV
            df_csv = df_f_user.copy()
            df_csv['Fecha'] = pd.to_datetime(df_csv['Fecha'])
            f_ini_p = pd.to_datetime(p_info['Fecha_Inicio'])
            df_csv['Semana'] = df_csv['Fecha'].apply(lambda f: (math.floor((f - f_ini_p).days / 7) + 1))
            df_csv = df_csv.sort_values("Fecha")
            
            # Limpieza CSV (quitar redundantes)
            cols_to_keep = ['Semana', 'Fecha', 'Tipo_Dia', 'Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada', 'Incidencias', 'Observaciones']
            df_csv = df_csv[cols_to_keep]
            df_csv['Fecha'] = df_csv['Fecha'].dt.strftime('%d/%m/%Y')

            output = io.StringIO()
            output.write(f"REPORTE DE JORNADAS - WrapTime Lite\n")
            output.write(f"Proyecto;{p_info['Proyecto']}\n")
            output.write(f"Usuario;{user_id}\n")
            output.write(f"Contrato;{p_info['Horas_Contrato']}h día / {p_info['Horas_Semana']}h semana\n")
            output.write(f"Exportado el;{datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            output.write("\n")
            
            df_csv.to_csv(output, index=False, sep=';', lineterminator='\n', encoding='utf-8-sig')
            st.download_button("📥 Descargar Reporte CSV", data=output.getvalue().encode('utf-8-sig'), file_name=f"reporte_{user_id}.csv", mime="text/csv")
    except:
        df_p_user = pd.DataFrame()
        df_f_user = pd.DataFrame()

# --- 1. PROYECTO ---
if "Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    if not df_p_user.empty:
        p = df_p_user.iloc[0]
        with st.container(border=True):
            st.subheader(f"🎥 {p['Proyecto']}")
            c1, c2 = st.columns(2)
            c1.metric("Jornada Contrato", f"{p['Horas_Contrato']} h")
            c2.metric("Semana Contrato", f"{p['Horas_Semana']} h")
            st.info(f"📅 Inicio: {pd.to_datetime(p['Fecha_Inicio']).strftime('%d/%m/%Y')}")

        with st.expander("✏️ Editar proyecto"):
            with st.form("edit_p"):
                nuevo_n = st.text_input("Nombre", value=p['Proyecto'])
                nueva_f = st.date_input("Día 1", pd.to_datetime(p['Fecha_Inicio']))
                col_h1, col_h2 = st.columns(2)
                n_h_dia = col_h1.number_input("Horas día", value=int(p['Horas_Contrato']))
                n_h_sem = col_h2.number_input("Horas semana", value=int(p['Horas_Semana']))
                if st.form_submit_button("Actualizar"):
                    df_p_new = df_p_all[df_p_all['ID_Usuario'].str.lower() != user_id]
                    editado = pd.DataFrame([{"ID_Usuario": user_id, "Proyecto": nuevo_n, "Fecha_Inicio": str(nueva_f), "Horas_Contrato": n_h_dia, "Horas_Semana": n_h_sem, "Estado": "Activo"}])
                    conn.update(worksheet="Config_Proyectos", data=pd.concat([df_p_new, editado], ignore_index=True))
                    if not df_f_user.empty:
                        df_f_all.loc[df_f_all['ID_Usuario'].str.lower() == user_id, 'Proyecto'] = nuevo_n
                        conn.update(worksheet="Fichajes_Diarios", data=df_f_all)
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

# --- 2. FICHAR ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje")
    if df_p_user.empty:
        st.warning("Configura tu proyecto primero.")
    else:
        fecha = st.date_input("📅 Fecha", datetime.now())
        tags = st.pills("Tipo:", ["Normal", "Viaje", "Pruebas", "Carga", "Oficina", "Localización", "Chequeo"], default="Normal")
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_wrap = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin", key="hora_fin")
        col_i1, col_i2 = st.columns(2)
        i_comida = col_i1.checkbox("❌ No comida")
        i_15min = col_i1.checkbox("⏱️ No 15 min")
        i_turn = col_i2.checkbox("📉 Turnaround")
        i_dietas = col_i2.checkbox("🍴 Dietas")
        obs = st.text_area("Notas")
        if st.button("💾 Guardar Jornada"):
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
            st.rerun()

# --- 3. HISTORIAL (MEJORADO) ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Mi Historial")
    if not df_f_user.empty and not df_p_user.empty:
        df_f_user['Fecha'] = pd.to_datetime(df_f_user['Fecha'])
        f_ini = pd.to_datetime(df_p_user.iloc[0]['Fecha_Inicio'])
        df_f_user['Semana'] = df_f_user['Fecha'].apply(lambda fj: (math.floor((fj - f_ini).days / 7) + 1))
        
        st.metric("Total Proyecto", f"{round(df_f_user['Horas_Totales'].sum(), 1)} h")
        
        for sem in sorted(df_f_user['Semana'].unique(), reverse=True):
            df_sem = df_f_user[df_f_user['Semana'] == sem].sort_values("Fecha").copy()
            titulo = f"📂 Semana {sem}" if sem > 0 else f"📂 Pre-producción (S{sem})"
            
            with st.expander(f"{titulo} — {round(df_sem['Horas_Totales'].sum(), 1)}h"):
                # Limpieza para mostrar en tabla
                df_tab = df_sem.copy()
                df_tab['Día'] = df_tab['Fecha'].dt.strftime('%d/%m/%Y')
                # Quitar posibles ":" sobrantes y limitar a 5 caracteres
                for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
                    df_tab[col] = df_tab[col].astype(str).apply(lambda x: re.sub(r':$', '', x[:5]))
                
                # Renombrar columnas para el usuario
                df_tab = df_tab.rename(columns={
                    "Tipo_Dia": "Tipo",
                    "Hora_Inicio": "Call",
                    "Corte_Camara": "Corte",
                    "Hora_Fin_Jornada": "Fin",
                    "Horas_Totales": "Horas",
                    "Incidencias": "Alertas"
                })
                # Mostrar tabla sin índice y con decimales controlados
                st.dataframe(
                    df_tab[["Día", "Tipo", "Call", "Corte", "Fin", "Horas", "Alertas"]], 
                    hide_index=True,
                    use_container_width=True
                )
        
        st.markdown("---")
        with st.expander("✏️ Gestionar Jornadas"):
            df_f_user['Día_Str'] = df_f_user['Fecha'].dt.strftime('%d/%m/%Y')
            f_sel = st.selectbox("Día:", df_f_user['Día_Str'].unique())
            datos = df_f_user[df_f_user['Día_Str'] == f_sel].iloc[0]
            def l_h(s):
                c = re.sub(r'[^0-9:]', '', str(s))[:5]
                try: return datetime.strptime(c, "%H:%M").time()
                except: return time(8, 0)
            c1, c2 = st.columns(2)
            n_ini = c1.time_input("Nuevo Inicio", l_h(datos['Hora_Inicio']))
            n_fin = c2.time_input("Nuevo Fin", l_h(datos['Hora_Fin_Jornada']))
            if st.button("💾 Guardar Cambios"):
                f_dt = datetime.strptime(f_sel, '%d/%m/%Y').strftime('%Y-%m-%d')
                df_new = df_f_all[~((df_f_all['ID_Usuario'].str.lower() == user_id) & (df_f_all['Fecha'] == f_dt))]
                h_ed = calcular_duracion(n_ini, n_fin)
                nueva = pd.DataFrame([{
                    "ID_Usuario": user_id, "Proyecto": datos['Proyecto'], "Fecha": f_dt,
                    "Tipo_Dia": datos['Tipo_Dia'], "Hora_Inicio": str(n_ini)[:5], 
                    "Corte_Camara": str(datos['Corte_Camara'])[:5], "Hora_Fin_Jornada": str(n_fin)[:5], 
                    "Horas_Totales": h_ed, "Incidencias": datos['Incidencias'], "Observaciones": datos['Observaciones']
                }])
                conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_new, nueva], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
