# 玻璃 Ag⁺/Na⁺ 離子交換 profile

Profile ID：`glass_ag_na_ion_exchange`

這個 profile 只處理以熔鹽進行的玻璃 Ag⁺/Na⁺ 離子交換。學長基準成分固定為 **75 mol% SiO₂–25 mol% Na₂O 二元玻璃**；不能把「含 25 mol% Na₂O 的多成分玻璃」當成相同配方。

## 執行範圍

- 第一次建立文獻庫：`mode=focused`，`start_at=1900-01-01T00:00:00+08:00`。
- 後續監測：`mode=daily`，Asia/Taipei 最近 168 小時。
- Discovery sources：Crossref、OpenAlex。
- 原文核對：publisher／repository full text。題名、摘要、搜尋片段或二手引用都不能證成納入。

## 必要條件

只有同時滿足以下三項才能標記 `INCLUDE`：

1. 原文明確顯示沒有外加電場。
2. 交換浴是純 AgNO₃；AgNO₃/NaNO₃、AgNO₃/KNO₃ 或其他混鹽一律排除。
3. 原文明確列出玻璃的氧化物組成與比例。

已明確違反必要條件時標記 `EXCLUDE`，並填寫 `exclusion_reasons`。全文不可得或原文沒有交代必要條件時標記 `UNCERTAIN`，不得猜成納入或排除。

## 成分比較

每篇必須擇一並用 `comparison_note` 明列與 75/25 基準的差異：

- `EXACT_75_25_BINARY`：只有 SiO₂ 75 mol% 與 Na₂O 25 mol%。
- `BINARY_DIFFERENT_RATIO`：仍是 SiO₂–Na₂O 二元玻璃，但比例不同；列出每一成分的 mol% 差。
- `MULTICOMPONENT_COMPARABLE`：含第三種以上氧化物；逐項列出新增／減少的成分，不能只比較 Na₂O。
- `NOT_COMPARABLE`：基準、組成單位或玻璃系統無法合理對照。
- `UNCERTAIN`：原文資訊不足以判定比較層級。

## 優先排序

在已通過必要條件的研究中，依下列訊號加分：完全符合 75/25 二元基準、不同交換時間、不同溫度、濃度—深度曲線、擴散係數 D、濃度相依 D(C)、mode 數、effective depth。排序加分不會放寬必要條件。

## 每篇輸出

報告卡片固定顯示：論文名稱、來源／期刊、年份、玻璃組成、交換溫度、交換時間、熔鹽條件、優先量測、主要數值、原文頁碼、成分比較與篩選判定。排除與不確定文獻保留在完整候選池，可用「玻璃篩選」下拉選單查看。

`INCLUDE` 的 `glass_screening` 最小範例如下；所有 composition、condition 與 main value locator 都必須含原文頁碼，可再附表號或圖號：

```json
{
  "decision": "INCLUDE",
  "decision_reason": "原文確認無外加電場、純 AgNO3，且列出氧化物組成。",
  "exclusion_reasons": [],
  "external_electric_field": "ABSENT",
  "molten_salt": "PURE_AGNO3",
  "oxide_composition_explicit": "YES",
  "reference_comparison": "EXACT_75_25_BINARY",
  "comparison_note": "與學長基準相同：75 mol% SiO2、25 mol% Na2O，且無其他氧化物。",
  "glass_compositions": [
    {
      "basis": "mol%",
      "components": [
        {"oxide": "SiO2", "value": 75.0},
        {"oxide": "Na2O", "value": 25.0}
      ],
      "source_locator": "p. 4, Table 1"
    }
  ],
  "exchange_conditions": [
    {
      "temperature_c": 350.0,
      "duration": "2 h",
      "salt_condition": "pure AgNO3 (100%)",
      "source_locator": "p. 5, Experimental"
    }
  ],
  "reported_outputs": [
    "CONCENTRATION_DEPTH_PROFILE",
    "DIFFUSION_COEFFICIENT",
    "MULTIPLE_EXCHANGE_TIMES"
  ],
  "main_values": [
    {
      "metric": "D",
      "value_text": "1.2 × 10^-11 cm2/s at 350 °C",
      "source_locator": "p. 8, Table 2"
    }
  ]
}
```

頁碼以原文印刷頁碼為優先；若原文沒有印刷頁碼，使用 `PDF page N`，並保留 Table／Figure／section locator。
