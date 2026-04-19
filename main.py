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
    opcion_menu = st.selectbox("Navegación", ["🏗️ Configurar Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"], index=1)
    st.markdown("---")
    st.caption("Versión 1.7 - Formato HH:MM")

# --- LÓGICA: CONFIGURAR PROYECTO ---
if "Configurar Proyecto" in opcion_menu:
    st.title("🏗️ Configuración")
    df_existente = conn.read(worksheet="Config_Proyectos", ttl=10)
    
    with st.form("nuevo_proyecto"):
        nombre_p = st.text_input("Nombre del Proyecto")
        fecha_ini = st.date_input("Día 1 / S1", datetime.now(), format="DD/MM/YYYY")
        if st.form_submit_button("🚀 Guardar Proyecto"):
            nuevo_p = pd.DataFrame([{"ID_Usuario":"User1","Proyecto":nombre_p,"Fecha_Inicio":str(fecha_ini),"Estado":"Activo"}])
            conn.update(worksheet="Config_Proyectos", data=pd.concat([df_existente, nuevo_p], ignore_index=True))
            st.success(f"Proyecto '{nombre_p}' guardado.")
            st.cache_data.clear()

# --- LÓGICA: FICHAR JORNADA ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Fichaje Diario")
    df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=10)
    df_fichajes_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=10)
    
    if df_proyectos.empty:
        st.warning("⚠️ No hay proyectos configurados. Ve a la pestaña 'Configurar Proyecto'.")
    else:
        lista_p = df_proyectos["Proyecto"].dropna().unique().tolist()
        proyecto_sel = st.selectbox("🎬 Proyecto", lista_p)
        fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
        
        st.write("📋 **Tipo de jornada:**")
        opciones_jornada = ["Normal", "Festivo", "Viaje", "Pruebas", "Carga", "Oficina", "Loc.", "Chequeo"]
        tipo_dia_lista = st.pills("Selecciona las etiquetas:", opciones_jornada, selection_mode="multi", default="Normal")

        st.write("---")
        c1, c2, c3 = st.columns(3)
        h_ini = c1.time_input("🕒 Call", time(8, 0))
        h_corte = c2.time_input("🎥 Wrap", key="hora_wrap", on_change=actualizar_fin)
        h_fin = c3.time_input("🚚 Fin Jornada", key="hora_fin")
        
        st.write("---")
        st.write("⚠️ **Incidencias:**")
        i1, i2, i3 = st.columns(3)
        inc_com = i1.checkbox("❌ No comida")
        inc_cor = i1.checkbox("⏱️ No 15 min")
        inc_tur = i2.checkbox("📉 Turnaround")
        inc_kms = i2.checkbox("🚗 Kms")
        inc_die = i3.checkbox("🍴 Dietas")
        inc_otr = i3.checkbox("❓ Otros")
        obs = st.text_area("📝 Notas")

        if st.button("💾 Guardar Jornada"):
            if not tipo_dia_lista:
                st.error("Selecciona al menos un tipo de jornada.")
            else:
                t_str = ", ".join(tipo_dia_lista)
                alertas = [k for k, v in {"No comida":inc_com,"No 15m":inc_cor,"Turnaround":inc_tur,"Km":inc_kms,"Dietas":inc_die,"Otros":inc_otr}.items() if v]
                
                # Guardamos las horas como string HH:MM:SS (Streamlit las devuelve así)
                nuevo = pd.DataFrame([{
                    "ID_Usuario": "User1", 
                    "Proyecto": proyecto_sel, 
                    "Fecha": str(fecha),
                    "Tipo_Dia": t_str, 
                    "Hora_Inicio": str(h_ini), 
                    "Corte_Camara": str(h_corte),
                    "Hora_Fin_Jornada": str(h_fin), 
                    "Comida": "No" if inc_com else "Sí",
                    "Incidencias": ", ".join(alertas), 
                    "Observaciones": obs
                }])
                
                conn.update(worksheet="Fichajes_Diarios", data=pd.concat([df_fichajes_existentes, nuevo], ignore_index=True))
                st.success("¡Jornada guardada correctamente!")
                st.cache_data.clear()
                st.balloons()

# --- LÓGICA: MI HISTORIAL ---
elif "Mi Historial" in opcion_menu:
    st.title("📅 Historial")
    df_f = conn.read(worksheet="Fichajes_Diarios", ttl=10)
    df_p = conn.read(worksheet="Config_Proyectos", ttl=10)
    
    if not df_f.empty:
        df_f['Fecha'] = pd.to_datetime(df_f['Fecha'])
        
        # Limpiamos las horas para que no muestren segundos en las tablas
        for col in ['Hora_Inicio', 'Corte_Camara', 'Hora_Fin_Jornada']:
            if col in df_f.columns:
                df_f[col] = df_f[col].astype(str).str[:5]

        for p in df_f['Proyecto'].unique():
            st.subheader(f"🎥 {p}")
            info = df_p[df_p['Proyecto'] == p]
            
            if not info.empty:
                start = pd.to_datetime(info['Fecha_Inicio'].iloc[0])
                df_proy = df_f[df_f['Proyecto'] == p].copy()
                
                # Cálculo de semana
                df_proy['Semana'] = df_proy['Fecha'].apply(lambda x: (math.floor((x-start).days/7)+1) if (x-start).days >=0 else (math.floor((x-start).days/7)))
                
                # Ordenar por semana descendente para ver lo último primero
                for s in sorted(df_proy['Semana'].unique(), reverse=True):
                    titulo_semana = f"📂 Semana {s}" if s > 0 else f"📂 Pre-prod (S{s})"
                    with st.expander(titulo_semana):
                        d_s = df_proy[df_proy['Semana'] == s].sort_values("Fecha")
                        d_s['Día'] = d_s['Fecha'].dt.strftime('%d/%m/%Y')
                        
                        # Tabla resumida
                        columnas_visibles = ["Día", "Tipo_Dia", "Hora_Inicio", "Hora_Fin_Jornada", "Incidencias"]
                        st.table(d_s[columnas_visibles])
                        
                        # Notas opcionales si existen
                        if d_s['Observaciones'].dropna().str.strip().any():
                            st.info("💡 **Notas de la semana:**")
                            for idx, row in d_s.iterrows():
                                if row['Observaciones']:
                                    st.write(f"- *{row['Día']}*: {row['Observaciones']}")
    else:
        st.info("Todavía no hay fichajes registrados.")
