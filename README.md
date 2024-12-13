# RDF to NGSI-LD

This Python project implements a generic translator from RDF to NGSI-LD.

The translator can ingest data from an RDF file or a Kafka stream. The generated
NGSI-LD entities can be sent to both a Context Broker and another file.

## Translation Rules

The following set of rules are applied to translate the RDF data model (triples)
into the NGSI-LD data model (property graph):

- **Subject**: Maps to an NGSI-LD Entity. The URI of the subject in
  the RDF triple is the URI of the NGSI-LD Entity.

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

## Acknowledgements

This work was partially supported by the following projects:

- **Horizon Europe aerOS**: Autonomous, scalablE, tRustworthy, intelligent European meta Operating System for the IoT edge-cloud continuum. Grant agreement 101069732
- **SNS Horizon Europe ROBUST-6G**: Smart, Automated, and Reliable Security Service Platform for 6G. Grant agreement 101139068
- **UNICO 5G I+D 6G-DATADRIVEN**: Redes de próxima generación (B5G y 6G) impulsadas por datos para la fabricación sostenible y la respuesta a emergencias. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.
- **UNICO 5G I+D 6G-CHRONOS**: Arquitectura asistida por IA para 5G-6G con red determinista para comunicaciones industriales. Ministerio de Asuntos Económicos y Transformación Digital. European Union NextGenerationEU.

![UNICO](./images/ack-logo.png)
