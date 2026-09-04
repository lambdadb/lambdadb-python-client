# ListDocsRequest

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `collection_name` | `str` | Yes | Collection name. |
| `size` | `Optional[int]` | No | Maximum documents returned at once. |
| `page_token` | `Optional[str]` | No | Opaque token from the previous page. |
| `include_vectors` | `Optional[bool]` | No | Include vector values. |
| `ref_kind` | `Optional[RefKind]` | No | Pair with `ref_name`. |
| `ref_name` | `Optional[str]` | No | Read ref name; pair with `ref_kind`. |
