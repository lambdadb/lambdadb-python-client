# IndexConfigsText

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `type` | [models.TypeText](typetext.md) | :heavy_check_mark: | N/A |
| `analyzers` | List[[models.Analyzer](analyzer.md)] | :heavy_minus_sign: | Text analyzers to apply to this field. Use the lowercase names listed below and avoid duplicates. Defaults to ["standard"] when omitted. Each selected analyzer indexes the field separately; language detection is not automatic. An empty array does not use the default. See the Choose text analyzers guide for Chinese and CJK tradeoffs. All names are fixed presets for text fields; keyword is an analyzer, not the keyword field type. Custom pipelines and analyzer options are not supported. Nepali, Tamil, and Telugu are Lucene extensions, not shared Elasticsearch/OpenSearch support. |
| `description` | *Optional[str]* | :heavy_minus_sign: | Optional free-form explanation of what the field holds, up to 255 characters. Returned in collection reads only when set and never affects indexing. On update, omitting it or `None` keeps the stored description, `""` clears it, and any other value replaces it without reindexing. Not accepted on the server-managed `id` field. |
