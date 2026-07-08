import streamlit as st
import folium
from streamlit_folium import st_folium

# 1. Configuración general de la página web
st.set_page_config(
    page_title="Geovisualizador de Valdivia", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Configuración del Sidebar (Panel Lateral)
st.sidebar.title("Controles del Mapa")
st.sidebar.markdown("Utiliza las opciones para interactuar con las capas.")

# Selector de mapas base
mapa_base = st.sidebar.selectbox(
    "Selecciona un mapa base:",
    ("OpenStreetMap", "Esri Satélite", "CartoDB Positron")
)

# Espacio reservado para futuros controles de capas vectoriales y ráster
st.sidebar.markdown("---")
st.sidebar.subheader("Capas de Información")
st.sidebar.info("Las opciones de capas se añadirán en los próximos bloques.")

# 3. Área Principal de la Aplicación
st.title("Geovisualizador: Expansión Urbana y Humedales")
st.markdown("Análisis espacial de la cobertura de suelo y la presión inmobiliaria sobre la red de humedales en la comuna de Valdivia.")

# 4. Configuración del Mapa Folium
# Coordenadas centrales ajustadas para abarcar la comuna completa
LAT_CENTRO = -39.8200
LON_CENTRO = -73.3000

# Inicializar el mapa base con un zoom más amplio (10 en lugar de 12)
m = folium.Map(location=[LAT_CENTRO, LON_CENTRO], zoom_start=10, control_scale=True)

# Lógica para renderizar el mapa base seleccionado por el usuario
if mapa_base == "Esri Satélite":
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satélite',
        overlay=False,
        control=True
    ).add_to(m)
elif mapa_base == "CartoDB Positron":
    folium.TileLayer(
        tiles='CartoDB Positron',
        name='CartoDB Positron',
        overlay=False,
        control=True
    ).add_to(m)
else:
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap',
        overlay=False,
        control=True
    ).add_to(m)

# Añadir el control de capas de Folium
folium.LayerControl().add_to(m)

# 5. Renderizar el mapa dentro de Streamlit
st_folium(m, width=1200, height=650)