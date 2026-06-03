import osmnx
import networkx
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed" 

#Crea il grafo corrispondente al network stradale e salvalo, solo quando serve

G = osmnx.graph_from_place(
   "Veneto, Italy",
    network_type="drive"
)
osmnx.io.save_graphml(G, PROCESSED / "padova.graphml")

#Carica il grafo, se già salvato

#G = osmnx.io.load_graphml(PROCESSED / "padova.graphml")

#print("Numero nodi:", len(G.nodes))
#print("Numero archi:", len(G.edges))
#print(list(G.edges(data=True))[:3])
#osmnx.plot_graph(G)

df = pd.read_csv(PROCESSED / "comuni_veneto.csv")

nrcomuni = len(df)
#Mappa ogni comune ad un punto sul grafo

def snap_to_graph(G, lon, lat):
    return osmnx.distance.nearest_nodes(G, X=lon, Y=lat)

nodes = []
i = 0
for _, row in df.iterrows():
    node_id = snap_to_graph(G, row["lon"], row["lat"])
    
    nodes.append({
        "codice_istat": row["codice_istat"],
        "nome_comune": row["nome_comune"],
        "node_osm": node_id
    })
    i = i+1
    if i % 10 == 0:
        print(f"Progresso: {i}/{nrcomuni}")

df_nodes = pd.DataFrame(nodes)

#print(df_nodes.head())

df_nodes.to_csv(PROCESSED / "comuni_nodi_osm.csv", index=False)

# =========================
# COSTRUZIONE MATRICE DISTANZE
# =========================

node_list = df_nodes["node_osm"].tolist()
codes = df_nodes["codice_istat"].tolist()

n = len(node_list)


print(n)
print(nrcomuni)

# matrice NxN
dist_matrix = np.zeros((n, n))

print("Calcolo distanze su grafo...")

for i, node_i in enumerate(node_list):

    # shortest path da nodo i a tutti gli altri
    lengths = networkx.single_source_dijkstra_path_length(
        G,
        node_i,
        weight="length"
    )

    for j, node_j in enumerate(node_list):
        dist_matrix[i, j] = lengths.get(node_j, np.inf)

    if i % 10 == 0:
        print(f"Progresso: {i}/{nrcomuni}")

# =========================
# DATAFRAME FINALE
# =========================

df_dist = pd.DataFrame(
    dist_matrix,
    index=codes,
    columns=codes
)

df_dist.to_csv(PROCESSED / "distanze_comuni.csv")

print("Matrice distanze salvata")