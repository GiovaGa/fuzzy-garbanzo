import geopandas as gpd
import pandas as pd

# =========================
# CONFIGURAZIONE
# =========================

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SHAPEFILE = BASE_DIR / "data" / "raw" / "Com01012026" /"Com01012026_WGS84.shp"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "comuni_veneto.csv"

# =========================
# LETTURA SHAPEFILE
# =========================

gdf = gpd.read_file(SHAPEFILE)

print("CRS originale:", gdf.crs)
print("Colonne disponibili:")
print(gdf.columns.tolist())
print(gdf.head())
print(gdf.columns)
print(gdf["COD_REG"].unique())
print(gdf["COD_REG"].dtype)
# =========================
# FILTRO VENETO
# =========================

# Regione Veneto = codice ISTAT regionale 05
gdf_veneto = gdf[gdf["COD_REG"] == 5].copy()

print(f"Comuni trovati: {len(gdf_veneto)}")

# =========================
# PUNTO RAPPRESENTATIVO
# =========================

# Più robusto del centroide:
# garantisce che il punto sia interno al comune
gdf_veneto["rep_point"] = gdf_veneto.geometry.representative_point()

# =========================
# ESTRAZIONE COORDINATE
# =========================

points = gpd.GeoSeries(
    gdf_veneto["rep_point"],
    crs=gdf_veneto.crs
)

# Conversione in WGS84 se necessario
if points.crs.to_epsg() != 4326:
    points = points.to_crs(epsg=4326)

gdf_veneto["lon"] = points.x
gdf_veneto["lat"] = points.y

# =========================
# COSTRUZIONE TABELLA
# =========================

result = pd.DataFrame({
    "codice_istat": gdf_veneto["PRO_COM"],
    "nome_comune": gdf_veneto["COMUNE"],
    "lat": gdf_veneto["lat"],
    "lon": gdf_veneto["lon"]
})

result = result.sort_values("nome_comune")

# =========================
# SALVATAGGIO
# =========================

result.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8"
)

print(result.head())
print()
print(f"Salvato in {OUTPUT_CSV}")