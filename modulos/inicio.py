import streamlit as st

def mostrar_pantalla():
    # 1. CREAMOS UN CONTENEDOR VACÍO (El borrador)
    # Esto asegura que al salir del módulo, no quede rastro en el DOM
    contenedor_principal = st.empty()
    
    with contenedor_principal.container():
        nombre = st.session_state.get("nombre_analista", "Analista")
        rol = st.session_state.get("rol", "operador").upper()

        # --- BLOQUE DE ESTILOS (Inyectados localmente) ---
        st.markdown("""
            <style>
                [data-testid="stMain"] p, [data-testid="stMain"] li, [data-testid="stMain"] h3 {
                    color: #000000 !important;
                }
                .bienvenida-titulo {
                    color: #003366 !important;
                    font-weight: bold !important;
                    margin-bottom: 0px;
                }
                .estatus-box {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    border: 1px solid #d1d3d8;
                    margin-bottom: 10px;
                }
            </style>
        """, unsafe_allow_html=True)

        # 2. CONTENIDO ENCAPSULADO
        st.markdown(f"<h1 class='bienvenida-titulo'>Bienvenido al sistema, {nombre}</h1>", unsafe_allow_html=True)
        st.divider()

        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Importante: Todo el HTML debe ir dentro de bloques st.markdown
            # para que el ScriptRunner los identifique como una sola unidad
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
            st.success(f"✅ Conexión Segura Establecida\n\nIP: Localhost\nDB: Sincronizada")

        # El mensaje de ayuda también dentro del contenedor
        st.info("💡 Utilice el menú lateral para navegar entre los módulos.")