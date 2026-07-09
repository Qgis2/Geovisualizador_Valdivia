import streamlit as st
import folium
import streamlit.components.v1 as components
from folium.plugins import MiniMap, Fullscreen, MeasureControl # <-- Importaciones actualizadas
import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds
import numpy as np
import matplotlib.colors as mcolors
import base64
from io import BytesIO
from PIL import Image

# 1. Configuración general
st.set_page_config(page_title="Geovisualizador de Valdivia", layout="wide", initial_sidebar_state="expanded")

# --- FUNCIONES DE CACHÉ Y OPTIMIZACIÓN ---
@st.cache_data
def cargar_capa_vectorial(ruta_archivo):
    try:
        gdf = gpd.read_file(ruta_archivo)
        if gdf.crs.to_string() != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        return gdf
    except Exception as e:
        return None

@st.cache_data
def procesar_raster(ruta_raster):
    try:
        with rasterio.open(ruta_raster) as src:
            banda = src.read(1)
            nodata = src.nodata if src.nodata is not None else -9999
            banda = np.where(banda == nodata, 0, banda)
            bounds = src.bounds
            left, bottom, right, top = transform_bounds(src.crs, 'EPSG:4326', bounds.left, bounds.bottom, bounds.right, bounds.top)
            extremo_mapa = [[bottom, left], [top, right]]
            return banda, extremo_mapa
    except Exception as e:
        return None, None

DICCIONARIO_COLORES = {
    0: {'nombre': 'Sin Cambio', 'color': '#EFEFEF'},
    1: {'nombre': 'Vegetación a Urbano', 'color': '#F4A261'},
    2: {'nombre': 'Urbano a Vegetación', 'color': '#A8DADC'},
    3: {'nombre': 'Vegetación a Humedal', 'color': '#A2D149'},
    4: {'nombre': 'Agua a Humedal', 'color': '#4EA8DE'},
    5: {'nombre': 'Humedal a Vegetación', 'color': '#56AB2F'},
    6: {'nombre': 'Agua a Vegetación', 'color': '#38b000'},
    7: {'nombre': 'Urbano a Humedal', 'color': '#D8B4F8'},
    8: {'nombre': 'Vegetación a Agua', 'color': '#0077B6'},
    9: {'nombre': 'Humedal a Agua', 'color': '#03045E'},
    10: {'nombre': 'Humedal a Urbano', 'color': '#E76F51'},
    11: {'nombre': 'Agua a Urbano', 'color': '#D62828'},
    12: {'nombre': 'Urbano a Agua', 'color': '#0096C7'}
}

# 2. Configuración del Sidebar
st.sidebar.title("Controles del Mapa")
mapa_base = st.sidebar.selectbox("Selecciona un mapa base:", ("OpenStreetMap", "Esri Satélite", "CartoDB Positron"))

st.sidebar.markdown("---")
st.sidebar.subheader("Capas de Información")

mostrar_raster = st.sidebar.checkbox("Dinámica de Cambio (Ráster)", value=True)
mostrar_comuna = st.sidebar.checkbox("Límite Comunal", value=True)
mostrar_urbano = st.sidebar.checkbox("Límite Urbano", value=False)
mostrar_ccu = st.sidebar.checkbox("Continuo Const. Urbana (CCU)", value=False)
mostrar_humedales = st.sidebar.checkbox("Humedales", value=False)
mostrar_vial = st.sidebar.checkbox("Red Vial", value=False)
mostrar_ipt = st.sidebar.checkbox("Planificación Territorial (IPT)", value=False)
mostrar_parcelas = st.sidebar.checkbox("Parcelas y Loteos", value=False)
mostrar_ds19 = st.sidebar.checkbox("Proyectos DS19", value=False)
mostrar_ds49 = st.sidebar.checkbox("Proyectos DS49", value=False)
mostrar_nuevos_terrenos = st.sidebar.checkbox("Construcción Nuevos Terrenos", value=False)

# 3. Área Principal y Mapa Base
st.title("Geovisualizador: Expansión Urbana y Humedales")
st.markdown("Análisis espacial de la matriz de cambio de uso de suelo y la presión inmobiliaria sobre la red de humedales en la comuna de Valdivia.")

