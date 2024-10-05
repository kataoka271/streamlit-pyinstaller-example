from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = copy_metadata("streamlit_folium")
datas += collect_data_files("streamlit_folium")
