import streamlit as st
import mysql.connector
import pandas as pd
import plotly.graph_objects as go
import time
import psutil
import requests
import urllib3
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, ColumnsAutoSizeMode

# Desactivar advertencias de certificados SSL para PRTG
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="SIMPOL | Banco Caroní", layout="wide", page_icon="🏦")

def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

load_css("style.css")

# --- 2. FUNCIONES DE BACKEND ---
def conectar_bd():
    return mysql.connector.connect(
        host="localhost", user="root", password="1234", database="monitoreo_banco"
    )

def verificar_usuario(user, password):
    try:
        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE BINARY usuario = %s AND BINARY clave = %s"
        cursor.execute(query, (user.strip(), password.strip()))
        resultado = cursor.fetchone()
        conn.close()
        return resultado
    except:
        return None

def obtener_telemetria_completa():
    cpu = float(psutil.cpu_percent(interval=None))
    ram = float(psutil.virtual_memory().percent)
    msg = "MODO LOCAL"
    try:
        # Intentar conectar con el sensor específico de PRTG
        url = "https://127.0.0.1/api/table.json?content=sensors&columns=objid,lastvalue,lastvalue_raw&filter_objid=2094&apitoken=ZX2K4GHPDFS4UDR3DVQWSZVYIDARCP6GCHQDHLZANM======"
        r = requests.get(url, timeout=0.8, verify=False)
        if r.status_code == 200:
            cpu = float(r.json()["sensors"][0].get("lastvalue_raw", cpu))
            msg = "PRTG SENSOR"
    except:
        pass
    return cpu, ram, msg

# --- Función de Diálogo para Eliminación ---
@st.dialog("⚠️ Confirmar Eliminación")
def confirmar_borrado(usuario_id):
    st.write(f"¿Está seguro de que desea eliminar permanentemente al analista **{usuario_id}**?")
    st.error("Esta acción es irreversible y el usuario perderá acceso inmediato.")
    
    c1, c2 = st.columns(2)
    if c1.button("SÍ, ELIMINAR", type="primary", use_container_width=True):
        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE usuario = %s", (usuario_id,))
            conn.commit()
            conn.close()
            st.success("Analista eliminado correctamente.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error en base de datos: {e}")
            
    if c2.button("CANCELAR", use_container_width=True):
        st.rerun()

# --- 3. LÓGICA DE ACCESO (LOGIN) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<h1 class='nombre-sistema'>SIMPOL</h1>", unsafe_allow_html=True)
            st.markdown("<p class='subtitulo-sistema'>SISTEMA INTELIGENTE DE MONITOREO PERMANENTE ONLINE</p>", unsafe_allow_html=True)
            with st.form("form_acceso"):
                u = st.text_input("USUARIO", placeholder="Ingrese ID")
                p = st.text_input("CONTRASEÑA", type="password", placeholder="••••••••")
                if st.form_submit_button("AUTENTICAR"):
                    user_info = verificar_usuario(u, p)
                    if user_info:
                        st.session_state.update({
                            "autenticado": True,
                            "user_actual": user_info["usuario"],
                            "nombre_analista": user_info["nombre_completo"],
                            "rol": user_info["rol"]
                        })
                        st.rerun()
                    else:
                        st.error("Credenciales Inválidas")
    st.stop()

