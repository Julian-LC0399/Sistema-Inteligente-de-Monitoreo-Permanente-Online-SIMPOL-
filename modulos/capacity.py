import streamlit as st
import io
import traceback
import os
import math
import tempfile
from datetime import datetime
from fpdf import FPDF
from database import conectar_bd, obtener_lista_servidores, obtener_datos_historicos

# =====================================================================
# CLASE PDF - VERSIÓN DEFINITIVA (EQUILIBRADA)
# =====================================================================
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(12, 14, 12)
        self.font_name = 'Helvetica'
        try:
            font_paths = [
                "C:\\Windows\\Fonts\\arial.ttf",
                "C:\\Windows\\Fonts\\Arial.ttf",
                "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
                "/Library/Fonts/Arial.ttf"
            ]
            for path in font_paths:
                if os.path.exists(path):
                    self.add_font('ArialUnicode', '', path, uni=True)
                    self.font_name = 'ArialUnicode'
                    break
        except:
            pass

    def set_font(self, family='ArialUnicode', style='', size=10):
        try:
            if hasattr(self, 'font_name') and self.font_name != 'Helvetica':
                super().set_font(self.font_name, style, size)
            else:
                super().set_font(family, style, size)
        except:
            super().set_font('Helvetica', style, size)

    def clean_text(self, text):
        if text is None:
            return ""
        return str(text).replace("•", "-").replace("·", "-").replace("→", "->")

    def cell(self, w, h=0, txt='', border=0, ln=0, align='', fill=False, link=''):
        return super().cell(w, h, self.clean_text(txt), border, ln, align, fill, link)

    def multi_cell(self, w, h, txt='', border=0, align='J', fill=False):
        return super().multi_cell(w, h, self.clean_text(txt), border, align, fill)

    def header(self):
        self.set_draw_color(0, 51, 102)
        self.set_line_width(1.0)
        self.line(10, 8, 200, 8)
        
        self.set_font(family='ArialUnicode', style='B', size=16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, "BANCO CARONI", 0, 1, "C")
        
        self.set_font(family='ArialUnicode', style='I', size=9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 5, "Sistema Inteligente de Monitoreo Permanente Online (SIMPOL)", 0, 1, "C")
        
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.4)
        self.line(10, 28, 200, 28)
        
        self.set_font(family='ArialUnicode', style='B', size=12)
        self.set_text_color(0, 51, 102)
        self.cell(0, 7, "INFORME DE PLANIFICACION DE CAPACIDAD", 0, 1, "C")
        self.ln(2)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(1)
        
        self.set_font(family='ArialUnicode', style='I', size=7)
        self.set_text_color(128, 128, 128)
        self.cell(65, 5, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, "L")
        self.cell(55, 5, "BANCO CARONI - SIMPOL v4.0", 0, 0, "C")
        self.cell(60, 5, f"Pagina {self.page_no()}", 0, 0, "R")

    def circle(self, x, y, r, style=""):
        self.ellipse(x, y, r, r, style)

    def _dashed_line(self, x1, y1, x2, y2, dash_length=2, gap_length=2):
        """Dibuja una línea discontinua manualmente"""
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
        
        # Calcular vector unitario
        ux = dx / length
        uy = dy / length
        
        # Parámetros del patrón
        pattern_length = dash_length + gap_length
        num_segments = int(length / pattern_length) + 1
        
        for i in range(num_segments):
            start_t = i * pattern_length
            end_t = min(start_t + dash_length, length)
            
            if start_t >= length:
                break
            
            x_start = x1 + ux * start_t
            y_start = y1 + uy * start_t
            x_end = x1 + ux * end_t
            y_end = y1 + uy * end_t
            
            self.line(x_start, y_start, x_end, y_end)

    def dibujar_grafico_tendencia(self, data_points, titulo="Tendencia", max_valor=None, ancho=170, alto=45):
        if not data_points or len(data_points) < 2:
            self.cell(0, 5, "Datos insuficientes para grafico", 0, 1, "L")
            return
        
        self.set_font(family='ArialUnicode', style='B', size=9)
        self.set_text_color(0, 51, 102)
        self.cell(0, 5, self.clean_text(titulo), 0, 1, "L")
        
        if max_valor is None:
            max_valor = max(data_points) * 1.2
        if max_valor == 0:
            max_valor = 100
        
        x_inicio = self.get_x()
        y_inicio = self.get_y()
        
        self.set_draw_color(100, 100, 100)
        self.set_line_width(0.3)
        self.line(x_inicio + 5, y_inicio, x_inicio + 5, y_inicio + alto)
        self.line(x_inicio + 5, y_inicio + alto, x_inicio + ancho, y_inicio + alto)
        
        num_puntos = len(data_points)
        paso = (ancho - 10) / (num_puntos - 1) if num_puntos > 1 else 0
        
        puntos = []
        for i, val in enumerate(data_points):
            x = x_inicio + 5 + (i * paso)
            y = y_inicio + alto - ((min(val, max_valor) / max_valor) * (alto - 10))
            puntos.append((x, y))
        
        self.set_draw_color(0, 51, 102)
        self.set_line_width(1.2)
        for i in range(len(puntos) - 1):
            self.line(puntos[i][0], puntos[i][1], puntos[i+1][0], puntos[i+1][1])
        
        for i, (x, y) in enumerate(puntos):
            self.set_fill_color(0, 51, 102)
            self.set_draw_color(0, 51, 102)
            self.circle(x, y, 1.8, "F")
            
            if i % max(1, num_puntos // 6) == 0 or i == num_puntos - 1:
                self.set_font(family='ArialUnicode', style='', size=6)
                self.set_text_color(80, 80, 80)
                self.set_xy(x - 6, y - 8)
                self.cell(12, 4, f"{data_points[i]:.1f}", 0, 0, "C")
        
        self.set_font(family='ArialUnicode', style='', size=6)
        self.set_text_color(100, 100, 100)
        for i in range(num_puntos):
            if i % max(1, num_puntos // 6) == 0 or i == num_puntos - 1:
                x = x_inicio + 5 + (i * paso)
                self.set_xy(x - 8, y_inicio + alto + 2)
                self.cell(16, 4, f"{i+1}", 0, 0, "C")
        
        self.set_font(family='ArialUnicode', style='', size=6)
        self.set_text_color(100, 100, 100)
        self.set_xy(x_inicio - 12, y_inicio)
        self.cell(10, 4, f"{max_valor:.0f}", 0, 0, "R")
        self.set_xy(x_inicio - 12, y_inicio + alto - 4)
        self.cell(10, 4, "0", 0, 0, "R")
        
        self.set_y(y_inicio + alto + 8)

    def dibujar_grafico_barras(self, labels, valores, colores=None, titulo="Comparativa", ancho=170, alto=45):
        if not labels or not valores or len(labels) != len(valores):
            return
        
        self.set_font(family='ArialUnicode', style='B', size=9)
        self.set_text_color(0, 51, 102)
        self.cell(0, 5, self.clean_text(titulo), 0, 1, "L")
        
        max_val = max(valores) * 1.2 if max(valores) > 0 else 100
        
        x_inicio = self.get_x()
        y_inicio = self.get_y()
        
        self.set_draw_color(100, 100, 100)
        self.set_line_width(0.3)
        self.line(x_inicio + 5, y_inicio, x_inicio + 5, y_inicio + alto)
        self.line(x_inicio + 5, y_inicio + alto, x_inicio + ancho, y_inicio + alto)
        
        num_barras = len(valores)
        ancho_barra = (ancho - 20) / num_barras
        separacion = ancho_barra * 0.2
        
        colores_def = [(0, 51, 102), (200, 50, 50), (200, 150, 0), (0, 150, 50), (150, 50, 150)]
        
        for i, (label, val) in enumerate(zip(labels, valores)):
            x = x_inicio + 10 + (i * ancho_barra)
            altura_barra = (min(val, max_val) / max_val) * (alto - 15)
            y = y_inicio + alto - altura_barra - 5
            
            if colores and i < len(colores):
                color = colores[i]
            else:
                color = colores_def[i % len(colores_def)]
            
            self.set_fill_color(color[0], color[1], color[2])
            self.set_draw_color(color[0], color[1], color[2])
            self.rect(x + separacion/2, y, ancho_barra - separacion, altura_barra, "F")
            
            self.set_font(family='ArialUnicode', style='', size=6)
            self.set_text_color(80, 80, 80)
            self.set_xy(x, y_inicio + alto + 2)
            self.cell(ancho_barra, 4, self.clean_text(label[:12]), 0, 0, "C")
            
            self.set_font(family='ArialUnicode', style='B', size=7)
            self.set_text_color(0, 0, 0)
            self.set_xy(x, y - 6)
            self.cell(ancho_barra, 4, f"{val:.1f}", 0, 0, "C")
        
        self.set_font(family='ArialUnicode', style='', size=6)
        self.set_text_color(100, 100, 100)
        self.set_xy(x_inicio - 12, y_inicio)
        self.cell(10, 4, f"{max_val:.0f}", 0, 0, "R")
        self.set_xy(x_inicio - 12, y_inicio + alto - 4)
        self.cell(10, 4, "0", 0, 0, "R")
        
        self.set_y(y_inicio + alto + 10)

    def dibujar_tendencia_con_proyeccion(self, historico, proyectado, titulo="Tendencia y Proyeccion", ancho=170, alto=45):
        if not historico or len(historico) < 2:
            self.cell(0, 5, "Datos insuficientes para grafico", 0, 1, "L")
            return
        
        datos_completos = historico + [proyectado]
        max_val = max(datos_completos) * 1.2 if max(datos_completos) > 0 else 100
        
        self.set_font(family='ArialUnicode', style='B', size=9)
        self.set_text_color(0, 51, 102)
        self.cell(0, 5, self.clean_text(titulo), 0, 1, "L")
        
        x_inicio = self.get_x()
        y_inicio = self.get_y()
        
        self.set_draw_color(100, 100, 100)
        self.set_line_width(0.3)
        self.line(x_inicio + 5, y_inicio, x_inicio + 5, y_inicio + alto)
        self.line(x_inicio + 5, y_inicio + alto, x_inicio + ancho, y_inicio + alto)
        
        num_puntos = len(datos_completos)
        paso = (ancho - 10) / (num_puntos - 1) if num_puntos > 1 else 0
        
        puntos_hist = []
        for i in range(len(historico)):
            x = x_inicio + 5 + (i * paso)
            y = y_inicio + alto - ((min(historico[i], max_val) / max_val) * (alto - 10))
            puntos_hist.append((x, y))
        
        x_proy = x_inicio + 5 + (len(historico) * paso)
        y_proy = y_inicio + alto - ((min(proyectado, max_val) / max_val) * (alto - 10))
        
        # Línea histórica (azul)
        self.set_draw_color(0, 51, 102)
        self.set_line_width(1.5)
        for i in range(len(puntos_hist) - 1):
            self.line(puntos_hist[i][0], puntos_hist[i][1], puntos_hist[i+1][0], puntos_hist[i+1][1])
        
        # Línea de proyección (rojo discontinua) - usando método manual
        self.set_draw_color(200, 0, 0)
        self.set_line_width(1.2)
        self._dashed_line(puntos_hist[-1][0], puntos_hist[-1][1], x_proy, y_proy, 3, 3)
        
        # Puntos históricos
        for i, (x, y) in enumerate(puntos_hist):
            self.set_fill_color(0, 51, 102)
            self.set_draw_color(0, 51, 102)
            self.circle(x, y, 1.8, "F")
        
        # Punto proyectado
        self.set_fill_color(200, 0, 0)
        self.set_draw_color(200, 0, 0)
        self.circle(x_proy, y_proy, 2.5, "F")
        
        # Etiquetas
        self.set_font(family='ArialUnicode', style='I', size=6)
        self.set_xy(x_inicio + 5, y_inicio - 8)
        self.set_text_color(0, 51, 102)
        self.cell(30, 4, "Historico", 0, 0, "L")
        
        self.set_xy(x_inicio + ancho - 35, y_inicio - 8)
        self.set_text_color(200, 0, 0)
        self.cell(30, 4, "Proyeccion", 0, 0, "R")
        
        # Valor proyectado
        self.set_font(family='ArialUnicode', style='B', size=7)
        self.set_text_color(200, 0, 0)
        self.set_xy(x_proy - 12, y_proy - 14)
        self.cell(24, 4, f"{proyectado:.1f}", 0, 0, "C")
        
        self.set_y(y_inicio + alto + 8)

    def crear_tabla_encabezado(self, headers, col_widths):
        self.set_font(family='ArialUnicode', style='B', size=8)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(0, 51, 102)
        self.set_draw_color(0, 51, 102)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, self.clean_text(header), 1, 0, "C", True)
        self.ln()

    def crear_tabla_fila(self, row_data, col_widths, is_alternate=False, status=None):
        self.set_font(family='ArialUnicode', style='', size=7.5)
        self.set_text_color(0, 0, 0)
        
        if is_alternate:
            self.set_fill_color(245, 248, 250)
        else:
            self.set_fill_color(255, 255, 255)
        
        if status:
            if "CRITICO" in status or "CRITICO" in status:
                self.set_fill_color(255, 220, 220)
            elif "PRECAUCION" in status or "PRECAUCI" in status:
                self.set_fill_color(255, 245, 200)
            else:
                self.set_fill_color(220, 255, 220)
        
        for i, data in enumerate(row_data):
            align = "C" if isinstance(data, (int, float)) else "L"
            self.cell(col_widths[i], 5.5, self.clean_text(str(data)), 1, 0, align, True)
        self.ln()

# =====================================================================
# FUNCIONES DE PERSISTENCIA
# =====================================================================
def registrar_proyeccion_v398(usuario_id, ip_servidor, metrica, t_gb, act_gb, act_pct, proy_gb, proy_pct, act_red, proy_red, veredicto):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        val_total_gb = 0.00
        val_actual_disponible_gb = 0.00
        val_actual_disponible_pct = 0.0
        val_actual_red_mbps = 0.0
        val_proyectado_total_gb = 0.00
        val_proyectado_disponible_gb = 0.00
        val_proyectado_disponible_pct = 0.0
        val_proyectado_red_mbps = 0.0

        if "Memoria" in metrica or "Almacenamiento" in metrica:
            val_total_gb = float(t_gb)
            val_actual_disponible_gb = float(act_gb)
            val_actual_disponible_pct = float(act_pct)
            val_proyectado_total_gb = float(t_gb)
            val_proyectado_disponible_gb = float(proy_gb)
            val_proyectado_disponible_pct = float(proy_pct)
        elif "Red" in metrica:
            val_actual_red_mbps = float(act_red)
            val_proyectado_red_mbps = float(proy_red)
        else:
            val_actual_disponible_pct = float(act_pct)
            val_proyectado_disponible_pct = float(proy_pct)

        query = """
            INSERT INTO proyecciones 
            (usuario_id, ip_servidor, metrica_analizada, 
             val_total_gb, val_actual_disponible_gb, val_actual_disponible_pct, val_actual_red_mbps,
             val_proyectado_total_gb, val_proyectado_disponible_gb, val_proyectado_disponible_pct, val_proyectado_red_mbps, veredicto)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (usuario_id, ip_servidor.strip(), metrica, 
                               val_total_gb, val_actual_disponible_gb, val_actual_disponible_pct, val_actual_red_mbps,
                               val_proyectado_total_gb, val_proyectado_disponible_gb, val_proyectado_disponible_pct, val_proyectado_red_mbps, veredicto))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error registrando proyeccion: {e}")
        if conn: conn.close()
        return False

def guardar_reporte_capacity_bd(nombre_archivo, formato, metrica, ip_servidor, contenido_blob, usuario_id, alerta_id, tipo_alerta, tamanio_kb, total_gb, act_gb, proy_gb, act_red, proy_red):
    conn = conectar_bd()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        
        bytes_actuales = float(act_gb) * 1024.0 * 1024.0 * 1024.0 if "Red" not in metrica and "CPU" not in metrica else 0.0
        bytes_proyectados = float(proy_gb) * 1024.0 * 1024.0 * 1024.0 if "Red" not in metrica and "CPU" not in metrica else 0.0
        
        red_actual = float(act_red) if "Red" in metrica else 0.0
        red_proy = float(proy_red) if "Red" in metrica else 0.0

        query = """
            INSERT INTO reportes_capacity_archivados 
            (nombre_archivo, formato, metrica_analizada, ip_servidor, contenido, usuario_id, 
             alerta_id, tipo_alerta, analisis_total_gb, analisis_bytes_actuales, analisis_bytes_proyectados, 
             analisis_red_mbps_actual, analisis_red_mbps_proyectado, tamanio_kb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (nombre_archivo, formato, metrica, ip_servidor.strip(), contenido_blob, usuario_id, 
                               alerta_id, tipo_alerta, float(total_gb), bytes_actuales, bytes_proyectados, 
                               red_actual, red_proy, tamanio_kb))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error registrando archivo: {e}")
        if conn: conn.close()
        return False

def listar_reportes_capacity_bd(ip_servidor):
    conn = conectar_bd()
    resultados = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, nombre_archivo, formato, metrica_analizada, ip_servidor, fecha_generacion, tamanio_kb, tipo_alerta
                FROM reportes_capacity_archivados
                WHERE TRIM(ip_servidor) = %s
                ORDER BY fecha_generacion DESC
            """
            cursor.execute(query, (ip_servidor.strip(),))
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error listando historico: {e}")
    return resultados

# =====================================================================
# FUNCIONES PARA LA BÓVEDA (PESTAÑA 2)
# =====================================================================
def listar_reportes_capacity_bd_con_filtros(ip_servidor, metrica_filtro=None, formato_filtro=None, fecha_desde=None, fecha_hasta=None):
    """Versión con filtros para la bóveda de reportes"""
    conn = conectar_bd()
    resultados = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT id, nombre_archivo, formato, metrica_analizada, ip_servidor, 
                       fecha_generacion, tamanio_kb, tipo_alerta
                FROM reportes_capacity_archivados
                WHERE TRIM(ip_servidor) = %s
            """
            params = [ip_servidor.strip()]
            
            if metrica_filtro and metrica_filtro != "Todas":
                query += " AND metrica_analizada = %s"
                params.append(metrica_filtro)
            
            if formato_filtro and formato_filtro != "Todos":
                query += " AND formato = %s"
                params.append(formato_filtro)
            
            if fecha_desde:
                query += " AND DATE(fecha_generacion) >= %s"
                params.append(fecha_desde)
            
            if fecha_hasta:
                query += " AND DATE(fecha_generacion) <= %s"
                params.append(fecha_hasta)
            
            query += " ORDER BY fecha_generacion DESC"
            
            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error listando historico con filtros: {e}")
    return resultados

def obtener_metricas_disponibles_boveda(ip_servidor):
    """Obtiene lista de métricas únicas para el filtro"""
    conn = conectar_bd()
    metricas = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT DISTINCT metrica_analizada 
                FROM reportes_capacity_archivados 
                WHERE TRIM(ip_servidor) = %s
                ORDER BY metrica_analizada
            """
            cursor.execute(query, (ip_servidor.strip(),))
            metricas = [row['metrica_analizada'] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error obteniendo métricas: {e}")
    return metricas

def descargar_blob_capacity(id_archivo):
    conn = conectar_bd()
    blob_data = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT contenido FROM reportes_capacity_archivados WHERE id = %s"
            cursor.execute(query, (id_archivo,))
            row = cursor.fetchone()
            if row:
                blob_data = row['contenido']
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error descargando: {e}")
    return blob_data

def reset_reporte():
    st.session_state.reporte_generado = False

# =====================================================================
# GENERAR PDF - CORREGIDO
# =====================================================================
def generar_pdf_con_graficos(servidor_sel, ip_objetivo, metrica_sel, veredicto,
                             detalle_veredicto, pct_actual, pct_final_proyectado,
                             gb_actual, total_gb_actual, gb_proyectado_final,
                             dias_proyeccion, nombre_analista, meta_metrica,
                             red_actual_val, red_proyectada_val, valores_historicos):
    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font(family='ArialUnicode', style='B', size=13)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, "RESUMEN EJECUTIVO", 0, 1, "C")
    pdf.ln(2)
    
    pdf.set_font(family='ArialUnicode', style='B', size=10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 6, "DATOS DEL SERVIDOR", 0, 1, "L")
    
    pdf.set_font(family='ArialUnicode', style='', size=9)
    pdf.cell(65, 5, f"Nombre: {servidor_sel}", 0, 0, "L")
    pdf.cell(65, 5, f"IP: {ip_objetivo}", 0, 1, "L")
    pdf.cell(65, 5, f"Metrica: {metrica_sel}", 0, 0, "L")
    
    if meta_metrica["tipo"] == "disponibilidad":
        pdf.cell(65, 5, f"Capacidad Total: {total_gb_actual} GB", 0, 1, "L")
    elif meta_metrica["tipo"] == "red":
        pdf.cell(65, 5, f"Red Actual: {red_actual_val} Mbit/s", 0, 1, "L")
    else:
        pdf.cell(65, 5, f"Uso Actual: {pct_actual}%", 0, 1, "L")
    
    pdf.cell(65, 5, f"Analista: {nombre_analista}", 0, 0, "L")
    pdf.cell(65, 5, f"Horizonte: {dias_proyeccion} dias", 0, 1, "L")
    pdf.ln(3)
    
    if "CRITICO" in veredicto or "CRITICO" in veredicto:
        color_fondo = (255, 230, 230)
        color_borde = (200, 0, 0)
        estado_texto = "CRITICO - ACCION INMEDIATA"
    elif "PRECAUCION" in veredicto or "PRECAUCI" in veredicto:
        color_fondo = (255, 245, 210)
        color_borde = (200, 150, 0)
        estado_texto = "PRECAUCION - ATENCION REQUERIDA"
    else:
        color_fondo = (220, 240, 220)
        color_borde = (0, 150, 50)
        estado_texto = "ESTABLE - OPERACION NORMAL"
    
    pdf.set_fill_color(color_fondo[0], color_fondo[1], color_fondo[2])
    pdf.set_draw_color(color_borde[0], color_borde[1], color_borde[2])
    pdf.set_line_width(0.6)
    pdf.rect(10, pdf.get_y(), 190, 22, "FD")
    
    pdf.set_y(pdf.get_y() + 4)
    pdf.set_font(family='ArialUnicode', style='B', size=13)
    pdf.set_text_color(color_borde[0], color_borde[1], color_borde[2])
    pdf.cell(0, 7, f"VEREDICTO TECNICO: {estado_texto}", 0, 1, "C")
    pdf.set_font(family='ArialUnicode', style='', size=9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 4.5, detalle_veredicto, 0, "C")
    pdf.set_y(pdf.get_y() + 4)
    
    pdf.ln(2)
    pdf.set_font(family='ArialUnicode', style='B', size=10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 6, "ANALISIS DE METRICAS", 0, 1, "L")
    
    col_widths = [60, 60, 60]
    pdf.crear_tabla_encabezado(["Metrica", "Valor Actual", "Valor Proyectado"], col_widths)
    
    if meta_metrica["tipo"] == "disponibilidad":
        filas = [
            ["Capacidad Total (GB)", f"{total_gb_actual:.2f}", f"{total_gb_actual:.2f}"],
            ["Espacio Libre (GB)", f"{gb_actual:.2f}", f"{gb_proyectado_final:.2f}"],
            ["Espacio Libre (%)", f"{pct_actual:.2f}%", f"{pct_final_proyectado:.2f}%"]
        ]
    elif meta_metrica["tipo"] == "red":
        filas = [
            ["Ancho de Banda Total", "-", "-"],
            ["Uso Actual (Mbit/s)", f"{red_actual_val:.2f}", f"{red_proyectada_val:.2f}"],
            ["Saturacion (%)", f"{(red_actual_val/100)*100:.2f}%", f"{(red_proyectada_val/100)*100:.2f}%"]
        ]
    else:
        filas = [
            ["Uso Actual (%)", f"{pct_actual:.2f}%", "-"],
            ["Proyeccion (%)", "-", f"{pct_final_proyectado:.2f}%"],
            ["Incremento", "-", f"{(pct_final_proyectado - pct_actual):.2f}%"]
        ]
    
    for i, fila in enumerate(filas):
        pdf.crear_tabla_fila(fila, col_widths, is_alternate=(i % 2 == 1))
    
    pdf.ln(2)
    
    pdf.set_font(family='ArialUnicode', style='B', size=10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 6, "GRAFICO 1 - TENDENCIA HISTORICA Y PROYECCION", 0, 1, "L")
    
    pdf.set_font(family='ArialUnicode', style='I', size=8)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 4, "Linea azul: comportamiento historico | Linea roja discontinua: proyeccion futura | Punto rojo: valor estimado", 0, "L")
    pdf.ln(1)
    
    if valores_historicos and len(valores_historicos) > 3:
        historico_mostrar = valores_historicos[-20:] if len(valores_historicos) > 20 else valores_historicos
        pdf.dibujar_tendencia_con_proyeccion(
            historico_mostrar,
            pct_final_proyectado,
            titulo=f"Evolucion y Proyeccion a {dias_proyeccion} dias"
        )
    else:
        datos_simulados = [pct_actual - i * 0.5 for i in range(5, 0, -1)]
        pdf.dibujar_grafico_tendencia(
            datos_simulados,
            titulo="Tendencia de la Metrica (Muestras Recientes)"
        )
    
    pdf.ln(2)
    
    pdf.set_font(family='ArialUnicode', style='B', size=10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 6, "GRAFICO 2 - COMPARATIVA DE VALORES", 0, 1, "L")
    
    pdf.set_font(family='ArialUnicode', style='I', size=8)
    pdf.set_text_color(80, 80, 80)
    
    if meta_metrica["tipo"] == "disponibilidad":
        pdf.multi_cell(0, 4, "Compara espacio libre actual vs proyectado. Barras: verde (libre actual), naranja (libre proyectado), azul (ocupado)", 0, "L")
    elif meta_metrica["tipo"] == "red":
        pdf.multi_cell(0, 4, "Compara uso de red actual vs proyectado. Barras: azul (uso actual), rojo (uso proyectado)", 0, "L")
    else:
        pdf.multi_cell(0, 4, "Compara consumo de CPU actual vs proyectado. Barras: azul (actual), rojo (proyectado)", 0, "L")
    pdf.ln(1)
    
    if meta_metrica["tipo"] == "disponibilidad":
        pdf.dibujar_grafico_barras(
            ["Libre Actual", "Libre Proy.", "Ocupado"],
            [gb_actual, gb_proyectado_final, total_gb_actual - gb_proyectado_final],
            colores=[(0, 150, 50), (200, 150, 0), (0, 51, 102)],
            titulo="Distribucion de Capacidad (GB)"
        )
    elif meta_metrica["tipo"] == "red":
        pdf.dibujar_grafico_barras(
            ["Uso Actual", "Uso Proy."],
            [red_actual_val, red_proyectada_val],
            colores=[(0, 51, 102), (200, 50, 50)],
            titulo="Uso de Red (Mbit/s)"
        )
    else:
        pdf.dibujar_grafico_barras(
            ["Actual", "Proyectado"],
            [pct_actual, pct_final_proyectado],
            colores=[(0, 51, 102), (200, 50, 50)],
            titulo="Consumo de CPU (%)"
        )
    
    pdf.ln(2)
    
    pdf.set_font(family='ArialUnicode', style='B', size=10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 6, "RECOMENDACIONES", 0, 1, "L")
    
    pdf.set_font(family='ArialUnicode', style='', size=9)
    pdf.set_text_color(0, 0, 0)
    
    if "CRITICO" in veredicto or "CRITICO" in veredicto:
        recomendaciones = [
            "• Incrementar la capacidad del recurso de forma inmediata.",
            "• Realizar un analisis detallado de la carga de trabajo actual.",
            "• Considerar la migracion a una infraestructura con mayor capacidad.",
            "• Programar mantenimiento preventivo para los proximos 7 dias."
        ]
    elif "PRECAUCION" in veredicto or "PRECAUCI" in veredicto:
        recomendaciones = [
            "• Monitorear la tendencia de crecimiento de forma semanal.",
            "• Evaluar la posibilidad de ampliar la capacidad en los proximos 30 dias.",
            "• Revisar la configuracion actual para optimizar el rendimiento.",
            "• Mantener un registro de los picos de demanda."
        ]
    else:
        recomendaciones = [
            "• Continuar con el monitoreo regular de la metrica.",
            "• Mantener la configuracion actual, esta dentro de parametros seguros.",
            "• Revisar la capacidad cada 90 dias para detectar cambios en la demanda.",
            "• Documentar el comportamiento historico para futuras referencias."
        ]
    
    pdf.multi_cell(0, 5, "\n".join(recomendaciones))
    pdf.ln(2)
    
    pdf.set_font(family='ArialUnicode', style='B', size=9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 5, "FIRMA Y SELLO", 0, 1, "L")
    pdf.set_font(family='ArialUnicode', style='', size=9)
    pdf.cell(0, 5, "_________________________________________", 0, 1, "L")
    pdf.cell(0, 5, f"{nombre_analista}", 0, 1, "L")
    pdf.cell(0, 5, "Analista de Infraestructura", 0, 1, "L")
    pdf.cell(0, 5, "Banco Caroni - SIMPOL", 0, 1, "L")
    
    pdf.set_y(pdf.get_y() + 6)
    pdf.set_font(family='ArialUnicode', style='I', size=7)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 4, f"Documento generado por SIMPOL v4.0.3 | ID: {datetime.now().strftime('%Y%m%d%H%M%S')}", 0, 1, "C")
    
    return pdf

# =====================================================================
# FUNCIÓN PARA OBTENER BYTES DEL PDF (CORREGIDA)
# =====================================================================
def obtener_bytes_pdf(pdf):
    """Convierte un objeto PDF a bytes de manera compatible"""
    try:
        # Intentar método para fpdf2 (versiones modernas)
        pdf_bytes = pdf.output(dest='S')
        if isinstance(pdf_bytes, str):
            return pdf_bytes.encode('latin1')
        return pdf_bytes
    except:
        # Fallback usando tempfile para versiones antiguas
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            with open(tmp_file.name, 'rb') as f:
                bytes_pdf = f.read()
            os.unlink(tmp_file.name)
            return bytes_pdf

# =====================================================================
# FUNCIÓN PARA LIMPIAR EL ESTADO DEL MÓDULO CAPACITY
# =====================================================================
def limpiar_estado_capacity():
    """Limpia todas las variables de estado del módulo capacity"""
    keys_to_clear = [
        'p1_servidor', 'p1_metrica', 'p1_dias', 'p1_ajuste',
        'p1_filtros_aplicados', 'p1_reporte_generado',
        'p2_servidor_seleccionado', 'p2_metrica_filtro',
        'p2_formato_filtro', 'p2_mostrar_tabla',
        'modulo_capacity_activo'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# =====================================================================
# VISTA PRINCIPAL
# =====================================================================
def mostrar_pantalla(nombre_analista="Analista", usuario_id=1, usuario_login="Sistema"):
    
    # =============================================================
    # DETECTAR EL MÓDULO ACTUAL Y LIMPIAR SI CAMBIA
    # =============================================================
    # Obtener el módulo actual desde el session_state
    modulo_actual = st.session_state.get("modulo_actual", "capacity")
    
    # Si el módulo actual no es "capacity" y el módulo capacity estaba activo, limpiar
    if modulo_actual != "capacity" and st.session_state.get("modulo_capacity_activo", False):
        limpiar_estado_capacity()
        st.session_state.modulo_capacity_activo = False
        # No hacer return, solo limpiar y continuar
        # Pero como no estamos en capacity, mejor salir
    
    # Si estamos en el módulo capacity, marcarlo como activo
    if modulo_actual == "capacity":
        st.session_state.modulo_capacity_activo = True
    
    # =============================================================
    # INICIALIZAR VARIABLES SI NO EXISTEN
    # =============================================================
    if "p1_servidor" not in st.session_state:
        st.session_state.p1_servidor = "-- Seleccione un Servidor --"
    if "p1_metrica" not in st.session_state:
        st.session_state.p1_metrica = ""
    if "p1_dias" not in st.session_state:
        st.session_state.p1_dias = 30
    if "p1_ajuste" not in st.session_state:
        st.session_state.p1_ajuste = 0
    if "p1_filtros_aplicados" not in st.session_state:
        st.session_state.p1_filtros_aplicados = False
    if "p1_reporte_generado" not in st.session_state:
        st.session_state.p1_reporte_generado = False
    if "p2_servidor_seleccionado" not in st.session_state:
        st.session_state.p2_servidor_seleccionado = "-- Seleccione un Servidor --"
    if "p2_metrica_filtro" not in st.session_state:
        st.session_state.p2_metrica_filtro = "Todas"
    if "p2_formato_filtro" not in st.session_state:
        st.session_state.p2_formato_filtro = "Todos"
    if "p2_mostrar_tabla" not in st.session_state:
        st.session_state.p2_mostrar_tabla = False

    st.markdown("""
        <style>
            .info-analista-capacity {
                color: #333333;
                font-size: 20px;
                font-weight: 500;
                margin-bottom: 15px;
                margin-top: 5px;
                padding: 4px 0;
            }
            .info-analista-capacity span {
                color: #003366;
                font-weight: 700;
            }
            .badge-pdf {
                background-color: #b30000;
                color: white;
                padding: 3px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            .badge-csv {
                background-color: #1b5e20;
                color: white;
                padding: 3px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h2 style="color:#003366; margin-bottom:0px;">📈 Planificacion de Capacidad (Capacity Planning)</h2>', unsafe_allow_html=True)
    
    cargo_actual = st.session_state.get("cargo", "Analista")
    usuario_actual = st.session_state.get("user_actual", "Sistema")
    
    st.markdown(f"""
        <div class="info-analista-capacity">
            👤 <span>Analista:</span> {cargo_actual} ({usuario_actual})
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    pestana_analisis, pestana_boveda = st.tabs(["📊 Simulacion y Analisis Tecnico", "🗄️ Boveda de Reportes Archivados"])

    try:
        servidores_activos = obtener_lista_servidores()
        if not servidores_activos:
            with pestana_analisis:
                st.info("📭 No hay servidores virtuales mapeados para realizar modelos de proyeccion.")
            return

        opciones_servidores = ["-- Seleccione un Servidor --"] + [s['nombre_alias'] for s in servidores_activos]

        # =====================================================================
        # PESTAÑA 1 - ANÁLISIS
        # =====================================================================
        with pestana_analisis:
            with st.container():
                st.markdown("#### ⚙️ Parametros de Simulacion")
                
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    servidor_sel = st.selectbox(
                        "1. Seleccione el Nodo de Infraestructura Virtual", 
                        options=opciones_servidores,
                        index=opciones_servidores.index(st.session_state.p1_servidor) if st.session_state.p1_servidor in opciones_servidores else 0,
                        key="p1_servidor_widget"
                    )
                    st.session_state.p1_servidor = servidor_sel
                
                if servidor_sel == "-- Seleccione un Servidor --":
                    st.info("🖥️ Por favor, elija un servidor de la infraestructura para desplegar sus metricas disponibles.")
                else:
                    info_servidor = next((s for s in servidores_activos if s['nombre_alias'] == servidor_sel), None)
                    ip_objetivo = str(info_servidor['ip']).strip()

                    dict_metricas_config = {}
                    if int(info_servidor.get('id_sensor_cpu') or 0) > 0:
                        dict_metricas_config["Procesamiento (Uso % CPU)"] = {
                            "col_pct": "val_cpu", "col_total": None, "col_gb": None, "tipo": "consumo"
                        }
                    if int(info_servidor.get('id_sensor_ram') or 0) > 0:
                        dict_metricas_config["Memoria Volatil (Disponible % RAM)"] = {
                            "col_pct": "val_ram_disponible_pct", "col_total": "val_ram_total_gb", "col_gb": "val_ram_disponible_gb", "tipo": "disponibilidad"
                        }
                    for d in range(1, 7):
                        if int(info_servidor.get(f'id_sensor_disco_{d}') or 0) > 0:
                            letra_bd = info_servidor.get(f'letra_disco_{d}')
                            letra_limpia = str(letra_bd).replace('\\', '') if letra_bd else f"Disco {d}"
                            dict_metricas_config[f"Almacenamiento Libre Unidad {letra_limpia} (% Libre)"] = {
                                "col_pct": f"val_disco_{d}_pct_libre", "col_total": f"val_disco_{d}_total_gb", "col_gb": f"val_disco_{d}_libres_gb", "tipo": "disponibilidad"
                            }
                    if int(info_servidor.get('id_sensor_red_total') or 0) > 0:
                        dict_metricas_config["Ancho de Banda Utilizado (Red Total Mbit/s)"] = {
                            "col_pct": "val_red_total", "col_total": None, "col_gb": None, "tipo": "red"
                        }

                    if not dict_metricas_config:
                        st.warning("⚠️ El servidor seleccionado no posee sensores de hardware mapeados en el catalogo.")
                    else:
                        metrica_sel = st.selectbox(
                            "2. Seleccione la Metrica de Hardware a Modelar", 
                            options=list(dict_metricas_config.keys()),
                            index=list(dict_metricas_config.keys()).index(st.session_state.p1_metrica) if st.session_state.p1_metrica in dict_metricas_config else 0,
                            key="p1_metrica_widget"
                        )
                        st.session_state.p1_metrica = metrica_sel
                        meta_metrica = dict_metricas_config[metrica_sel]

                        st.markdown("#### 📊 Parametros del Escenario de Capacidad")
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            dias_proyeccion = st.slider(
                                "Horizonte de simulacion (Dias a proyectar):", 
                                min_value=7, max_value=180, 
                                value=st.session_state.p1_dias, 
                                step=7,
                                key="p1_dias_widget"
                            )
                            st.session_state.p1_dias = dias_proyeccion
                        with col_p2:
                            porcentaje_ajuste_analista = st.slider(
                                "Factor de Ajuste de Crecimiento Adicional (%):", 
                                min_value=0, max_value=50, 
                                value=st.session_state.p1_ajuste, 
                                step=5,
                                key="p1_ajuste_widget"
                            )
                            st.session_state.p1_ajuste = porcentaje_ajuste_analista

                        # =============================================================
                        # BOTONES CON TAMAÑO IGUAL - CORREGIDO
                        # =============================================================
                        col_btn_filtrar, col_btn_limpiar = st.columns(2, gap="small")
                        
                        with col_btn_filtrar:
                            if st.button("🔍 Filtrar", use_container_width=True, key="p1_btn_filtrar"):
                                st.session_state.p1_filtros_aplicados = True
                                st.session_state.p1_reporte_generado = False
                                st.success("✅ Filtros aplicados correctamente.")
                                st.rerun()
                        
                        with col_btn_limpiar:
                            if st.button("🧹 Limpiar", use_container_width=True, key="p1_btn_limpiar"):
                                st.session_state.p1_servidor = "-- Seleccione un Servidor --"
                                st.session_state.p1_metrica = ""
                                st.session_state.p1_dias = 30
                                st.session_state.p1_ajuste = 0
                                st.session_state.p1_filtros_aplicados = False
                                st.session_state.p1_reporte_generado = False
                                st.success("🧹 Filtros limpiados correctamente.")
                                st.rerun()

                        if st.session_state.p1_filtros_aplicados:
                            st.info(f"📌 Filtros activos: Servidor: {st.session_state.p1_servidor} | Metrica: {st.session_state.p1_metrica} | Dias: {dias_proyeccion} | Ajuste: {porcentaje_ajuste_analista}%")

            if st.session_state.p1_filtros_aplicados and st.session_state.p1_servidor != "-- Seleccione un Servidor --":
                servidor_sel = st.session_state.p1_servidor
                metrica_sel = st.session_state.p1_metrica
                
                info_servidor = next((s for s in servidores_activos if s['nombre_alias'] == servidor_sel), None)
                if not info_servidor:
                    st.warning("⚠️ El servidor seleccionado ya no esta disponible.")
                else:
                    ip_objetivo = str(info_servidor['ip']).strip()
                    meta_metrica = dict_metricas_config[metrica_sel]

                    conn_temp = conectar_bd()
                    datos_diarios = []
                    valores_historicos = []
                    
                    if conn_temp:
                        try:
                            cursor_temp = conn_temp.cursor(dictionary=True)
                            c_pct = meta_metrica["col_pct"]
                            c_tot = meta_metrica["col_total"] if meta_metrica["col_total"] else "1"
                            c_gb = meta_metrica["col_gb"] if meta_metrica["col_gb"] else "1"
                            
                            query_diaria = f"""
                                SELECT DATE(fecha_registro) AS fecha_limpia, AVG({c_pct}) AS promedio_pct, MAX({c_tot}) AS max_total_gb, AVG({c_gb}) AS promedio_gb
                                FROM monitoreo WHERE TRIM(ip_servidor) = %s GROUP BY DATE(fecha_registro) ORDER BY fecha_limpia ASC
                            """
                            cursor_temp.execute(query_diaria, (ip_objetivo,))
                            datos_diarios = cursor_temp.fetchall()
                            cursor_temp.close()
                            conn_temp.close()
                            
                            valores_historicos = [float(d['promedio_pct'] or 0.0) for d in datos_diarios if d['promedio_pct'] is not None]
                            
                        except Exception as e_sql:
                            st.error(f"❌ Fallo en la query analitica: {e_sql}")
                            if conn_temp: conn_temp.close()

                    CON_DATOS_SUFICIENTES = True
                    if not datos_diarios or len(datos_diarios) < 3:
                        CON_DATOS_SUFICIENTES = False
                        if datos_diarios and len(datos_diarios) > 0:
                            valores_pct = [float(datos_diarios[-1]['promedio_pct'] or 0.0)]
                            valores_total = [float(datos_diarios[-1]['max_total_gb'] or 0.0)]
                            valores_gb = [float(datos_diarios[-1]['promedio_gb'] or 0.0)]
                        else:
                            valores_pct = [80.0 if meta_metrica["tipo"] == "disponibilidad" else 20.0]
                            valores_total = [float(info_servidor.get(meta_metrica["col_total"]) or 100.0) if meta_metrica["col_total"] else 0.0]
                            valores_gb = [valores_total[0] * 0.8] if meta_metrica["tipo"] == "disponibilidad" else [0.0]
                    else:
                        valores_pct = [float(d['promedio_pct'] or 0.0) for d in datos_diarios]
                        valores_total = [float(d['max_total_gb'] or 0.0) for d in datos_diarios]
                        valores_gb = [float(d['promedio_gb'] or 0.0) for d in datos_diarios]

                    num_muestras = len(valores_pct)
                    X = list(range(num_muestras))
                    Y = valores_pct

                    if CON_DATOS_SUFICIENTES:
                        sum_x = sum(X)
                        sum_y = sum(Y)
                        sum_x_cuadrado = sum([x**2 for x in X])
                        sum_xy = sum([X[i] * Y[i] for i in range(num_muestras)])
                        denominador = (num_muestras * sum_x_cuadrado) - (sum_x**2)
                        if denominador == 0:
                            pendiente, interseccion = 0.0, Y[-1]
                        else:
                            pendiente = ((num_muestras * sum_xy) - (sum_x * sum_y)) / denominador
                            interseccion = (sum_y - (pendiente * sum_x)) / num_muestras
                    else:
                        factor_direccion = -1.0 if meta_metrica["tipo"] == "disponibilidad" else 1.0
                        pendiente = (5.0 / 30.0) * factor_direccion
                        interseccion = Y[-1]

                    pct_actual = Y[-1]
                    total_gb_actual = valores_total[-1]
                    gb_actual = valores_gb[-1]
                    
                    indice_proyectado = num_muestras + dias_proyeccion - 1
                    pct_base_proyectado = (pendiente * indice_proyectado) + interseccion

                    red_actual_val = pct_actual if meta_metrica["tipo"] == "red" else 0.0
                    red_proyectada_val = pct_base_proyectado if meta_metrica["tipo"] == "red" else 0.0

                    if meta_metrica["tipo"] == "consumo":
                        pct_final_proyectado = pct_base_proyectado * (1 + (porcentaje_ajuste_analista / 100.0))
                        pct_final_proyectado = max(0.0, min(100.0, pct_final_proyectado))
                        gb_proyectado_final = 0.0
                        if pct_final_proyectado >= 85.0:
                            veredicto, color_alert = "CRITICO", "red"
                            detalle_veredicto = "Saturacion de CPU inminente. El consumo proyectado supera el umbral corporativo del 85%."
                        elif pct_final_proyectado >= 70.0:
                            veredicto, color_alert = "PRECAUCION", "orange"
                            detalle_veredicto = "Crecimiento elevado en procesamiento. Se aconseja revision preventiva."
                        else:
                            veredicto, color_alert = "ESTABLE", "green"
                            detalle_veredicto = f"La capacidad de procesamiento operara de forma segura en los proximos {dias_proyeccion} dias."
                    elif meta_metrica["tipo"] == "red":
                        pct_final_proyectado = pct_base_proyectado * (1 + (porcentaje_ajuste_analista / 100.0))
                        red_proyectada_val = pct_final_proyectado
                        gb_proyectado_final = 0.0
                        if pct_final_proyectado >= 90.0:
                            veredicto, color_alert = "CRITICO", "red"
                            detalle_veredicto = "Saturacion de interfaz de Red proyectada por encima de limites de canal (90% de saturacion)."
                        elif pct_final_proyectado >= 75.0:
                            veredicto, color_alert = "PRECAUCION", "orange"
                            detalle_veredicto = "Trafico de red elevado. Posible congestion en horas pico de procesamiento bancario."
                        else:
                            veredicto, color_alert = "ESTABLE", "green"
                            detalle_veredicto = "Ancho de banda stable con holgura suficiente para la operacion diaria."
                    else:
                        pct_final_proyectado = pct_base_proyectado * (1 - (porcentaje_ajuste_analista / 100.0))
                        pct_final_proyectado = max(0.0, min(100.0, pct_final_proyectado))
                        gb_proyectado_final = round((total_gb_actual * pct_final_proyectado) / 100.0, 2)
                        if pct_final_proyectado <= 10.0:
                            veredicto, color_alert = "CRITICO", "red"
                            detalle_veredicto = "Agotamiento total de recurso libre inminente (Menos del 10% disponible)."
                        elif pct_final_proyectado <= 20.0:
                            veredicto, color_alert = "PRECAUCION", "orange"
                            detalle_veredicto = "Recurso libre escaso para responder ante contingencias operativas (Menos del 20% disponible)."
                        else:
                            veredicto, color_alert = "ESTABLE", "green"
                            detalle_veredicto = "La infraestructura mantendra indices de disponibilidad saludables durante el periodo simulado."

                    st.markdown(" ")
                    if st.button("🚀 Generar Reporte y Procesar Simulacion de Tendencia", use_container_width=True, key="p1_btn_generar"):
                        st.session_state.p1_reporte_generado = True
                        st.rerun()

                    if st.session_state.p1_reporte_generado:
                        st.markdown("---")
                        if not CON_DATOS_SUFICIENTES:
                            st.warning("⚠️ **Modo de Proyeccion Estatica Normativa Activo:** Muestras historicas insuficientes.")

                        st.markdown(
                            f'<div style="background-color:#f8f9fa; border:1px solid #ddd; border-left:6px solid {color_alert}; padding:12px; border-radius:4px; margin-top:10px;">'
                            f'<h4 style="margin:0px; color:#333;">Veredicto Tecnico: <span style="color:{color_alert}; font-weight:bold;">{veredicto}</span></h4>'
                            f'<p style="margin:5px 0px; font-size:13px; color:#555;">{detalle_veredicto}</p>'
                            f'<ul style="margin:5px 0px; padding-left:20px; font-size:12px; color:#444;">'
                            f'<li><b>Muestra Actual:</b> {round(pct_actual, 2)} {"Mbit/s" if meta_metrica["tipo"] == "red" else "%"}</li>'
                            f'<li><b>Tendencia Proyectada:</b> {round(pct_final_proyectado, 2)} {"Mbit/s" if meta_metrica["tipo"] == "red" else "%"}</li>'
                            f'{"<li><b>Capacidad Absoluta Actual:</b> " + str(round(gb_actual, 2)) + " GB de " + str(round(total_gb_actual, 2)) + " GB Totales</li>" if meta_metrica["tipo"] == "disponibilidad" else ""}'
                            f'{"<li><b>Capacidad Absoluta Proyectada:</b> " + str(round(gb_proyectado_final, 2)) + " GB libres estimados</li>" if meta_metrica["tipo"] == "disponibilidad" else ""}'
                            f'<li><b>Veredicto del Sistema:</b> {veredicto}</li>'
                            f'</ul>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )

                        nombre_doc_pdf = f"capacity_{ip_objetivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        nombre_doc_csv = f"capacity_{ip_objetivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

                        pdf = generar_pdf_con_graficos(
                            servidor_sel=servidor_sel,
                            ip_objetivo=ip_objetivo,
                            metrica_sel=metrica_sel,
                            veredicto=veredicto,
                            detalle_veredicto=detalle_veredicto,
                            pct_actual=pct_actual,
                            pct_final_proyectado=pct_final_proyectado,
                            gb_actual=gb_actual,
                            total_gb_actual=total_gb_actual,
                            gb_proyectado_final=gb_proyectado_final,
                            dias_proyeccion=dias_proyeccion,
                            nombre_analista=nombre_analista,
                            meta_metrica=meta_metrica,
                            red_actual_val=red_actual_val,
                            red_proyectada_val=red_proyectada_val,
                            valores_historicos=valores_historicos
                        )

                        # ===== CORRECCIÓN: Obtener bytes del PDF de manera compatible =====
                        bytes_pdf = obtener_bytes_pdf(pdf)

                        csv_lineas = [
                            "PROPIEDAD,VALOR",
                            f"VEREDICTO SIMPOL TECNICO,{veredicto}",
                            f"Servidor Nombrado,{servidor_sel}",
                            f"Direccion IP V4,{ip_objetivo}",
                            f"Metrica de Analisis,{metrica_sel}",
                            f"Horizonte Simulado Dias,{dias_proyeccion}",
                            f"Porcentaje Actual,{round(pct_actual, 2)}",
                            f"Porcentaje Proyectado,{round(pct_final_proyectado, 2)}",
                            f"Total Capacidad GB,{round(total_gb_actual, 2)}",
                            f"Actual Libre GB,{round(gb_actual, 2)}",
                            f"Proyectado Libre GB,{round(gb_proyectado_final, 2)}",
                            f"Red Mbps Actual,{round(red_actual_val, 2)}",
                            f"Red Mbps Proyectado,{round(red_proyectada_val, 2)}"
                        ]
                        bytes_csv = "\n".join(csv_lineas).encode("utf-8")

                        col_exp1, col_exp2 = st.columns(2)
                        with col_exp1:
                            def archivar_pdf_callback():
                                registrar_proyeccion_v398(usuario_id, ip_objetivo, metrica_sel, total_gb_actual, gb_actual, pct_actual, gb_proyectado_final, pct_final_proyectado, red_actual_val, red_proyectada_val, veredicto)
                                kb = round(len(bytes_pdf) / 1024.0, 2)
                                guardar_reporte_capacity_bd(nombre_doc_pdf, "PDF", metrica_sel, ip_objetivo, bytes_pdf, usuario_id, None, veredicto, kb, total_gb_actual, gb_actual, gb_proyectado_final, red_actual_val, red_proyectada_val)
                            
                            st.download_button(
                                label="📥 Exportar PDF", 
                                data=bytes_pdf, file_name=nombre_doc_pdf, mime="application/pdf", 
                                use_container_width=True, on_click=archivar_pdf_callback, key="p1_btn_pdf"
                            )

                        with col_exp2:
                            def archivar_csv_callback():
                                registrar_proyeccion_v398(usuario_id, ip_objetivo, metrica_sel, total_gb_actual, gb_actual, pct_actual, gb_proyectado_final, pct_final_proyectado, red_actual_val, red_proyectada_val, veredicto)
                                kb = round(len(bytes_csv) / 1024.0, 2)
                                guardar_reporte_capacity_bd(nombre_doc_csv, "CSV", metrica_sel, ip_objetivo, bytes_csv, usuario_id, None, veredicto, kb, total_gb_actual, gb_actual, gb_proyectado_final, red_actual_val, red_proyectada_val)
                            
                            st.download_button(
                                label="📥 Exportar CSV", 
                                data=bytes_csv, file_name=nombre_doc_csv, mime="text/csv", 
                                use_container_width=True, on_click=archivar_csv_callback, key="p1_btn_csv"
                            )

        # =====================================================================
        # PESTAÑA 2 - BÓVEDA CON BOTONES ALINEADOS VERTICALMENTE
        # =====================================================================
        with pestana_boveda:
            st.markdown("#### 📜 Repositorio de Informes Archivados")
            
            st.markdown("##### 🔍 Filtros de Búsqueda")
            
            # CSS para alinear botones verticalmente con los selectboxes
            st.markdown("""
                <style>
                    /* Contenedor de columnas - alinear todo en la parte inferior */
                    div[data-testid="column"] {
                        display: flex !important;
                        flex-direction: column !important;
                        justify-content: flex-end !important;
                        height: 100% !important;
                        min-height: 80px !important;
                    }
                    /* Los selectboxes deben estar en la parte superior de su columna */
                    div[data-testid="stSelectbox"] {
                        margin-bottom: auto !important;
                    }
                    /* Las etiquetas de los selectboxes */
                    div[data-testid="stSelectbox"] label {
                        margin-bottom: 4px !important;
                    }
                    /* Los botones deben estar alineados con la base de los selectboxes */
                    div[data-testid="column"]:has(button) {
                        justify-content: flex-end !important;
                        padding-bottom: 0px !important;
                        min-height: 80px !important;
                    }
                    div[data-testid="column"]:has(button) button {
                        margin-top: auto !important;
                        margin-bottom: 0px !important;
                        height: 38px !important;
                        width: 100% !important;
                    }
                    /* Ajustar el contenedor de las columnas */
                    .row-widget.stColumns {
                        align-items: flex-end !important;
                    }
                    /* Espacio entre los elementos */
                    .stSelectbox div[data-baseweb="select"] {
                        margin-top: 0px !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # =============================================================
            # FILTROS DE BÓVEDA - COLUMNAS BALANCEADAS
            # =============================================================
            # Las columnas 4 y 5 (botones) deben tener el mismo peso que las columnas de los selectboxes
            col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([2, 1.5, 1.2, 1.2, 1.2])
            
            with col_f1:
                servidor_boveda = st.selectbox(
                    "Servidor",
                    options=opciones_servidores,
                    index=opciones_servidores.index(st.session_state.p2_servidor_seleccionado) if st.session_state.p2_servidor_seleccionado in opciones_servidores else 0,
                    key="p2_servidor_widget"
                )
                st.session_state.p2_servidor_seleccionado = servidor_boveda
            
            with col_f2:
                # Mostrar métricas disponibles según el servidor seleccionado
                if servidor_boveda != "-- Seleccione un Servidor --":
                    info_servidor = next((s for s in servidores_activos if s['nombre_alias'] == servidor_boveda), None)
                    if info_servidor:
                        ip_objetivo = str(info_servidor['ip']).strip()
                        metricas_disponibles = obtener_metricas_disponibles_boveda(ip_objetivo)
                        opciones_metricas = ["Todas"] + metricas_disponibles
                    else:
                        opciones_metricas = ["Todas"]
                else:
                    opciones_metricas = ["Todas"]
                
                metrica_filtro = st.selectbox(
                    "Métrica",
                    options=opciones_metricas,
                    index=opciones_metricas.index(st.session_state.p2_metrica_filtro) if st.session_state.p2_metrica_filtro in opciones_metricas else 0,
                    key="p2_filtro_metrica"
                )
                st.session_state.p2_metrica_filtro = metrica_filtro
            
            with col_f3:
                opciones_formatos = ["Todos", "PDF", "CSV"]
                formato_filtro = st.selectbox(
                    "Formato",
                    options=opciones_formatos,
                    index=opciones_formatos.index(st.session_state.p2_formato_filtro) if st.session_state.p2_formato_filtro in opciones_formatos else 0,
                    key="p2_filtro_formato"
                )
                st.session_state.p2_formato_filtro = formato_filtro
            
            # =============================================================
            # BOTONES SIEMPRE VISIBLES CON ALINEACIÓN VERTICAL
            # =============================================================
            with col_f4:
                # Espacio para empujar el botón hacia abajo y alinearlo con los selectboxes
                st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
                if st.button("🔍 Filtrar", use_container_width=True, key="p2_btn_filtrar"):
                    st.session_state.p2_mostrar_tabla = True
                    st.rerun()
            
            with col_f5:
                st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
                if st.button("🧹 Limpiar", use_container_width=True, key="p2_btn_limpiar", help="Limpiar filtros"):
                    st.session_state.p2_metrica_filtro = "Todas"
                    st.session_state.p2_formato_filtro = "Todos"
                    st.session_state.p2_mostrar_tabla = False
                    st.rerun()
            
            # =============================================================
            # MOSTRAR RESULTADOS (SOLO SI HAY SERVIDOR SELECCIONADO)
            # =============================================================
            if servidor_boveda == "-- Seleccione un Servidor --":
                st.info("🖥️ Seleccione un servidor para ver sus reportes archivados.")
            else:
                if st.session_state.p2_mostrar_tabla:
                    info_servidor = next((s for s in servidores_activos if s['nombre_alias'] == servidor_boveda), None)
                    if info_servidor:
                        ip_objetivo = str(info_servidor['ip']).strip()
                        
                        st.markdown("---")
                        
                        items_historicos = listar_reportes_capacity_bd_con_filtros(
                            ip_objetivo,
                            metrica_filtro if metrica_filtro != "Todas" else None,
                            formato_filtro if formato_filtro != "Todos" else None,
                            None,
                            None
                        )
                        
                        if not items_historicos:
                            st.info("📭 No se encontraron reportes con los filtros seleccionados.")
                        else:
                            st.markdown(
                                '<div style="background-color:#003366; color:white; padding:10px; border-radius:4px; font-weight:bold; font-size:13px; font-family:Arial; display:flex; align-items:center;">'
                                '<div style="flex:3.5;">Nombre del Archivo Guardado</div>'
                                '<div style="flex:1.2; text-align:center;">Formato</div>'
                                '<div style="flex:1.2; text-align:center;">Tamaño</div>'
                                '<div style="flex:2.5; text-align:center;">Fecha de Almacenamiento</div>'
                                '<div style="flex:1.6; text-align:center;">Acción</div>'
                                '</div>', unsafe_allow_html=True
                            )
                            
                            for idx, item in enumerate(items_historicos):
                                fecha_str = item['fecha_generacion'].strftime("%Y-%m-%d %H:%M:%S") if hasattr(item['fecha_generacion'], 'strftime') else str(item['fecha_generacion'])
                                
                                badge_class = "badge-pdf" if item['formato'] == "PDF" else "badge-csv"
                                
                                tamanio = item['tamanio_kb']
                                if tamanio and tamanio > 1024:
                                    tamanio_str = f"{tamanio/1024:.1f} MB"
                                else:
                                    tamanio_str = f"{tamanio:.1f} KB" if tamanio else "-"
                                
                                st.markdown(
                                    f'<div style="background-color:#ffffff; border-bottom:1px solid #ddd; padding:12px 10px; font-size:12px; font-family:Arial; display:flex; align-items:center; margin-bottom: 2px;">'
                                    f'<div style="flex:3.5; font-weight:bold; color:#111;">🗃️ {item["nombre_archivo"]}</div>'
                                    f'<div style="flex:1.2; text-align:center;"><span class="{badge_class}">{item["formato"]}</span></div>'
                                    f'<div style="flex:1.2; text-align:center; color:#444;">{tamanio_str}</div>'
                                    f'<div style="flex:2.5; text-align:center; color:#444; font-family:monospace;">{fecha_str}</div>'
                                    f'<div style="flex:1.6; text-align:center;"></div>'
                                    f'</div>', unsafe_allow_html=True
                                )
                                
                                reporte_blob = descargar_blob_capacity(item['id'])
                                if reporte_blob:
                                    st.download_button(
                                        label="📥 Descargar",
                                        data=bytes(reporte_blob),
                                        file_name=item['nombre_archivo'],
                                        mime="application/pdf" if item['formato'] == "PDF" else "text/csv",
                                        key=f"dl_capacity_{item['id']}",
                                        use_container_width=True
                                    )
                            
                            st.caption(f"📊 **{len(items_historicos)}** reportes encontrados")
                else:
                    st.info("🔍 Selecciona los filtros y presiona **'Filtrar'** para ver los reportes archivados.")

    except Exception as e_main:
        st.error(f"❌ Fallo general critico en la ejecucion de la vista analitica: {e_main}")
        traceback.print_exc()

if __name__ == "__main__":
    cargo_usuario = st.session_state.get("nombre_completo", "Analista de Infraestructura")
    id_usuario = st.session_state.get("id", 1)
    login_usuario = st.session_state.get("usuario", "admin")
    mostrar_pantalla(nombre_analista=cargo_usuario, usuario_id=id_usuario, usuario_login=login_usuario)