import json
import os
import networkx as nx
import enum
from itertools import islice


class WeightType(enum.Enum):
    LENGTH = "weight"
    HOPS = "hops"
    NONE = None


def main():
    G = nx.Graph()
    absolutepath = os.path.abspath(__file__)
    fileDirectory = str(os.path.dirname(absolutepath))

    filename = fileDirectory + "/routes-txt/nsfnet_chen.txt"
    network_name = "RMSA_NSFNet"

    json_routes = []
    json_id_nodes = []

    divider = " "
    counter = 0

    routes = []
    total_routes = 3
    weight: WeightType = WeightType.LENGTH
    print(weight.value)

    with open(filename) as f:
        file = f.readlines()
        nodes = int(file[1])
        # enlaces = int(archivo[2])

        # For para nodes
        for i in range(nodes):
            json_id_nodes.append({"id": i})

        # For para topologias
        for line in file[3 : len(file)]:
            split_data = line.split(divider)
            src = int(split_data[1]) - 1
            dst = int(split_data[0]) - 1

            G.add_edge(src, dst, weight=int(split_data[2]))
            G.add_edge(dst, src, weight=int(split_data[2]))

            data_rutas_ida = {}
            data_rutas_vuelta = {}

            data_rutas_ida = {
                "dst": src,
                "id": counter,
                "length": int(split_data[2]),
                "slots": 100,
                "src": dst,
            }
            counter += 1
            data_rutas_vuelta = {
                "dst": dst,
                "id": counter,
                "length": int(split_data[2]),
                "slots": 100,
                "src": src,
            }
            counter += 1
            json_routes.append(data_rutas_ida)
            json_routes.append(data_rutas_vuelta)

        # For para rutas
        for initial_node in range(nodes):
            for end_node in range(nodes):
                if initial_node != end_node:
                    X = list(
                        islice(
                            nx.shortest_simple_paths(
                                G,
                                source=initial_node,
                                target=end_node,
                                weight=weight.value,
                            ),
                            total_routes,
                        )
                    )
                    paths = []
                    for counter, path in enumerate(X):
                        paths.append(path)
                        if counter == total_routes - 1:
                            break
                    data_routes = {}
                    data_routes = {
                        "src": initial_node,
                        "dst": end_node,
                        "paths": paths,
                    }
                    routes.append(data_routes)

    data = {
        "alias": network_name,
        "Name": network_name,
        "nodes": json_id_nodes,
        "links": json_routes,
    }

    data_paths_all_nodes = {
        "alias": network_name,
        "name": network_name,
        "routes": routes,
    }

    json_object = json.dumps(data, indent=4)

    with open(
        fileDirectory + "/results-json/" + network_name + ".json", "w"
    ) as outfile_topologia:
        outfile_topologia.write(json_object)

    json_object_rutas = json.dumps(data_paths_all_nodes, indent=4)

    with open(
        fileDirectory + "/results-json/" + network_name + "_routes.json", "w"
    ) as outfile_rutas:
        outfile_rutas.write(json_object_rutas)

    outfile_topologia.close()
    outfile_rutas.close()
    f.close()


main()