# --- 4. DASHBOARD Y NAVEGACIÓN ---
else:
    opciones_menu = ["🏠 Inicio", "📊 Monitoreo en Vivo", "📄 Reportes PDF"]
    if st.session_state.get("rol") == "admin":
        opciones_menu.append("👥 Gestión de Personal")

    with st.sidebar:
        st.image("logo-banco.jpg", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="titulo-seccion-sidebar">Identificación</p>', unsafe_allow_html=True)
        
        nombre_display = st.session_state.get("nombre_analista") or st.session_state["user_actual"]
        rol_display = st.session_state["rol"].upper()

        st.markdown(f"""
            <div class="user-info-box">
                <span style="color:#888; font-size:11px;">ANALISTA DE NODO:</span><br>
                <span class="user-name-text">👤 {nombre_display}</span><br>
                <span style="color:#28a745; font-size:10px; font-weight:bold;">● {rol_display} - CSU</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<p class="titulo-seccion-sidebar">Menú Principal</p>', unsafe_allow_html=True)
        seleccion = st.radio("Navegación", opciones_menu, label_visibility="collapsed")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    # --- VISTA INICIO ---
    if seleccion == "🏠 Inicio":
        st.markdown(f"<h1 style='color:#003366;'>Bienvenido, {nombre_display}</h1>", unsafe_allow_html=True)
        st.write("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### Panel de Control de Nodo CSU\nHas ingresado al sistema de monitoreo de infraestructura del Banco Caroní.")
        with col2:
            st.info(f"**Estatus de Conexión**\n\n**Analista:** {st.session_state['user_actual']}\n\n**Rol:** {rol_display}\n\n**Base de Datos:** Conectada")

    # --- VISTA MONITOREO EN VIVO ---
    elif seleccion == "📊 Monitoreo en Vivo":
        st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Monitoreo en Tiempo Real: Nodo CSU</h2>", unsafe_allow_html=True)
        
        # Obtener datos de telemetría
        cpu_val, ram_val, fuente_msg = obtener_telemetria_completa()
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # --- FICHA TÉCNICA DEL DISPOSITIVO ---
        col_info, col_status = st.columns([2, 1])
        
        with col_info:
            # Aquí definimos visualmente qué dispositivo se mide
            st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #d3d3d3; padding: 20px; border-left: 5px solid #003366;">
                    <div style="background-color: #003366; color: white; padding: 2px 8px; font-size: 10px; font-weight: bold; display: inline-block; margin-bottom: 10px;">DISPOSITIVO ACTIVO</div>
                    <h3 style="margin:0; color:#003366;">Servidor Central de Operaciones - Nodo CSU</h3>
                    <p style="margin:0; color:#666; font-size:13px;">
                        <b>Origen de Datos:</b> {fuente_msg} <br>
                        <b>ID de Sensor PRTG:</b> 2094 | <b>Interface:</b> Ethernet 0 <br>
                        <b>Última Lectura:</b> {fecha_actual}
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        with col_status:
            st.markdown("<br>", unsafe_allow_html=True)
            st.write(f"**Uptime:** 14d 06h 22m")
            st.progress(cpu_val / 100, text=f"Carga CPU: {cpu_val}%")

        st.write("---")

        # --- MÉTRICAS CUÁDRUPLES ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("USO DE CPU", f"{cpu_val}%", delta=fuente_msg)
        m2.metric("MEMORIA RAM", f"{ram_val}%", delta="Estable")
        m3.metric("ESTADO LÓGICO", "OPERATIVO", delta="OK")

        # --- GRÁFICO DE HISTORIAL ---
        
        try:
            conn = conectar_bd(); cursor = conn.cursor()
            cursor.execute("INSERT INTO monitoreo_30_nodos (fecha_registro, nodo_nombre, uso_cpu, uso_ram, estado) VALUES (%s, %s, %s, %s, %s)",
                         (datetime.now(), st.session_state["user_actual"], cpu_val, ram_val, "ESTABLE"))
            conn.commit()
            df_m = pd.read_sql("SELECT fecha_registro, uso_cpu, uso_ram FROM monitoreo_30_nodos ORDER BY id DESC LIMIT 40", conn)
            conn.close()

            if not df_m.empty:
                df_m = df_m.sort_values("fecha_registro")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_m["fecha_registro"], y=df_m["uso_cpu"], mode='lines', name='CPU %', line=dict(color='#003366', width=3), fill='tozeroy'))
                fig.update_layout(
                    plot_bgcolor="white", 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    margin=dict(l=0, r=0, t=30, b=0), 
                    height=400,
                    xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
                    yaxis=dict(showgrid=True, gridcolor='#f0f0f0', range=[0, 105])
                )
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.error("Error al graficar telemetría en tiempo real.")
        
        time.sleep(5)
        st.rerun()

    # --- VISTA REPORTES ---
    elif seleccion == "📄 Reportes PDF":
        st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Reportes de Gestión</h2>", unsafe_allow_html=True)
        st.write("---")
        st.info("Módulo de generación de PDF en fase de integración (CSU-Report System).")

    # --- VISTA GESTIÓN DE PERSONAL ---
    elif seleccion == "👥 Gestión de Personal":
        st.markdown("<h2 style='color:#003366; margin-top:-30px;'>Administración de Personal CSU</h2>", unsafe_allow_html=True)
        st.write("---")

        with st.popover("➕ REGISTRAR NUEVO ANALISTA", use_container_width=True):
            with st.form("reg_user_form", clear_on_submit=True):
                n_u = st.text_input("Usuario (ID Acceso)")
                n_n = st.text_input("Nombre y Apellido")
                n_p = st.text_input("Contraseña", type="password")
                n_r = st.selectbox("Nivel de Acceso", ["operador", "admin"])
                if st.form_submit_button("GUARDAR REGISTRO", use_container_width=True):
                    if n_u and n_n and n_p:
                        try:
                            conn = conectar_bd(); cursor = conn.cursor()
                            cursor.execute("INSERT INTO usuarios (usuario, clave, nombre_completo, rol) VALUES (%s,%s,%s,%s)", (n_u.strip(), n_p.strip(), n_n.strip(), n_r))
                            conn.commit(); conn.close()
                            st.success("Analista registrado correctamente."); st.rerun()
                        except: st.error("Error: El ID de usuario ya existe.")

        st.markdown("### 🔍 Listado Maestro de Analistas")
        busqueda = st.text_input("Filtro rápido:", placeholder="Escriba para buscar...")

        conn = conectar_bd()
        df_u = pd.read_sql("SELECT usuario, nombre_completo, rol, fecha_creacion FROM usuarios", conn)
        conn.close()

        if busqueda:
            df_u = df_u[df_u['usuario'].str.contains(busqueda, case=False) | df_u['nombre_completo'].str.contains(busqueda, case=False)]

        gb = GridOptionsBuilder.from_dataframe(df_u)
        gb.configure_selection(selection_mode="single", use_checkbox=True)
        gb.configure_column("usuario", headerName="ID ACCESO")
        gb.configure_column("nombre_completo", headerName="NOMBRE COMPLETO")
        gb.configure_column("rol", headerName="RANGO / ROL")
        gb.configure_column("fecha_creacion", headerName="FECHA REGISTRO")
        grid_options = gb.build()

        grid_response = AgGrid(
            df_u,
            gridOptions=grid_options,
            theme='balham', 
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            height=300,
            allow_unsafe_jscode=True
        )

        # SECCIÓN DE EDICIÓN MEJORADA
        seleccionados = grid_response['selected_rows']

        if seleccionados is not None and len(seleccionados) > 0:
            fila = seleccionados.iloc[0] if isinstance(seleccionados, pd.DataFrame) else seleccionados[0]
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader(f"📝 Ficha de Analista: {fila['usuario']}")
            
            with st.form("form_edicion_final"):
                c_edit1, c_edit2 = st.columns(2)
                with c_edit1:
                    st.text_input("Identificador único", value=fila['usuario'], disabled=True)
                    nom_upd = st.text_input("Nombre Completo del Analista", value=fila['nombre_completo'])
                with c_edit2:
                    st.text_input("Rol en el sistema", value=fila['rol'], disabled=True)
                    pass_upd = st.text_input("Actualizar Contraseña", type="password", placeholder="Dejar vacío para mantener")
                
                if st.form_submit_button("💾 GUARDAR CAMBIOS EN FICHA", type="primary", use_container_width=True):
                    conn = conectar_bd(); cursor = conn.cursor()
                    if pass_upd:
                        cursor.execute("UPDATE usuarios SET nombre_completo=%s, clave=%s WHERE usuario=%s", (nom_upd, pass_upd, fila['usuario']))
                    else:
                        cursor.execute("UPDATE usuarios SET nombre_completo=%s WHERE usuario=%s", (nom_upd, fila['usuario']))
                    conn.commit(); conn.close()
                    st.success("Cambios aplicados exitosamente."); time.sleep(1); st.rerun()

            # Bloque de eliminación separado para mayor seguridad
            st.markdown('<div class="delete-section">', unsafe_allow_html=True)
            col_del_text, col_del_btn = st.columns([3, 1])
            col_del_text.write("**Zona de Peligro:** La eliminación de un analista revocará todos sus permisos de monitoreo.")
            
            if col_del_btn.button("🗑️ ELIMINAR ANALISTA", use_container_width=True):
                if fila['usuario'] == st.session_state['user_actual']:
                    st.error("Acción denegada: No puede eliminar su propia cuenta activa.")
                else:
                    confirmar_borrado(fila['usuario'])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("💡 Seleccione un analista de la tabla superior para editar sus datos.")