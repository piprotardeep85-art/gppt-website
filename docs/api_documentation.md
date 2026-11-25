# API Documentation

Interactive OpenAPI documentation is available at `/docs`.

## Text scan

`POST /api/scan/text`

```json
{"text":"Pay a registration fee immediately.","language":"en"}
```

## URL scan

`POST /api/scan/url`

```json
{"url":"https://careers.example.com/jobs/123"}
```

## Health

`GET /api/health`
