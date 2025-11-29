import networkx as nx
import enum
import json
from pathlib import Path


class WeightType(enum.Enum):
    LENGTH = "weight"
    HOPS = "hops"
    NONE = None


spaces = 3
topologies = ["nsfnet", "arpanet", "eurocore", "uknet", "eon"]
routes_output_name = "routes"
network_output_name = "network"
centrality_output_name = "betweenness_centrality"


bands_info = {"C": 344, "L": 480, "S": 760, "E": 1136}


def main():
    for topology in topologies:
        output_dir = f"./scripts/results/{topology}/"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        G = nx.Graph()
        network_filename = f"./scripts/topologies-txt/{topology}.txt"
        json_id_nodes = []
        divider = " "

        with open(network_filename) as f:
            file = f.readlines()
            nodes = int(file[1])

            # For para nodes
            for i in range(nodes):
                json_id_nodes.append({"id": i})

            # For para topologias
            for line in file[3 : len(file)]:
                split_data = line.split(divider)
                src = int(split_data[0]) - 1
                dst = int(split_data[1]) - 1

                G.add_edge(src, dst, weight=int(split_data[2]))
                G.add_edge(dst, src, weight=int(split_data[2]))

        # Calcular betweenness centrality para nodos
        node_betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)

        # Ordenar los nodos de mayor a menor centralidad
        sorted_nodes = sorted(
            node_betweenness.items(), key=lambda item: item[1], reverse=True
        )
        sorted_nodes_list = [
            {"node": node, "centrality": score} for node, score in sorted_nodes
        ]

        # Calcular betweenness centrality para enlaces (lo que necesitas)
        edge_betweenness = nx.edge_betweenness_centrality(
            G, weight="weight", normalized=True
        )

        # Ordenar los enlaces de mayor a menor centralidad
        # Se convierten las tuplas de los enlaces (e.g., (0, 1)) a strings (e.g., "0-1") para que sea compatible con JSON
        sorted_edges = sorted(
            edge_betweenness.items(), key=lambda item: item[1], reverse=True
        )
        sorted_edges_str_keys = [
            {"edge": f"{u}-{v}", "centrality": score} for (u, v), score in sorted_edges
        ]

        # Preparar datos para el archivo JSON
        centrality_data = {
            "topology": topology,
            "node_betweenness_centrality_ordered": sorted_nodes_list,
            "most_used_links_ordered": sorted_edges_str_keys,
        }

        # Guardar los resultados en un archivo JSON
        json_object = json.dumps(centrality_data, indent=4)
        output_path = Path(output_dir) / f"{centrality_output_name}.json"
        with open(output_path, "w") as outfile:
            outfile.write(json_object)


main()
