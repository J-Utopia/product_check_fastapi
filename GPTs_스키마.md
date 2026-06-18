# GPTs 스키마

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Modetour Itinerary Inspection API",
    "version": "2.1.0",
    "description": "단체번호 입력 시 현재 기준 모두투어 일정표 API를 호출해 정규화와 검수를 수행한다. 단체번호가 있으면 반드시 이 API를 호출해야 한다."
  },
  "servers": [
    {
      "url": "https://your-fastapi-host.example.com"
    }
  ],
  "paths": {
    "/run-itinerary": {
      "post": {
        "operationId": "runItinerary",
        "summary": "단체번호로 일정표 검수를 실행한다.",
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
                    "description": "사용자가 입력한 단체번호(productNo)"
                  }
                },
                "required": ["group_id"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "검수 실행 결과",
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
                        "normalized": {
                          "type": "object",
                          "description": "GetPackageInfo, GetScheduleList, GetProductDetailInfo, GetHotelList, GetFlightRemarkList, GetProductKeyPointInfo, GetPackageCouponList를 통합한 정규화 결과"
                        },
                        "issues": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "rule_id": { "type": "string" },
                              "level": { "type": "string", "enum": ["FATAL", "ERROR", "WARN", "INFO"] },
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
