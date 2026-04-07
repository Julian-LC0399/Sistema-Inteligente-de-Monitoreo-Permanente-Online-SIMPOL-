import streamlit as st

def mostrar_pantalla():
    nombre = st.session_state.get("nombre_analista", "Analista")
    rol = st.session_state.get("rol", "operador").upper()

    # --- BLOQUE DE ESTILOS PARA FORZAR TEXTO NEGRO ---
    st.markdown("""
        <style>
            /* Forzar negro en todos los textos del área principal */
            [data-testid="stMain"] p, [data-testid="stMain"] li, [data-testid="stMain"] h3 {
                color: #000000 !important;
            }
            /* Título de bienvenida en Azul Caroní */
            .bienvenida-titulo {
                color: #003366 !important;
                font-weight: bold !important;
                margin-bottom: 0px;
            }
            /* Contenedor de estatus para darle estructura */
            .estatus-box {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border: 1px solid #d1d3d8;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<h1 class='bienvenida-titulo'>Bienvenido al sistema, {nombre}</h1>", unsafe_allow_html=True)
    st.divider()

    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Usamos un div con clase para asegurar que el estilo se aplique
        st.markdown(f"""
        <div class="estatus-box">
            <h3>📊 Estatus de Sesión</h3>
            <p>Usted ha ingresado al <b>SIMPOL</b> (Sistema Inteligente de Monitoreo Permanente Online).</p>
            <ul>
                <li><b>Rango:</b> {rol}</li>
                <li><b>Ubicación:</b> Central Banco Caroní</li>
                <li><b>Acceso:</b> Autorizado</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # El success de Streamlit suele ser verde, lo mantenemos pero aseguramos legibilidad
        st.success(f"✅ Conexión Segura Establecida\n\nIP: Localhost\nDB: Sincronizada")

    st.info("💡 Utilice el menú lateral para navegar entre los módulos.")