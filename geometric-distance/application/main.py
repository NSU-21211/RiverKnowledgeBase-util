import json
import logging
from typing import Any

from geopy.distance import geodesic

# Way example:
# file_name = "ob_way_river.geojson"

# Relation example:
# file_name = "ob_relation_river.geojson"

# Relation example with inflows:
file_name = "ob_with_inflows_river.geojson"

with open("resources/examples/" + file_name) as geojson_file:
    geojson_data = json.load(geojson_file)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def initialize_logger() -> None:
    logger_formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s")
    logger_handler = logging.FileHandler(filename="logs/app-info.log", mode="w")
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)


def calculate_river_length(*, river_name: str) -> float:
    river_features = [feature for feature in geojson_data["features"] if river_name in feature["properties"]["name"]]
    distance_km = 0
    for feature in river_features:
        if feature["geometry"]["type"] == "LineString":
            river_coordinates = feature["geometry"]["coordinates"]
            for i in range(len(river_coordinates) - 1):
                prepared_first_point = tuple(reversed(river_coordinates[i]))  # convert to (latitude, longitude)
                prepared_second_point = tuple(reversed(river_coordinates[i + 1]))
                distance_km += geodesic(prepared_first_point, prepared_second_point).kilometers
        elif feature["geometry"]["type"] == "MultiLineString":
            for coordinates_line in feature["geometry"]["coordinates"]:
                for i in range(len(coordinates_line) - 1):
                    prepared_first_point = tuple(reversed(coordinates_line[i]))  # convert to (latitude, longitude)
                    prepared_second_point = tuple(reversed(coordinates_line[i + 1]))
                    distance_km += geodesic(prepared_first_point, prepared_second_point).kilometers

    return distance_km


def find_inflows(*, river_name: str):
    return [feature for feature in geojson_data["features"] if river_name not in feature["properties"]["name"]]


def find_mouth_position_for_river(*, river_feature) -> tuple[Any, ...]:
    mouth_coordinates = tuple()
    if river_feature["geometry"]["type"] == "MultiLineString":
        inflow_coordinates = river_feature["geometry"]["coordinates"]
        last_coordinate_line = inflow_coordinates[len(inflow_coordinates) - 1]
        mouth_coordinates = tuple(reversed(last_coordinate_line[len(last_coordinate_line) - 1]))
    elif river_feature["geometry"]["type"] == "LineString":
        inflow_coordinates = river_feature["geometry"]["coordinates"]
        mouth_coordinates = tuple(reversed(inflow_coordinates[len(inflow_coordinates) - 1]))

    return mouth_coordinates


# Координаты устья - последняя координата из всех координат
def find_mouth_position_for_inflows(*, base_river_name: str) -> list[tuple[str, tuple[Any, ...]]]:
    inflows = find_inflows(river_name=base_river_name)
    mouth_positions = list()
    for feature in inflows:
        mouth_coordinates = find_mouth_position_for_river(river_feature=feature)
        mouth_positions.append((feature["properties"]["name"], mouth_coordinates))

    return mouth_positions


def calculate_distances_from_river_to_inflows(*, base_river_name: str,
                                              inflows_mouth_positions: list[tuple[str, tuple[Any, ...]]]):
    river_features = [feature for feature in geojson_data["features"] if
                      base_river_name in feature["properties"]["name"]]
    base_river_mouth_position = find_mouth_position_for_river(river_feature=river_features[0])

    distances_from_inflows = list()
    for inflow_tuple in inflows_mouth_positions:
        inflow_name = inflow_tuple[0]
        inflow_distance = geodesic(base_river_mouth_position, inflow_tuple[1]).kilometers
        distances_from_inflows.append((inflow_name, inflow_distance))

    return distances_from_inflows


def application_entrypoint(*, river_name: str) -> None:
    initialize_logger()
    logger.info(f"Received event with river=\"{river_name}\"")
    river_length = calculate_river_length(river_name=river_name)
    inflows_rivers = find_inflows(river_name=river_name)

    logger.info(f"Length of river=\"{river_name}\" is: {river_length} km")
    logger.info(f"Count of inflows for river=\"{river_name}\": {len(inflows_rivers)}")

    inflows_mouth_positions = find_mouth_position_for_inflows(base_river_name=river_name)
    logger.info(f"Call method calculate_distances_from_river_to_inflows for river=\"{river_name}\"")
    distances_from_inflows = calculate_distances_from_river_to_inflows(base_river_name=river_name,
                                              inflows_mouth_positions=inflows_mouth_positions)
    logger.info(f"Distances from mouth of river=\"{river_name}\":")
    for inflow_tuple in distances_from_inflows:
        logger.info(f"\tFrom \"{inflow_tuple[0]}\": distance={inflow_tuple[1]} km")


if __name__ == "__main__":
    application_entrypoint(river_name="Обь")

# Overpass API Query:
"""
    [out:json][timeout:30];
    (
        relation[waterway=river][name="Обь"]({{bbox}}) -> .river;
        relation[waterway=river][destination="Обь"]({{bbox}}) -> .inflows;
    );
    out body;
    >;
    out skel qt;
"""
