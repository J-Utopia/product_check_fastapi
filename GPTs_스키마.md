# GPTs Action 스키마

아래 스키마는 `https://product-check-fastapi.onrender.com` 기준이다.

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Modetour Itinerary Inspection API",
    "version": "2.0.0",
    "description": "모두투어 단체번호를 입력받아 일정표 검수 결과를 반환하는 API"
  },
  "servers": [
    {
      "url": "https://product-check-fastapi.onrender.com"
    }
  ],
  "paths": {
    "/run-itinerary": {
      "post": {
        "operationId": "runItinerary",
        "summary": "단체번호로 일정표 검수를 실행한다",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "group_id": {
                    "type": "string",
                    "description": "모두투어 단체번호(productNo)"
                  }
                },
                "required": ["group_id"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "검수 성공",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": { "type": "string" },
                    "code": { "type": "string" },
                    "message": { "type": "string" },
                    "group_id": { "type": "string" },
                    "meta": { "type": "object" },
                    "result": {
                      "type": ["object", "null"],
                      "properties": {
                        "summary": { "type": "string" },
                        "normalized": { "type": "object" },
                        "issues": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "rule_id": { "type": "string" },
                              "level": {
                                "type": "string",
                                "enum": ["FATAL", "ERROR", "WARN", "INFO"]
                              },
                              "title": { "type": "string" },
                              "message": { "type": "string" },
                              "evidence": { "type": "array" },
                              "suggestion": { "type": "string" }
                            }
                          }
                        },
                        "quality": {
                          "type": "object",
                          "properties": {
                            "score": { "type": "integer", "minimum": 0, "maximum": 100 },
                            "grade": { "type": "string" }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## 핵심

- GPTs는 `group_id`만 보내고, FastAPI가 검수용 핵심 데이터를 정리해서 돌려준다.
- GPTs는 그 응답과 `검증룰1~5.json`을 비교해 최종 판정을 만든다.
- `servers.url`은 반드시 실제 Render 주소를 쓴다.