LAT_CENTRO, LON_CENTRO = -39.8200, -73.3000
m = folium.Map(location=[LAT_CENTRO, LON_CENTRO], zoom_start=10, control_scale=True)

if mapa_base == "Esri Satélite":
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Esri Satélite').add_to(m)
elif mapa_base == "CartoDB Positron":
    folium.TileLayer(tiles='CartoDB Positron', name='CartoDB Positron').add_to(m)
else:
    folium.TileLayer(tiles='OpenStreetMap', name='OpenStreetMap').add_to(m)

# --- BLOQUE 6: HERRAMIENTAS AVANZADAS EN EL MAPA ---

# --- BLOQUE 6: HERRAMIENTAS AVANZADAS EN EL MAPA (REESTRUCTURADO) ---

# 6.1 Herramienta de Medición (Cargada al principio de los plugins)
mc = MeasureControl(
    position='topright', 
    primary_length_unit='meters', 
    secondary_length_unit='kilometers', 
    primary_area_unit='sqmeters', 
    secondary_area_unit='hectares',
    active_color='#ae1011',
    completed_color='#0077b6'
)
m.add_child(mc)

# 6.2 Modo Pantalla Completa
fs = Fullscreen(
    position='topleft', 
    title='Expandir', 
    title_cancel='Salir de pantalla completa', 
    force_separate_button=True
)
m.add_child(fs)

# 6.3 Minimapa de Referencia (Forzado con una capa base estándar)
minimapa = MiniMap(
    tile_layer='OpenStreetMap', 
    position="bottomright", 
    zoom_level_offset=-5,
    toggle_display=True
)
m.add_child(minimapa)

# --- RENDERIZADO DEL RÁSTER ---
if mostrar_raster:
    matriz_raster, limites = procesar_raster("Landsat8_Valdivia_recortado.tif")
    if matriz_raster is not None and limites is not None:
        rgba_img = np.zeros((matriz_raster.shape[0], matriz_raster.shape[1], 4), dtype=np.uint8)
        for val, info in DICCIONARIO_COLORES.items():
            mask = (matriz_raster == val)
            color_rgb = mcolors.hex2color(info['color'])
            rgba_img[mask, 0] = int(color_rgb[0] * 255)
            rgba_img[mask, 1] = int(color_rgb[1] * 255)
            rgba_img[mask, 2] = int(color_rgb[2] * 255)
            rgba_img[mask, 3] = 180 
        img = Image.fromarray(rgba_img)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        image_url = f"data:image/png;base64,{img_str}"
        folium.raster_layers.ImageOverlay(image=image_url, bounds=limites, name="Dinámica de Cambio de Suelo", opacity=0.8, interactive=False).add_to(m)

# --- RENDERIZADO DE CAPAS VECTORIALES ---
if mostrar_comuna:
    comuna_gdf = cargar_capa_vectorial("Valdivia_comuna_reproy.gpkg")
    if comuna_gdf is not None:
        folium.GeoJson(comuna_gdf, name="Límite Comunal", style_function=lambda x: {'fillColor': 'transparent', 'color': 'black', 'weight': 2, 'dashArray': '5, 5'}).add_to(m)

if mostrar_urbano:
    urbano_gdf = cargar_capa_vectorial("limite_urbano_Valdivia_reproy.gpkg")
    if urbano_gdf is not None:
        folium.GeoJson(urbano_gdf, name="Límite Urbano", style_function=lambda x: {'fillColor': 'transparent', 'color': 'red', 'weight': 3}).add_to(m)

if mostrar_ccu:
    ccu_gdf = cargar_capa_vectorial("CCU_2023_valdivia.gpkg")
    if ccu_gdf is not None:
        folium.GeoJson(ccu_gdf, name="Continuo Const. Urbana (CCU)", style_function=lambda x: {'fillColor': '#7a0177', 'color': '#7a0177', 'weight': 1, 'fillOpacity': 0.5}).add_to(m)

if mostrar_humedales:
    humedales_gdf = cargar_capa_vectorial("humedales_comuna_valdivia_reproy.gpkg")
    if humedales_gdf is not None:
        folium.GeoJson(humedales_gdf, name="Humedales", style_function=lambda x: {'fillColor': '#1f78b4', 'color': '#1f78b4', 'weight': 1, 'fillOpacity': 0.6}).add_to(m)

