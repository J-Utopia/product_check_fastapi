# GPTs Action 스키마

아래 스키마는 `https://product-check-fastapi.onrender.com` 기준이다.

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Modetour Itinerary Inspection API",
    "version": "2.0.0",
    "description": "모두투어 단체번호를 입력받아 일정표 검수용 데이터를 반환하는 API"
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
        "summary": "단체번호로 일정표 검수 데이터를 조회한다",
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
            "description": "검수 데이터 조회 성공",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "code": {
                      "type": "string"
                    },
                    "message": {
                      "type": "string"
                    },
                    "group_id": {
                      "type": "string"
                    },
                    "meta": {
                      "type": "object"
                    },
                    "result": {
                      "type": ["object", "null"],
                      "properties": {
                        "summary": {
                          "type": "string"
                        },
                        "normalized": {
                          "type": "object"
                        },
                        "issues": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "rule_id": {
                                "type": "string"
                              },
                              "level": {
                                "type": "string",
                                "enum": ["FATAL", "ERROR", "WARN", "INFO"]
                              },
                              "title": {
                                "type": "string"
                              },
                              "message": {
                                "type": "string"
                              },
                              "evidence": {
                                "type": "array"
                              },
                              "suggestion": {
                                "type": "string"
                              }
                            }
                          }
                        },
                        "quality": {
                          "type": "object",
                          "properties": {
                            "score": {
                              "type": "integer",
                              "minimum": 0,
                              "maximum": 100
                            },
                            "grade": {
                              "type": "string"
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
}
```

## 사용 메모

- GPTs는 `group_id`만 보내고, FastAPI가 검수용 정규화 데이터를 반환한다.
- GPTs는 `result.issues`를 그대로 복사하지 말고, `normalized`와 `summary`를 함께 보고 근거를 재정리한다.
- `quality.score`는 참고값으로 사용하되, 최종 설명은 반드시 근거 중심으로 작성한다.
- `servers.url`은 실제 Render 배포 주소와 일치해야 한다.
