---
model: "gpt-4o"
temperature: 0.7
response_schema: AnalysisSchema
---
# ANALYSIS TASK
You are an expert content analyzer.
Please analyze the following text provided by {{ user_name }}:
{{name}}
TEXT:
{{ config_schema }}

Provide your response in the requested schema format.
