# GRE Quiz Adaptive Spaced Repetition 系統

## 專案簡介

本專案是一套針對 GRE 單字與詞根的自適應間隔重複記憶系統（Spaced Repetition System, SRS），結合三階段學習策略（Blind Test、AIMD 負荷控制、SM-2 算法），並支援「爆練模式」，讓使用者可以靈活切換練習強度，提升學習效率。

系統特色：

* **自適應三階段策略**：由完全盲測漸進到依據表現調整間隔
* **AIMD 負荷控制**：動態調整每日練習配額，避免過度疲勞
* **SM-2 演算法**：依答題品質計算下一次複習間隔
* **爆練模式切換**：用戶可選擇暫時解除每日配額限制
* **終端即時負荷視覺化**：以進度條顯示學習負荷狀態
* **多欄位題庫支援**：詞根、單字、例句及翻譯

---

## 環境與安裝

### 系統需求

* Python 3.7 以上
* Windows / macOS / Linux 皆可

### 快速安裝

1. 克隆本專案：

```bash
git clone https://github.com/你的帳號/gre-quiz-srs.git
cd gre-quiz-srs
```

2. 建議建立虛擬環境（可選）：

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. 安裝依賴套件：

```bash
pip install -r requirements.txt
```

4. 準備題庫檔 `voc.xlsx`（請放在同目錄下），格式請參考範例。

5. 執行測驗：

```bash
python quiz.py
```

---

## 使用說明

### 啟動程式後

* 輸入 `1`：提問詞根（Root）問題
* 輸入 `2`：提問單字（Vocabulary）問題
* 輸入 `3`：查看學習統計與進度
* 輸入 `4`：切換爆練模式（解除每日題量限制）
* 輸入 `q`：退出並保存進度

### 其他說明

* 每題有時間限制，超時視為答錯。
* 答題時系統會自動調整下一次複習的間隔時間。
* 程式會自動保存進度至 `voc.xlsx`，請定期備份。

---

## 目錄結構

```
gre-quiz-srs/
├── quiz.py           # 主程式
├── voc.xlsx          # GRE 詞彙題庫（Excel 格式）
├── requirements.txt  # Python 依賴套件
└── README.md         # 專案說明文件
```

---

## requirements.txt 範例

```
pandas>=1.0.0
numpy>=1.18.0
colorama>=0.4.0
openpyxl>=3.0.0
```

> 本專案使用到 `pandas`, `numpy`, `colorama`, `openpyxl`（讀寫 Excel 檔案）。

你可以用以下命令快速生成 `requirements.txt`：

```bash
pip freeze > requirements.txt
```

或是手動建立內容（推薦），以避免鎖定過多不必要版本。

---

## 參考資料與靈感

* SM-2 演算法：[SuperMemo 官方算法說明](https://www.supermemo.com/en/archives1990-2015/english/ol/sm2)
* AIMD 負荷控制理念：類比 TCP 網路流量控制
* 間隔重複記憶理論及心理學研究

---

## 貢獻與回報

歡迎針對功能提出 Issue 或 Pull Request！
若覺得本專案有幫助，歡迎在 GitHub 給個 Star ⭐️ 支持！

---

## 聯絡方式

* Email: [husenior11123@gmail.com](mailto:your.email@example.com)
* GitHub: [https://github.com/ylin3-learner](https://github.com/ylin3-learner
)



