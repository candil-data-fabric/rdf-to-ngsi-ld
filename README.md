# RDF to NGSI-LD

This Python project implements a generic translator from RDF to NGSI-LD.

The work takes inspiration from
[rdflib](https://rdflib.readthedocs.io/en/stable/index.html) plugins that store
RDF data in backends like Neo4j (https://github.com/neo4j-labs/rdflib-neo4j).

In this sense, this project provides an rdflib plugin where an NGSI-LD Context
Broker works as the storage backend for RDF data. Additionally, the translator
supports the ingestion of streams of RDF data via Kafka.

## Translation Rules

The following set of rules are applied to translate the RDF data model (triples)
into the NGSI-LD data model (property graph):

- **Subject**: Maps to an NGSI-LD Entity. The URI of the subject in
  the RDF triple is the URI of the NGSI-LD Entity.

  > :warning: This approach does not follow the convention recommended by
  > ETSI CIM, which goes "urn:ngsi-ld:\<entity-type>:\<identifier>".
  > The reason for doing this is to facilitate interoperability between RDF and
  > NGSI-LD.

- **Predicate**:
  - `a` or `rdf:type` predicate maps to the NGSI-LD Entity Type. For example:
  the RDF triple `<http://example.org/people/Bob> a foaf:Person` translates
  into an NGSI-LD Entity of `foaf:Person` type, and URI
  `http://example.org/people/Bob`.

  - **RDF Datatype property** maps to an NGSI-LD Property. A special treatment
  is required when the literal of the predicate uses `xsd:datetime`.
  In this case the resulting NGSI-LD Property must follow the special format:

    ```json
        "myProperty": {
            "type": "Property", "value": {
                "@type": "DateTime",
                "@value": "2018-12-04T12:00:00Z"
            }
        }
    ```

  - **RDF Object property** maps to an NGSI-LD Relationship. The target of the
  Relationship is the URI of the object in the RDF triple.

- **Namespaces**: There is no need to create specific `@context` for translating
  to NGSI-LD. The resulting NGSI-LD Entity can just used expanded the URIs.
  This approach is easier to maintain as avoids maintaining `@context` files.

  Optionally, If the ingested RDF data includes a definition of namespaces
  with prefixes, then this information could be used to generate the
  `@context` for the translated NGSI-LD Entity. The resulting `@context` can be
  send along the NGSI-LD payload or stored elsewhere and reference
  via Link header. The selected approach will depend on the use case
  andthe developer's implementation.

## Translation Modes

The translator could be configured to expect `batches` of RDF data, instead of
`streaming` events. In batching mode, the translator can analyze all RDF triples
for the same subject, bundle the datatype and object properties, and produce
a complete NGSI-LD Entity with a set of Properties and Relationships.
This approach can improve performance as less NGSI-LD requests are sent
to create the Entities in the Context Broker.

## Acknowledgements

This work was partially supported by the following projects:

- **Horizon Europe aerOS**: Autonomous, scalablE, tRustworthy, intelligent European meta Operating System for the IoT edge-cloud continuum. Grant agreement 101069732
- **SNS Horizon Europe ROBUST-6G**: Smart, Automated, and Reliable Security Service Platform for 6G. Grant agreement 101139068
- **UNICO 5G I+D 6G-DATADRIVEN**: Redes de próxima generación (B5G y 6G) impulsadas por datos para la fabricación sostenible y la respuesta a emergencias. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.
- **UNICO 5G I+D 6G-CHRONOS**: Arquitectura asistida por IA para 5G-6G con red determinista para comunicaciones industriales. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.

  ![UNICO](./images/ack-logo.png)
