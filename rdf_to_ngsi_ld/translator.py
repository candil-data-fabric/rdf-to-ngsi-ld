import argparse
import json
import logging

import ngsi_ld_client
from kafka import KafkaConsumer
from ngsi_ld_client import (ContextInformationConsumptionApi,
                            ContextInformationProvisionApi, Entity, EntityType)
from ngsi_ld_client.api_client import ApiClient as NGSILDClient
from ngsi_ld_client.configuration import Configuration as NGSILDConfiguration
from ngsi_ld_client.exceptions import ApiException
from rdflib import Graph, Literal
from rdflib.namespace import RDF, XSD

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)

def serializer(rdf_graph: Graph) -> list[Entity]:
    subjects = []
    for subject in rdf_graph.subjects():
        if subject in subjects:
            continue
        subjects.append(subject)

    ngsild_entities = []
    for subject in subjects:
        dict_buffer = {}
        dict_buffer["id"] = subject
        dict_buffer["type"] = ""
        dict_buffer["attributes"] = {}
        for p, o in rdf_graph.predicate_objects(subject):
            if p == RDF.type:
                dict_buffer["type"] = o
            elif isinstance(o, Literal): # Properties:
                if o.datatype == XSD.dateTime:
                    dict_buffer["attributes"][p] = {}
                    dict_buffer["attributes"][p]["type"] = "Property"
                    dict_buffer["attributes"][p]["value"] = o.isoformat()
                else:
                    dict_buffer["attributes"][p] = {}
                    dict_buffer["attributes"][p]["type"] = "Property"
                    dict_buffer["attributes"][p]["value"] = o
            else: # Relationships:
                dict_buffer["attributes"][p] = {}
                dict_buffer["attributes"][p]["type"] = "Relationship"
                dict_buffer["attributes"][p]["object"] = o

        ngsild_entity = Entity(
            id=dict_buffer["id"],
            type=EntityType(dict_buffer["type"]),
            additional_properties=dict_buffer["attributes"]
        )
        ngsild_entities.append(ngsild_entity)
    return ngsild_entities

def create_ngsi_ld_entity(ngsi_ld: NGSILDClient, entity: Entity) -> bool:
    api_instance = ContextInformationProvisionApi(ngsi_ld)
    try:
        api_instance.create_entity(
            query_entity200_response_inner=ngsi_ld_client.QueryEntity200ResponseInner(
                    id=entity.id,
                    type=entity.type,
                    additional_properties=entity.additional_properties
            )
        )
    except ApiException as e:
        logger.warning(e)
        return False
    return


def check_ngsi_ld_entity_exists(ngsi_ld: NGSILDClient, entity_id: str) -> bool:
    api_instance = ContextInformationConsumptionApi(ngsi_ld)
    try:
        api_instance.retrieve_entity(entity_id)
    except ApiException as e:
        logger.warning(e)
        return False
    return True

def update_ngsi_ld_entity(ngsi_ld: NGSILDClient, entity: Entity) -> bool:
    api_instance = ContextInformationProvisionApi(ngsi_ld)
    try:
        api_instance.merge_entity(
            entity_id=entity.id,
            entity=entity
        )
    except ApiException as e:
        logger.warning(e)
        return False
    return True

def send_to_context_broker(entities: list[Entity], context_broker: str, debug: bool):
    # Init NGSI-LD Client
    configuration = NGSILDConfiguration(host=context_broker)
    configuration.debug = debug
    ngsild_client = NGSILDClient(configuration=configuration)

    for entity in entities:
        exists = check_ngsi_ld_entity_exists(ngsild_client, entity.id)
        if exists == False:
            logger.info("Entity " + entity.id + " Does not exist. Trying to create it...")
            create_ngsi_ld_entity(ngsild_client, entity)
        else:
            logger.info("Entity " + entity.id + " already created. Updating...")
            update_ngsi_ld_entity(ngsild_client, entity)


def send_to_file(entities: list[Entity], output_file: str) :
    """Stores NGSI-LD Entities in a JSON file"""
    with open(output_file, "w") as file:
        json_data = [ entity.to_dict() for entity in entities]
        json_output = json.dumps(json_data, indent=4)
        file.write(json_output)

# Run translator as script
def main():
    """Run the program as a script to consume RDF data from Kafka and store it."""
    parser = argparse.ArgumentParser(description="Consume RDF data from Kafka and store it.")
    parser.add_argument('--kafka-topic', help="Kafka topic to consume RDF data from.")
    parser.add_argument('--kafka-server', help="Kafka bootstrap server.")
    parser.add_argument('--input-file', help="Path to the RDF file to process.")
    parser.add_argument(
        '--rdf-format',
        choices=['turtle', 'nt'],
        default='turtle',
        required=True,
        help="Format of the input RDF data."
    )
    parser.add_argument('--context-broker', help="NGSI-LD Context Broker endpoint.")
    parser.add_argument('--output-file', help="Store NGSI-LD data in file.")
    parser.add_argument('--debug', default=False, help="Debug mode.")
    args = parser.parse_args()

    if args.input_file:
        logging.info(f"Processing RDF data from file: {args.input_file}")
        rdf_graph = Graph()
        rdf_graph.parse(args.input_file, format=args.rdf_format)
        ngsild_data = serializer(rdf_graph)
        if args.output_file:
            send_to_file(ngsild_data, args.output_file)
        if args.context_broker:
            send_to_context_broker(ngsild_data, args.context_broker, args.debug)

    elif args.kafka_topic and args.bootstrap_servers:
        logging.info(f"Processing RDF data from Kafka topic: {args.kafka_topic}")
        consumer = KafkaConsumer(
            args.kafka_topic,
            bootstrap_servers=args.kafka_server,
            enable_auto_commit=True
        )
        for rdf_data in consumer:
            rdf_graph = Graph()
            rdf_graph.parse(rdf_data, format=args.rdf_format)
            ngsild_data = serializer(rdf_graph)
            if args.output_file:
                send_to_file(ngsild_data, args.output_file)
            if args.context_broker:
                send_to_context_broker(ngsild_data, args.context_broker, args.debug)

if __name__ == "__main__":
    main()
