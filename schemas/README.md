# Analyzer contract maintenance

`text-analyzers.json` contains the exact analyzer property extracted from
[OpenAPI at docs revision 3bda642](https://github.com/lambdadb/docs/blob/3bda642f2e7f4f26432f1dfdcb076f656d50f873/reference/api/openapi.json),
the pinned head of [docs PR #63](https://github.com/lambdadb/docs/pull/63).
The source metadata records the full revision, path, and JSON pointer.
The names match [backend PR #417](https://github.com/lambdadb/lambdadb/pull/417)
(head `410154abcdf5275add1df47dcf23c170ed0e0efd`, merge
`a163d66a54ae68cd0e12a19752beea300a3bc8e1`). These pins identify source
contracts, not deployment in an API environment.

The SDK originated from Speakeasy, but its configuration and workflow were
removed in commit `f74e6ef55660e63f01f26ac7792e1855a5f7075d`. There is no current
full-SDK generation command in this repository. For analyzer changes, maintain
this scoped source and regenerate only the enum, field descriptions, and model
references:

```bash
python3 scripts/generate_analyzers.py
python3 scripts/generate_analyzers.py --check
```

To update the source, fetch `reference/api/openapi.json` at an exact docs commit,
extract the property at `source.pointer`, and replace `schema` and
`source.revision` together. Review the upstream diff and compare the names with
the backend before regeneration. Run `tests/test_analyzers.py`; it also checks
that the generated outputs are current. Review the diff for unrelated changes.

The schema's `["standard"]` default describes server behavior. Generation does
not populate a client default or change the existing optional field and
serializer. Omission remains omission; empty and duplicate lists are passed
through without added validation. The broader `API_CONTRACT_REVISION` remains
the existing base contract: this snapshot pins only the analyzer extension and
does not claim that unrelated intervening OpenAPI changes have been ported.
