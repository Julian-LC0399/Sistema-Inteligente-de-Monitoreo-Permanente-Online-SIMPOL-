import streamlit as st

def mostrar_pantalla():
    nombre = st.session_state.get("nombre_analista", "Analista")
    rol = st.session_state.get("rol", "operador").upper()
    
    st.markdown(f"<h1 style='color:#003366;'>Bienvenido al Nodo CSU, {nombre}</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        ### Estatus de Sesión
        Usted ha ingresado al **SIMPOL v2** (Sistema Inteligente de Monitoreo Permanente Online).
        
        * **Rango:** {rol}
        * **Ubicación:** Central Banco Caroní
        * **Acceso:** Autorizado
        """)
    
    with col2:
        st.success(f"✅ Conexión Segura Establecida\n\nIP: Localhost\nDB: Sincronizada")