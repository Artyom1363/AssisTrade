# Transactions Service
## Base info
Service works in following flow:

User query -> Supervisor agent -> NER agent -> TX

## Example

```python
message: "отправь 0.01 ETH Ивану Иванову"

response:
{
  "status": "Build",
  "transaction": {
    "to": "Иван Иванов",
    "value": 0.01
  },
  "reasoning": "Мы можем построить транзакцию, так как сообщение содержит значение и имя получателя."
}
```

In Future:
`MCP-server for Metamask extension`
