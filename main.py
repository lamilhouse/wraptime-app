import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="WrapTime Lite", page_icon="🎬")

st.title("🎬 WrapTime")
st.subheader("Configuración de Proyecto")

# 1. CONEXIÓN CON TU GOOGLE SHEETS
# (Usaremos los 'Secrets' de Streamlit para conectar el JSON después)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. FORMULARIO PARA LA VERSIÓN LITE
# Recuerda: En la Lite solo permitimos un proyecto activo.
with st.form("nuevo_proyecto"):
    st.write("Datos del nuevo rodaje:")
    nombre_p = st.text_input("Nombre del Proyecto", placeholder="Ej: Anuncio Cerveza")
    h_jornada = st.number_input("Horas por jornada (Base)", min_value=1, max_value=12, value=8)
    t_comida = st.text_input("Tiempo de comida pactado", value="1 hora")
    descanso = st.radio("¿El descanso de 20min está incluido en la jornada?", ["Sí", "No"])
    
    boton_guardar = st.form_submit_button("Empezar a Fichar")

    if boton_guardar:
        if nombre_p == "":
            st.error("Por favor, ponle un nombre al proyecto.")
        else:
            # Creamos la fila de datos para la pestaña 'Config_Proyectos'
            nuevo_dato = pd.DataFrame([{
                "ID_Usuario": "Usuario_Test", # Esto lo haremos dinámico más adelante
                "Proyecto": nombre_p,
                "Horas_Jornada": h_jornada,
                "Tiempo_Comida": t_comida,
                "Descanso_Incluido": descanso,
                "Estado": "Activo"
            }])
            
            # Lo enviamos a la pestaña correspondiente
            try:
                # Nota: El nombre de la hoja debe coincidir exactamente con tu pestaña
                conn.update(worksheet="Config_Proyectos", data=nuevo_dato)
                st.success(f"¡Proyecto '{nombre_p}' creado! Ahora puedes ir al registro diario.")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# 3. LISTADO DE PROYECTOS (Vista previa)
st.write("---")
st.write("### Tus Proyectos")
try:
    df_proyectos = conn.read(worksheet="Config_Proyectos")
    st.dataframe(df_proyectos)
except:
    st.info("Aún no tienes proyectos registrados.")
