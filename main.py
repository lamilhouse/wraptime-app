# --- DISEÑO DEL MENÚ LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=100) # Un icono de claqueta opcional
    st.title("WrapTime Lite")
    st.markdown("---")
    
    # Usamos un selectbox con iconos para una navegación más limpia
    opcion = st.selectbox(
        "Navegación",
        ["🏗️ Configurar Proyecto", "📝 Fichar Jornada", "📅 Mi Historial"],
        index=1 # Para que por defecto se abra en "Fichar Jornada" que es lo más común
    )
    
    st.markdown("---")
    st.caption("Versión 1.0 - El diario del técnico")
    if st.button("🆘 Ayuda / Soporte"):
        st.info("Contacto: soporte@wraptime.app")

# --- TRADUCCIÓN DE OPCIÓN PARA LA LÓGICA ---
# Como ahora la opción tiene emojis, ajustamos la lógica:
if "Configurar Proyecto" in opcion:
    opcion_logica = "Configurar Proyecto"
elif "Fichar Jornada" in opcion:
    opcion_logica = "Fichar Jornada"
else:
    opcion_logica = "Mi Historial"

# --- AHORA USAMOS opcion_logica EN LOS IF ---
if opcion_logica == "Configurar Proyecto":
    # ... (resto del código de configuración)
