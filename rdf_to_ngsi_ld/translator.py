from io import BytesIO
from kafka import KafkaConsumer
import logging
import ngsi_ld_client
from ngsi_ld_client.api_client import ApiClient as NGSILDClient
from ngsi_ld_client.configuration import Configuration as NGSILDConfiguration
from ngsi_ld_client.exceptions import ApiException
from ngsi_ld_client.models.query_entity200_response_inner import QueryEntity200ResponseInner
import os
from pyoxigraph import Literal, parse

## -- BEGIN RETRIEVAL OF ENVIRONMENTAL VARIABLES -- ##

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "knowledge-graphs")
NGSI_LD_BROKER = os.getenv("BROKER_URI", "http://orion-ld:1026/ngsi-ld/v1")

## -- END RETRIEVAL OF ENVIRONMENTAL VARIABLES -- ##

## -- BEGIN LOGGING  CONFIGURATION -- ##

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

## -- END LOGGING CONFIGURATION -- ##

## -- BEGIN CONSTANTS DEFINITION -- ##

USER_TYPE = "https://gitlab.aeros-project.eu/wp4/t4.1/aeros-continuum#/User"
ORGANIZATION_TYPE = "http://www.w3.org/ns/org#Organization"
ROLE_TYPE = "http://www.w3.org/ns/org#Role"
MEMBERSHIP_TYPE = "http://www.w3.org/ns/org#Membership"

## -- END CONSTANTS DEFINITION -- ## 

## -- BEGIN DEFINITION OF AUXILIARY FUNCTIONS/CLASSES -- ##

class PreEntity(object):
    def __init__(self, id: str, type: str, attributes: dict):
        self.id = id
        self.type = ngsi_ld_client.EntityType(type)
        self.attributes = attributes

def generate_dict_buffers(message) -> list:
    dict_buffers = []

    triples = list(parse(BytesIO(message.value), 'application/n-quads'))
    subjects = []
    for triple in triples:
        if triple.subject in subjects:
            continue
        subjects.append(triple.subject)

    for subject in subjects:
        dict_buffer = {}
        dict_buffer["id"] = subject.value
        dict_buffer["type"] = ""
        dict_buffer["attributes"] = {}
        pos = [(p, o) for s, p, o, _ in triples if s == subject]
        for p, o in pos:
            if p.value == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                dict_buffer["type"] = o.value
            elif p.value == "http://www.w3.org/2000/01/rdf-schema#subClassOf":
                dict_buffer["attributes"][p.value] = {}
                dict_buffer["attributes"][p.value]["type"] = "Property"
                dict_buffer["attributes"][p.value]["value"] = o.value
            elif isinstance(o, Literal): # Properties:
                if o.datatype.value == "http://www.w3.org/2001/XMLSchema#DateTime":
                    dict_buffer["attributes"][p.value] = {}
                    dict_buffer["attributes"][p.value]["type"] = "Property"
                    dict_buffer["attributes"][p.value]["value"] = o.value.isoformat()
                else:
                    dict_buffer["attributes"][p.value] = {}
                    dict_buffer["attributes"][p.value]["type"] = "Property"
                    dict_buffer["attributes"][p.value]["value"] = o.value
            else: # Relationships:
                dict_buffer["attributes"][p.value] = {}
                dict_buffer["attributes"][p.value]["type"] = "Relationship"
                dict_buffer["attributes"][p.value]["object"] = o.value
        dict_buffers.append(dict_buffer)
    
    return dict_buffers[::-1]

def init_ngsi_ld_client():
    configuration = NGSILDConfiguration(host=NGSI_LD_BROKER)
    configuration.debug = True
    ngsi_ld = NGSILDClient(configuration=configuration)

    ngsi_ld.set_default_header(
        header_name="Accept",
        header_value="application/json"
    )

    return ngsi_ld

def create_ngsi_ld_entity(ngsi_ld, entity: PreEntity) -> bool:
    result = False

    api_instance = ngsi_ld_client.ContextInformationProvisionApi(ngsi_ld)

    try:
        api_response = api_instance.create_entity(
            query_entity200_response_inner=ngsi_ld_client.QueryEntity200ResponseInner(
                    id=entity.id,
                    type=entity.type,
                    additional_properties=entity.attributes
            )
        )
        result = True
    except Exception as e:
        logger.exception("Exception when calling ContextInformationProvisionApi->create_entity: %s\n" % e)
        result = False

    return result

def check_ngsi_ld_entity_exists(ngsi_ld, entity_id: str) -> bool:
    result = False

    api_instance = ngsi_ld_client.ContextInformationConsumptionApi(ngsi_ld)

    try:
        api_response = api_instance.retrieve_entity(entity_id)
        result = True
    except Exception as e:
        logger.exception("Exception when calling ContextInformationConsumptionApi->retrieve_entity: %s\n" % e)
        result = False

    return result

def update_ngsi_ld_entity(ngsi_ld, entity: PreEntity) -> bool:
    result = False

    api_instance = ngsi_ld_client.ContextInformationProvisionApi(ngsi_ld)

    try:
        api_response = api_instance.update_entity(
            entity_id=entity.id,
            entity=ngsi_ld_client.Entity(
                additional_properties=entity.attributes
            )
        )
        result = True
    except Exception as e:
        logger.exception("Exception when calling ContextInformationProvisionApi->update_entity: %s\n" % e)
        result = False

    return result

## -- END DEFINITION OF AUXILIARY FUNCTIONS/CLASSES -- ##

## -- BEGIN MAIN CODE -- ##

consumer = KafkaConsumer('knowledge-graphs', bootstrap_servers=['kafka:9092'])

ngsi_ld = init_ngsi_ld_client()

while True:
    for message in consumer:
        dict_buffers = generate_dict_buffers(message)

        for dict_buffer in dict_buffers:
            entity_id = dict_buffer["id"]
            entity_type = dict_buffer["type"]
            entity_attributes = dict_buffer["attributes"]

            logger.info("Dictionary buffer contains information for entity " + entity_id)

            entity = PreEntity(
                id = entity_id,
                type = entity_type,
                attributes = entity_attributes
            )

            exists = check_ngsi_ld_entity_exists(ngsi_ld, entity_id)
            if exists == False:
                logger.info("Entity " + entity_id + " DOES NOT EXIST. Trying to create it...")
                created = create_ngsi_ld_entity(ngsi_ld, entity)
                if created == False:
                    logger.info("Entity " + entity_id + " COULD NOT BE CREATED")
                else:
                    logger.info("Entity " + entity_id + " WAS SUCCESSFULLY CREATED")
            else:
                logger.info("Entity " + entity_id + " DOES EXIST")
                if bool(entity_attributes) == False:
                    logger.info("Attributes dictionary for Entity " + entity_id + " is empty. There is no need to update it. Skipping it...")
                    continue
                else:
                    logger.info("Attributes dictionary for Entity " + entity_id + " is not empty. Trying to update it...")
                    updated = update_ngsi_ld_entity(ngsi_ld, entity)
                    if updated == False:
                        logger.info("Entity " + entity_id + " COULD NOT BE UPDATED")
                    else:
                        logger.info("Entity " + entity_id + " WAS SUCCESSFULLY UPDATED")

## -- END MAIN CODE -- ##
