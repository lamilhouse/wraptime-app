# --- SECCIÓN: FICHAR JORNADA (CON TAGS Y FECHA ESPAÑOLA) ---
elif "Fichar Jornada" in opcion_menu:
    st.title("📝 Registro Diario")
    try:
        df_proyectos = conn.read(worksheet="Config_Proyectos", ttl=10)
        df_fichajes_existentes = conn.read(worksheet="Fichajes_Diarios", ttl=10)
    except:
        st.error("Error al conectar con Google Sheets.")
        st.stop()
    
    if df_proyectos.empty:
        st.warning("⚠️ Primero configura un proyecto en el menú lateral.")
    else:
        lista_proyectos = df_proyectos["Proyecto"].dropna().unique().tolist()
        with st.form("fichaje_diario"):
            proyecto_sel = st.selectbox("🎬 Proyecto", lista_proyectos)
            
            # Fecha con formato español en el widget
            fecha = st.date_input("📅 Fecha", datetime.now(), format="DD/MM/YYYY")
            
            st.write("📋 **Tipo de jornada:**")
            # Etiquetas visuales en cuadrícula
            f1, f2 = st.columns(4), st.columns(4)
            t_normal = f1[0].checkbox("Normal", value=True)
            t_festivo = f1[1].checkbox("Festivo")
            t_viaje = f1[2].checkbox("Viaje")
            t_pruebas = f1[3].checkbox("Pruebas")
            t_carga = f2[0].checkbox("Carga")
            t_oficina = f2[1].checkbox("Oficina")
            t_loc = f2[2].checkbox("Loc.")
            t_chequeo = f2[3].checkbox("Chequeo")

            st.write("---")
            col1, col2, col3 = st.columns(3)
            with col1: h_ini = st.time_input("🕒 Citación (Call)")
            with col2: h_corte = st.time_input("🎥 Wrap Cámara")
            with col3: h_fin = st.time_input("🚚 Fin Jornada")
            
            st.write("---")
            st.write("⚠️ **Incidencias / Extras:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                inc_comida = st.checkbox("❌ No comida")
                inc_corte = st.checkbox("⏱️ No corte 15 min")
            with c2:
                inc_turn = st.checkbox("📉 Salto Turnaround")
                inc_km = st.checkbox("🚗 Kilometraje")
            with c3:
                inc_dietas = st.checkbox("🍴 Dietas")
                inc_otros = st.checkbox("❓ Otras")

            obs = st.text_area("📝 Notas / Observaciones")

            if st.form_submit_button("💾 Guardar Jornada"):
                # Recopilar etiquetas marcadas
                tags = {
                    "Normal": t_normal, "Festivo": t_festivo, "Viaje": t_viaje, 
                    "Pruebas": t_pruebas, "Carga": t_carga, "Oficina": t_oficina, 
                    "Localización": t_loc, "Chequeo": t_chequeo
                }
                tipo_dia_str = ", ".join([k for k, v in tags.items() if v])
                
                alertas = [k for k, v in {
                    "No comida": inc_comida, "No corte 15min": inc_corte, 
                    "Salto Turnaround": inc_turn, "Kilometraje": inc_km, 
                    "Dietas": inc_dietas, "Otros": inc_otros
                }.items() if v]
                
                nuevo_fichaje = pd.DataFrame([{
                    "ID_Usuario": "User1", "Proyecto": proyecto_sel, 
                    "Fecha": str(fecha), # En el Excel se guarda ISO por seguridad de datos
                    "Tipo_Dia": tipo_dia_str, "Hora_Inicio": str(h_ini), 
                    "Corte_Camara": str(h_corte), "Hora_Fin_Jornada": str(h_fin), 
                    "Comida": "No" if inc_comida else "Sí",
                    "Incidencias": ", ".join(alertas), "Observaciones": obs
                }])
                
                df_final_f = pd.concat([df_fichajes_existentes, nuevo_fichaje], ignore_index=True)
                conn.update(worksheet="Fichajes_Diarios", data=df_final_f)
                st.success("¡Jornada guardada!")
                st.balloons()