if mostrar_vial:
    vial_gdf = cargar_capa_vectorial("red_vial_reproyectada_cortado_union.gpkg")
    if vial_gdf is not None:
        folium.GeoJson(vial_gdf, name="Red Vial", style_function=lambda x: {'color': '#525252', 'weight': 1}, tooltip=folium.GeoJsonTooltip(fields=['Nom_Ruta', 'Catego'], aliases=['Ruta:', 'Categoría:'])).add_to(m)

if mostrar_ipt:
    ipt_gdf = cargar_capa_vectorial("IPT_PRC_Valdivia.gpkg")
    if ipt_gdf is not None:
        folium.GeoJson(ipt_gdf, name="Planificación Territorial (IPT)", style_function=lambda x: {'fillColor': '#ff7f00', 'color': '#ff7f00', 'weight': 1, 'fillOpacity': 0.4}, tooltip=folium.GeoJsonTooltip(fields=['UPERM'], aliases=['Uso Permitido:'])).add_to(m)

if mostrar_parcelas:
    parcelas_gdf = cargar_capa_vectorial("Conjuntos_parcelas_comuna_valdivia_recortado.gpkg")
    if parcelas_gdf is not None:
        folium.GeoJson(parcelas_gdf, name="Parcelas y Loteos", style_function=lambda x: {'fillColor': '#33a02c', 'color': '#33a02c', 'weight': 1, 'fillOpacity': 0.5}, tooltip=folium.GeoJsonTooltip(fields=['TIPO', 'SUP_HA'], aliases=['Tipo:', 'Superficie (HA):'])).add_to(m)

if mostrar_ds19:
    ds19_gdf = cargar_capa_vectorial("Proyectos_DS19_valdivia.gpkg")
    if ds19_gdf is not None:
        folium.GeoJson(ds19_gdf, name="Proyectos DS19", style_function=lambda x: {'fillColor': '#6a3d9a', 'color': '#6a3d9a', 'weight': 1, 'fillOpacity': 0.6}, tooltip=folium.GeoJsonTooltip(fields=['NOM_PROY'], aliases=['Proyecto:'])).add_to(m)

if mostrar_ds49:
    ds49_gdf = cargar_capa_vectorial("Proyectos_DS49_valdivia.gpkg")
    if ds49_gdf is not None:
        folium.GeoJson(ds49_gdf, name="Proyectos DS49", marker=folium.CircleMarker(radius=5, fill_color='#e31a1c', color='#e31a1c', fill_opacity=0.8), tooltip=folium.GeoJsonTooltip(fields=['USER_NOMBR'], aliases=['Nombre:'])).add_to(m)

if mostrar_nuevos_terrenos:
    nuevos_terrenos_gdf = cargar_capa_vectorial("construccion_nuevos_terrenos_valdivia.gpkg")
    if nuevos_terrenos_gdf is not None:
        folium.GeoJson(nuevos_terrenos_gdf, name="Construcción Nuevos Terrenos", marker=folium.CircleMarker(radius=5, fill_color='#fb9a99', color='#fb9a99', fill_opacity=0.8), tooltip=folium.GeoJsonTooltip(fields=['NOMBRE_PRO', 'VILLA_POBL'], aliases=['Proyecto:', 'Villa/Población:'])).add_to(m)

# --- Leyenda Cartográfica Flotante ---
html_leyenda = '''
<div style="position: fixed; bottom: 50px; left: 50px; width: 230px; height: auto; max-height: 350px; overflow-y: auto;
            background-color: white; color: black; z-index:9999; font-size:12px; font-family: Arial, sans-serif;
            border:2px solid grey; border-radius:5px; padding: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
    <b style="color: black;">Dinámica de Cambio de Suelo</b><br><hr style="margin: 4px 0; border-color: #ccc;">
'''
for val, info in DICCIONARIO_COLORES.items():
    html_leyenda += f'<p style="margin: 4px 0; color: black;"><i style="background:{info["color"]}; width: 14px; height: 14px; float: left; margin-right: 8px; opacity: 0.8; border-radius: 2px;"></i>{info["nombre"]}</p>'
html_leyenda += '</div>'

m.get_root().html.add_child(folium.Element(html_leyenda))

folium.LayerControl().add_to(m)
components.html(m._repr_html_(), width=1200, height=650)