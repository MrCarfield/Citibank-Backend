# Market 接口文档汇总

本文档汇总了原油市场分析系统的四个核心数据接口。

---

## 接口列表

| 接口                                          | 功能         | 更新频率        |
| ------------------------------------------- | ---------- | ----------- |
| [`/v1/market/snapshot`](#1-market-snapshot) | 获取市场实时快照数据 | 实时（缓存 5 分钟） |
| [`/v1/market/drivers`](#2-market-drivers)   | 获取市场驱动因素分析 | 每日 1:00 AM  |
| [`/v1/market/regime`](#3-market-regime)     | 获取市场状态机制   | 每日 1:10 AM  |
| [`/v1/market/events`](#4-market-events)     | 获取近期市场事件   | 每日 1:20 AM  |

---

## 1. Market Snapshot

### 接口说明

获取指定原油市场（WTI 或 Brent）的实时快照数据，包括最新价格、日变化、波动率和期限结构等信息。

**用途**：Market & Factor Radar 页面展示，包含价格卡片和走势迷你图。

### 请求示例

```bash
GET /v1/market/snapshot?market=WTI
GET /v1/market/snapshot?market=Brent&asOf=2026-02-15T00:00:00Z
```

### 请求参数

| 参数       | 类型               | 必填  | 说明                   |
| -------- | ---------------- | --- | -------------------- |
| `market` | string           | ✅   | 市场类型：`WTI` 或 `Brent` |
| `asOf`   | string(datetime) | ❌   | ISO-8601 时间戳，查询历史数据  |

### 成功响应 (200)

| 字段                                | 类型       | 说明                          |
| --------------------------------- | -------- | --------------------------- |
| `market`                          | string   | 市场类型                        |
| `asOf`                            | datetime | 数据时间点                       |
| `lastPrice`                       | float    | 最新价格（USD/桶）                 |
| `change1d`                        | float    | 日绝对变化                       |
| `pctChange1d`                     | float    | 日百分比变化 (%)                  |
| `volatility20d`                   | float    | 20日年化波动率                    |
| `termStructure`                   | object   | 期限结构                        |
| `termStructure.state`             | string   | BACKWARDATION/CONTANGO/FLAT |
| `termStructure.spreadFrontSecond` | float    | 近远月价差                       |
| `history`                         | array    | 最近30天价格走势                   |

```json
{
  "market": "WTI",
  "asOf": "2026-02-15T10:00:00Z",
  "lastPrice": 75.50,
  "change1d": 2.30,
  "pctChange1d": 3.15,
  "volatility20d": 0.25,
  "termStructure": {
    "state": "BACKWARDATION",
    "spreadFrontSecond": 1.50
  },
  "history": [
    {"ts": "2026-01-15T00:00:00Z", "value": 72.30},
    {"ts": "2026-01-16T00:00:00Z", "value": 73.10}
  ]
}
```

### 错误响应

| 状态码     | 说明        | 示例                                |
| ------- | --------- | --------------------------------- |
| **400** | 请求参数错误    | `{"detail": "不支持的市场类型: XXX"}`     |
| **401** | 未授权（需要登录） | `{"detail": "Not authenticated"}` |
| **503** | 服务内部错误    | `{"detail": "获取市场数据失败: ..."}`     |

---

## 2. Market Drivers

### 接口说明

获取影响原油价格的各类驱动因素及其贡献度分析，包括供应、需求、宏观金融、外汇和事件等因素。

**用途**：Factor Radar 页面展示，显示 Top 3 驱动因素和完整列表。

### 请求示例

```bash
GET /v1/market/drivers?market=WTI
GET /v1/market/drivers?market=Brent&asOf=2026-02-15T00:00:00Z
```

### 请求参数

| 参数       | 类型       | 必填  | 说明                   |
| -------- | -------- | --- | -------------------- |
| `market` | string   | ✅   | 市场类型：`WTI` 或 `Brent` |
| `asOf`   | string(datetime) | ❌   | ISO-8601 时间戳，查询历史分析  |

### 成功响应 (200)

| 字段           | 类型       | 说明            |
| ------------ | -------- | ------------- |
| `market`     | string   | 市场类型          |
| `asOf`       | datetime | 数据时间点         |
| `topDrivers` | array    | 影响力最大的前3个驱动因素 |
| `allDrivers` | array    | 全部识别到的驱动因素    |
| `summary`    | string   | 市场整体驱动逻辑总结    |

```json
{
  "market": "WTI",
  "asOf": "2026-02-15T10:00:00Z",
  "topDrivers": [
    {
      "factorId": "opec_production_cut",
      "factorName": "OPEC+减产",
      "category": "SUPPLY",
      "direction": "UP",
      "strength": 8,
      "evidence": ["OPEC+宣布延长减产至Q2"]
    }
  ],
  "allDrivers": [...],
  "summary": "当前市场主要由供应端因素驱动..."
}
```

### 驱动因素结构

| 字段           | 类型     | 说明                                            |
| ------------ | ------ | --------------------------------------------- |
| `factorId`   | string | 因素唯一标识                                        |
| `factorName` | string | 因素名称                                          |
| `category`   | string | SUPPLY/DEMAND/MACRO_FINANCIAL/FX/EVENTS/OTHER |
| `direction`  | string | UP/DOWN/NEUTRAL                               |
| `strength`   | float  | 影响力评分 (1-10)                                  |
| `evidence`   | array  | 证据列表                                          |

### 错误响应

| 状态码     | 说明     | 示例                                |
| ------- | ------ | --------------------------------- |
| **400** | 请求参数错误 | `{"detail": "不支持的市场类型: XXX"}`     |
| **401** | 未授权    | `{"detail": "Not authenticated"}` |
| **503** | 服务内部错误 | `{"detail": "获取驱动因素分析失败: ..."}`   |

---

## 3. Market Regime

### 接口说明

获取当前市场所处的状态机制（需求驱动、供应驱动、事件驱动等）及其稳定性评估。

**用途**：帮助理解市场当前的主导因素，判断市场状态是否稳定。

### 请求示例

```bash
GET /v1/market/regime?market=WTI
GET /v1/market/regime?market=Brent&asOf=2026-02-15T00:00:00Z
```

### 请求参数

| 参数       | 类型       | 必填  | 说明                   |
| -------- | -------- | --- | -------------------- |
| `market` | string   | ✅   | 市场类型：`WTI` 或 `Brent` |
| `asOf`   | string(datetime) | ❌   | ISO-8601 时间戳，查询历史分析  |

### 成功响应 (200)

| 字段               | 类型       | 说明                      |
| ---------------- | -------- | ----------------------- |
| `market`         | string   | 市场类型                    |
| `asOf`           | datetime | 数据时间点                   |
| `regime`         | string   | 当前市场状态机制类型              |
| `stability`      | string   | 稳定性等级 (HIGH/MEDIUM/LOW) |
| `confidence`     | float    | 置信度 (0-1)               |
| `recentSwitches` | array    | 近期状态转换记录                |

```json
{
  "market": "WTI",
  "asOf": "2026-02-15T10:00:00Z",
  "regime": "SUPPLY_DRIVEN",
  "stability": "MEDIUM",
  "confidence": 0.75,
  "recentSwitches": [
    {
      "from": "DEMAND_DRIVEN",
      "to": "SUPPLY_DRIVEN",
      "ts": "2026-02-10T00:00:00Z",
      "reason": "OPEC+ 减产决议导致供应端影响力上升"
    }
  ]
}
```

### 状态机制类型

| 类型                 | 说明   |
| ------------------ | ---- |
| `DEMAND_DRIVEN`    | 需求驱动 |
| `SUPPLY_DRIVEN`    | 供应驱动 |
| `EVENT_DRIVEN`     | 事件驱动 |
| `FINANCIAL_DRIVEN` | 金融驱动 |
| `MIXED`            | 混合状态 |

### 错误响应

| 状态码     | 说明     | 示例                                |
| ------- | ------ | --------------------------------- |
| **400** | 请求参数错误 | `{"detail": "不支持的市场类型: XXX"}`     |
| **401** | 未授权    | `{"detail": "Not authenticated"}` |
| **503** | 服务内部错误 | `{"detail": "获取状态机制分析失败: ..."}`   |

---

## 4. Market Events

### 接口说明

获取指定时间窗口内影响原油市场的重要事件列表，包括地缘政治、政策变化、供需事件等。

**用途**：Event Lens 页面展示，事件卡片时间线。

### 请求示例

```bash
GET /v1/market/events?market=WTI
GET /v1/market/events?market=WTI&windowDays=7
GET /v1/market/events?market=Brent&asOf=2026-02-15T00:00:00Z&windowDays=14
```

### 请求参数

| 参数           | 类型       | 必填  | 说明                   |
| ------------ | -------- | --- | -------------------- |
| `market`     | string   | ✅   | 市场类型：`WTI` 或 `Brent` |
| `asOf`       | string(datetime) | ❌   | ISO-8601 时间戳，查询历史分析  |
| `windowDays` | int      | ❌   | 回溯天数，默认7天            |

### 成功响应 (200)

| 字段           | 类型       | 说明        |
| ------------ | -------- | --------- |
| `market`     | string   | 市场类型      |
| `asOf`       | datetime | 数据时间点     |
| `windowDays` | int      | 回溯时间窗口（天） |
| `events`     | array    | 事件卡片列表    |

```json
{
  "market": "WTI",
  "asOf": "2026-02-15T10:00:00Z",
  "windowDays": 7,
  "events": [
    {
      "eventId": "evt_opec_meeting_20260210",
      "ts": "2026-02-10T00:00:00Z",
      "title": "OPEC+ 部长级会议决定延长减产至Q2",
      "type": "POLICY",
      "impact": "UP",
      "linkedFactors": ["opec_production_cut"],
      "evidence": ["路透社报道", "OPEC官方公告"]
    }
  ]
}
```

### 事件结构

| 字段              | 类型       | 说明                                           |
| --------------- | -------- | -------------------------------------------- |
| `eventId`       | string   | 事件唯一标识                                       |
| `ts`            | datetime | 事件发生时间                                       |
| `title`         | string   | 事件标题                                         |
| `type`          | string   | GEOPOLITICS/POLICY/SUPPLY/DEMAND/MACRO/OTHER |
| `impact`        | string   | UP/DOWN/UNCERTAIN                            |
| `linkedFactors` | array    | 关联的驱动因素ID                                    |
| `evidence`      | array    | 证据来源列表                                       |

### 错误响应

| 状态码     | 说明     | 示例                                |
| ------- | ------ | --------------------------------- |
| **400** | 请求参数错误 | `{"detail": "不支持的市场类型: XXX"}`     |
| **401** | 未授权    | `{"detail": "Not authenticated"}` |
| **503** | 服务内部错误 | `{"detail": "获取市场事件分析失败: ..."}`   |

---

## 通用说明

### 认证方式

所有 Market 接口都需要 Bearer Token 认证：

```bash
curl -H "Authorization: Bearer <your_token>" \
     "http://localhost:8000/v1/market/snapshot?market=WTI"
```

### 日期分界时间

由于原油市场主要在欧美交易时段活跃，系统将每日 **01:00 AM (北京时间)** 设为新一天的分界线：

- 请求时间 < 01:00 → 返回前一天的分析数据
- 请求时间 ≥ 01:00 → 返回当天的分析数据

### 缓存策略

| 数据类型                  | Redis TTL    | 说明         |
| --------------------- | ------------ | ---------- |
| Snapshot              | 300s (5分钟)   | 价格数据实时性要求高 |
| Drivers/Regime/Events | 1800s (30分钟) | 分析结果相对稳定   |

### 数据流程

```
用户请求
    │
    ▼
┌─────────────────────┐
│   Redis 缓存查询     │  ← 优先返回（<50ms）
└─────────────────────┘
    │ 未命中
    ▼
┌─────────────────────┐
│   MySQL 数据库查询   │  ← 持久化数据
└─────────────────────┘
    │ 无数据
    ▼
┌─────────────────────┐
│   实时生成分析       │  ← Bing搜索 + LLM分析
│   (Drivers/Regime/  │     耗时 20-60s
│    Events)          │
└─────────────────────┘
    │
    ▼
  返回响应
```

## 相关文档

- [Market Snapshot 详细文档](./market_snapshot.md)
- [Market Drivers 详细文档](./market_drivers.md)
- [Market Regime 详细文档](./market_regime.md)
- [Market Events 详细文档](./market_events.md)
