from logging import basicConfig, getLogger
from typing import Any, NamedTuple

import geopandas as gpd
import overpy
import shapely
import streamlit as st
from folium import FeatureGroup, GeoJson, GeoJsonTooltip, LayerControl, Map, Marker, TileLayer
from streamlit_folium import st_folium
from xyzservices import TileProvider

import geohash

logger = getLogger(__name__)

PRECISION = 4


def query(lat_min: float, lon_min: float, lat_max: float, lon_max: float) -> str:
    return f"""\
node({lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f})["highway" = "motorway_junction"];
way(bn)["highway" ~ "^motorway_link$|^motorway$"];
(._;>;);
out body;
"""


@st.cache_data
def branches(query: str) -> dict[str, Any]:
    logger.info(f"query: {query!r}")
    api = overpy.Overpass()
    result = api.query(query)
    logger.info(f"result: {len(result.ways)}")
    D = {}
    for way in result.ways:
        nodes = []
        latlons = []
        for n in way.nodes:
            if n.tags.get("highway") == "motorway_junction":
                nodes.append(n)
            latlons.append(shapely.Point(n.lon, n.lat))
        for node in nodes:
            item = way.tags.copy()
            item["geometry"] = shapely.LineString(latlons)
            item["node_id"] = node.id
            item["lat0"] = float(node.lat)
            item["lon0"] = float(node.lon)
            highway = way.tags.get("highway")
            if highway == "motorway" or highway == "motorway_link":
                if node.id not in D:
                    D[node.id] = {}
                if highway not in D[node.id]:
                    D[node.id][highway] = {}
                D[node.id][highway].update(item)
    r = {}
    for node_id, ways in D.items():
        if "motorway" in ways and "motorway_link" in ways:
            r[node_id] = ways["motorway"]
            r[node_id].update(ways["motorway_link"])
    return r


class Rect(NamedTuple):
    miny: float
    minx: float
    maxy: float
    maxx: float

    @property
    def width(self):
        return self.maxx - self.minx

    @property
    def height(self):
        return self.maxy - self.miny

    @property
    def centroid(self):
        return ((self.maxy + self.miny) / 2.0, (self.maxx + self.minx) / 2.0)

    def contains(self, other: "Rect"):
        return shapely.box(*self).contains(shapely.box(*other))


def main():
    st.set_page_config(layout="wide")

    basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", force=True)
    logger.setLevel("INFO")

    st.header("Map")

    m = Map(tiles=None)
    TileLayer(
        TileProvider(
            {
                "name": "Google Hybrid",
                "url": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                "attribution": "(c) Google",
            }
        )
    ).add_to(m)
    TileLayer(
        TileProvider(
            {
                "name": "Google Roadmap",
                "url": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
                "attribution": "(c) Google",
            }
        )
    ).add_to(m)
    ls = []

    col1, col2 = st.columns([2, 1])

    codes = None
    gdf = None
    box = st.session_state.get("box")
    if box is not None:
        logger.info(f"request: {box}")

        codes = st.session_state.setdefault("codes", set())
        data = {}
        for code in geohash.create_rect(*box, PRECISION):
            codes.add(code)
            data.update(branches(query(*geohash.decode(code))))

        if data:
            gdf = gpd.GeoDataFrame.from_dict(data, orient="index", crs="EPSG:4326")
            geojson = FeatureGroup(name="branch")
            geojson.add_child(
                GeoJson(
                    gdf,
                    tooltip=GeoJsonTooltip(gdf.columns.drop("geometry").to_list()),
                    overlay=False,
                ),
            )
            markers = FeatureGroup(name="marker")
            for lat0, lon0 in zip(gdf["lat0"], gdf["lon0"]):
                markers.add_child(Marker(location=[lat0, lon0]))  # type: ignore
            ls.append(geojson)
            ls.append(markers)

    layer_control = LayerControl()
    with col1:
        st_data = st_folium(
            m,
            key="map",
            width=500,
            height=700,
            center=(32.8400948, -97.3542091),
            zoom=15,
            use_container_width=True,
            feature_group_to_add=ls,
            layer_control=layer_control,
        )

    st.subheader("query")
    if codes is not None:
        st.code(codes)
    else:
        st.info("No code")
    st.subheader("result")
    if gdf is not None:
        st.dataframe(gdf.drop(columns=["geometry"]))
    else:
        st.info("No dataframe")

    try:
        box = Rect(
            float(st_data["bounds"]["_southWest"]["lat"]),
            float(st_data["bounds"]["_southWest"]["lng"]),
            float(st_data["bounds"]["_northEast"]["lat"]),
            float(st_data["bounds"]["_northEast"]["lng"]),
        )
        lat, lon = box.centroid
    except (KeyError, TypeError) as e:
        lat, lon = 32.8400948, -97.3542091
        box = Rect(
            lat - 0.05,
            lon - 0.05,
            lat + 0.05,
            lon + 0.05,
        )

    if st_data["zoom"] >= 12:
        codes = st.session_state.get("codes")
        if codes is None:
            logger.info("rerun")
            st.session_state.box = box
            st.rerun()
        elif st.session_state.get("box") is None:
            st.session_state.box = box
            st.rerun()
        else:
            for code in geohash.create_rect(*box, PRECISION):
                if code not in codes:
                    logger.info("rerun")
                    st.session_state.box = box
                    st.rerun()
    elif st.session_state.get("box") is not None:
        st.session_state.box = None
        st.rerun()

    with col2:
        st.write(st_data)


if __name__ == "__main__":
    main()
