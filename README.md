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

