# IndexConfigsText

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `type` | [models.TypeText](typetext.md) | :heavy_check_mark: | N/A |
| `analyzers` | List[[models.Analyzer](analyzer.md)] | :heavy_minus_sign: | Text analyzers to apply to this field. Use the lowercase names listed below and avoid duplicates. Defaults to ["standard"] when omitted. Each selected analyzer indexes the field separately; language detection is not automatic. An empty array does not use the default. See the Choose text analyzers guide for Chinese and CJK tradeoffs. |
