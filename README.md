# GRE Quiz SRS

## 專案簡介

本專案是一套針對 GRE 單字與詞根的**自適應間隔重複記憶系統**（Spaced Repetition System, SRS），結合：

- **三階段學習策略**：Blind Test → AIMD 負荷控制 → SM‑2 演算法
- **AIMD Workload Control**（Additive Increase / Multiplicative Decrease）動態調整每日練習配額
- **SM‑2 Scheduling** 根據答題品質計算下一次複習間隔
- **爆練模式** 暫時解除每日配額限制
- **終端即時負荷視覺化** 進度條顯示學習負荷狀態
- **多欄位題庫支援** 詞根、單字、例句與翻譯

其核心理念為：  
> **SM‑2 負責卡片層級的最佳化，AIMD 負責每日總負荷的穩定控制**，  
> 兩者結合能同時兼顧記憶效率與心理壓力管理，避免 Burnout。

---

## 系統架構

![System Architecture](doc/system-architecture.png)

> *SM‑2（卡片間隔計算）與 AIMD（每日負荷控制）的互動示意圖。學習者表現（錯題率 / 壓力）形成迴路回饋至兩個模組。圖示為概念設計，非實驗數據。*

---

## AIMD 負荷變化趨勢（概念示意）

![Conceptual AIMD Trend](doc/aimd-trend.png)

> *Additive Increase 緩步增加每日負荷，Multiplicative Decrease 在壓力或錯誤率過高時快速下降。  
> 曲線為概念趨勢圖，非真實測量數據。*

---

## 環境與安裝

### 系統需求
- Python 3.7 以上
- Windows / macOS / Linux 皆可

### 快速安裝
```bash
git clone https://github.com/你的帳號/gre-quiz-srs.git
cd gre-quiz-srs

# 建立虛擬環境（可選）
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安裝依賴
pip install -r requirements.txt
````

---

## 題庫格式與版本說明

本專案核心以 CLI（命令列介面）版本為主，優點是輕量、易擴展，並且方便在各種環境或自動化流程中使用。

然而，我們的主要目標用戶群為非程式背景（如英文系學生、非 CS 出身者），他們對於 JSON、CSV 這類純資料格式不熟悉，也不習慣用命令列操作。

因此，本專案同時提供 **Excel 格式題庫（`voc.xlsx`）**，作為最直觀、易於理解與修改的資料載體，讓用戶能直接在熟悉的介面編輯詞彙與例句，無需學習任何程式或資料結構知識。

此外，我們在 [Release 頁面](https://github.com/ylin3-learner/GRE-Quiz-SRS/releases) 附上了 **GUI 版本**，為不熟悉命令列的用戶提供友善的使用體驗。GUI 完全兼容 `voc.xlsx` 題庫格式，並且會自動備份題庫檔，避免資料意外遺失。

請用戶在使用過程中務必**定期備份 `voc.xlsx`**，以防止因操作不慎或檔案損壞造成的資料遺失。

---

## 使用說明

啟動程式：

```bash
python quiz.py
```

進入後可選：

* `1` 詞根模式
* `2` 單字模式
* `3` 查看統計
* `4` 切換爆練模式
* `q` 退出並保存

**注意**

* 每題有時間限制，超時視為答錯
* 系統自動計算間隔並保存進度
* 進度儲存在 `voc.xlsx`，請定期備份

---

## 目錄結構

```
gre-quiz-srs/
├── quiz.py           # 主程式
├── voc.xlsx          # 題庫
├── requirements.txt  # 依賴套件
├── docs/
│   ├── system-architecture.png
│   └── aimd-trend.png
└── README.md
```

---

## requirements.txt 範例

```
pandas>=1.0.0
numpy>=1.18.0
colorama>=0.4.0
openpyxl>=3.0.0
```

## 📦 下載

[點我下載最新版本](https://github.com/ylin3-learner/GRE-Quiz-SRS/releases/latest/download/QuizApp.zip)

---

## 參考資料

* [SuperMemo SM‑2 Algorithm](https://www.supermemo.com/en/archives1990-2015/english/ol/sm2)
* Jacobson, V., *Congestion Avoidance and Control*, SIGCOMM 1988
* Cepeda, N. J., et al. (2006). *Distributed practice in verbal recall tasks: A review and quantitative synthesis.* Psychological Bulletin, 132(3), 354–380

---

## 貢獻

歡迎提出 Issue 或 PR。
如果覺得有幫助，歡迎 Star ⭐ 支持！

---

## 聯絡方式

* Email: [husenior11123@gmail.com](mailto:husenior11123@gmail.com)
* GitHub: [https://github.com/ylin3-learner](https://github.com/ylin3-learner)
