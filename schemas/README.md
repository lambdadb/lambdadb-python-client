# Analyzer contract maintenance

`text-analyzers.json` is a scoped SDK schema: its original analyzer property
comes from [OpenAPI at docs revision 3bda642](https://github.com/lambdadb/docs/blob/3bda642f2e7f4f26432f1dfdcb076f656d50f873/reference/api/openapi.json).
`source` retains that base revision, path, and JSON pointer. `extension` pins
33 additional names to [backend PR #437](https://github.com/lambdadb/lambdadb/pull/437),
merge [55d888299fee44466326a9db8016af9811ade13b](https://github.com/lambdadb/lambdadb/blob/55d888299fee44466326a9db8016af9811ade13b/core/src/main/java/ai/lambdadb/core/IndexingConstants.java).
The 49-name schema is adapted from that backend allowlist, not an exact copy of
a 49-name upstream OpenAPI property. The original 16 names and enum order are
preserved. These pins identify source contracts, not API deployment.

The upstream OpenAPI inspected at docs revision
`961561c379acb079aec20191e13b89809ef096e9` still lists 16 names and adds duplicate
validation. Neither that unrelated validation change nor any other intervening
API changes are imported here. Upstream OpenAPI propagation remains separate.

The SDK originated from Speakeasy, but its configuration and workflow were
removed in commit `f74e6ef55660e63f01f26ac7792e1855a5f7075d`. There is no current
full-SDK generation command in this repository. For analyzer changes, maintain
this scoped source and regenerate only the enum, field descriptions, and model
references:

```bash
python3 scripts/generate_analyzers.py
python3 scripts/generate_analyzers.py --check
```

To update the source, inspect an exact upstream docs/backend commit. Keep the
base `source` metadata and the backend `extension` metadata accurate: a backend
allowlist adaptation must not be described as an extracted OpenAPI property.
Compare all names and defaults before regeneration. Run
`tests/test_analyzers.py`; it also checks generated outputs. Review the diff for
unrelated changes.

The schema's `["standard"]` default describes server behavior. Generation does
not populate a client default or change the existing optional field and
serializer. Omission remains omission; empty and duplicate lists are passed
through without added validation. The broader `API_CONTRACT_REVISION` remains
the existing base contract: this snapshot pins only the analyzer extension and
does not claim that unrelated intervening OpenAPI changes have been ported.

## Consumer impact

The enum is shared by the text model, TypedDict, collection create/update
requests, nested object index configs, and collection response parsing. The
serializer needs no changes. SDK analyzer values remain lowercase and
case-sensitive, although the backend selects analyzers case-insensitively and
preserves configured suffixes. No case normalization is introduced here.

This repository has no CLI, ES/OpenSearch importer, or complete OpenAPI file.
Its Qdrant compatibility layer has a payload schema mapping used by both
`create_collection` and `create_payload_index`. Explicit LambdaDB-style
`{"type": "text", "analyzers": ["simple"]}` mappings preserve supported names;
omitting `analyzers` preserves the server default. Other options (including
Qdrant tokenizer/lowercase settings or custom pipeline settings) fail explicitly.
Qdrant tokenizer names are not interpreted as LambdaDB analyzer names.
`keyword` with `type: text` stays distinct from `type: keyword`.

All names are fixed presets. Nepali/Tamil/Telugu are Lucene extensions, not
shared Elasticsearch/OpenSearch support. Deployment verification, live smoke,
upstream documentation/schema propagation, and package publication are separate
follow-up work; this local change does not establish any of those outcomes.
