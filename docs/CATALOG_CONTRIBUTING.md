# Technology catalog contributions

MetropoGits catalogs are versioned JSON data, not executable plugins. A catalog
rule may classify only exact manifest, code, or configuration facts and must
ship with both a matching fixture and a confusing non-matching fixture.

The current contract is [`catalog/0.1`](../schemas/catalog-0.1.schema.json), and
the bundled release is [`0.3.0`](../catalog/0.3.0/catalog.json). Previous
release directories remain unchanged so generated artifact provenance stays
auditable.

## Validate a contribution

Place fixture files under a `fixtures` directory beside `catalog.json`, using
the IDs declared by the rule, and run:

```powershell
python -m metropogits validate --input catalog/0.3.0/catalog.json
```

The standalone validator accepts an explicit fixture root when needed:

```powershell
python scripts/validate_catalog.py path/to/catalog.json --fixtures path/to/fixtures
```

Validation checks the JSON schema, deterministic ordering, exact (non-regex)
signatures, evidence requirements, source/license attribution, and whether each
positive and negative fixture produces the promised result.

## Rule safety levels

- `DECLARED` is for a manifest declaration alone. It may emit a technology tag
  and the `LIBRARY` archetype, but no capability or semantic role.
- `DIRECT` requires an exact code or configuration signature and its matching
  evidence kind. Roles, capabilities, and specialized archetypes require this
  level.

This separation prevents a dependency name or package-name lookalike from
claiming that a technology is actually used. Unknown packages remain ordinary
dependency facts until a reviewed rule has stronger evidence.

## Contribution checklist

1. Add or update one rule with a new semantic version and concise
   `changeSummary`.
2. Use exact package coordinates and exact signatures; wildcards and regular
   expressions are rejected.
3. Add at least one positive fixture and one near-match negative fixture.
4. Cite an authoritative HTTPS reference and identify its license.
5. Run the catalog validator and the full test suite.

Fixture documents use `catalog-fixture/0.1` and contain sorted, unique facts.
Configuration facts use the literal `key=value` form so fixtures never need to
contain raw configuration files or secret values.

## Bundled direct-use mappings

Catalog `0.3.0` combines exact Maven package declarations with exact Java
imports for Spring `RestClient`, Kafka `KafkaTemplate`, MongoDB
`MongoRepository`, RabbitMQ `RabbitTemplate`, and Redis `RedisTemplate`. These
produce `PORT`, `EXCHANGE`, `DOCUMENT_DEPOT`, and `CACHE_TOWER` city archetypes.
A package declaration or similarly named class alone remains unclassified, and
imports never create HTTP or messaging edges without a verified target or
channel.
