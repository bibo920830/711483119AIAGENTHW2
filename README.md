# 國中數學錯題診斷與變形出題 Agent (v1.0 Baseline)

* **作者**：黃祺容（學號：711483119）
* **專案架構**：本專案針對台灣國中數學核心「代數與數列」課程，結合 **LangGraph 狀態機（State-based Decision）**、**SymPy 雙重符號驗證工具**、**三層推論容錯路由**與 **Podman 跨平台容器化部署**，建構一套具備「逐步算式等價驗證」與「變形練習題品質守門」的 AI 家教代理系統。

---

## 0.快速重現與執行（Run with Podman）

本專案已透過 `Containerfile`（基於 `python:3.11-slim`）完整封裝所有執行環境與相依套件，支援在 Windows、macOS 與 Linux 透過 Podman 一鍵重現。

#### 1. 建置容器映像檔（Build Image）
```bash
git clone [https://github.com/bibo920830/711483119AIAGENTHW2.git](https://github.com/bibo920830/711483119AIAGENTHW2.git)
cd 711483119AIAGENTHW2
podman build -t math-tutor-agent:v1.0 -f Containerfile .
```

#### 2. 啟動執行（任選以下一種模式）
模式 A：零外部依賴直接執行
無需設定任何 API Key 或本機模型，系統將自動啟動離線 Deterministic Fallback 題庫並執行 SymPy 數學驗證：
```
podman run --rm math-tutor-agent:v1.0
```
模式 B：掛載環境變數執行（啟用地端 Ollama 或雲端 LLM）
複製 .env.example 為 .env 並依需求填入參數後執行：
```
cp .env.example .env
podman run --rm --env-file .env math-tutor-agent:v1.0
```


---

## 專案目錄結構

```text
711483119AIAGENTHW2/
├── Containerfile          # Podman/Docker 容器建置檔 (python:3.11-slim)
├── requirements.txt       # Python 相依套件清單 (LangGraph, SymPy, LangChain 等)
├── .env.example           # 環境變數設定範本（不含真實金鑰）
├── .gitignore             # 排除本機 .env 與快取檔案
├── README.md              # 專案說明、工具定義、執行追蹤與失敗情境分析
└── src/
    ├── agent.py           # LangGraph 狀態機與三層推論路由主程式
    └── tools.py           # SymPy 符號運算與數學驗算工具
```


---

## 1. 系統概述與教學設計


### 課綱知識圖譜（共 14 個螺旋遞進節點）
系統於 src/state.py 定義 CURRICULUM_GRAPH，完整保留章節先後順序與先備知識包含鏈（Prerequisites），當學生在某單元出錯時可精準溯源其先備概念盲點：
* **第一冊**：`1. 整數的運算` $\rightarrow$ `2. 分數的運算` $\rightarrow$ `3. 一元一次方程式`
* **第二冊**：`4. 二元一次聯立方程式`、`5. 二元一次方程式的圖形`、`6. 比與比例式`、`7. 一元一次不等式`
* **第三冊**：`10-1. 乘法公式` $\rightarrow$ `10-2. 多項式`、`11-1. 平方根與根式運算` $\rightarrow$ `11-2. 畢氏定理`、`12-1. 因式分解` $\rightarrow$ `12-2. 一元二次方程式`
* **第四冊**：`13. 數列與級數`




---

## 2.系統架構與選型說明

### 1. 架構選型理由（為何採用 State-based Workflow 而非 ReAct）
本專案採用 **LangGraph 狀態機（State-based Decision）** 而非自由循環的 ReAct 架構。原因在於國中數學錯誤診斷與變形出題對「數值與代數正確性」具有零容錯要求；透過顯式的狀態節點與條件邊（Conditional Edges），可強制所有 LLM 生成的題目必須經過 SymPy 確定性工具驗證通過後才能輸出，避免 ReAct 迴圈產生無窮重試或幻覺跳脫。

```text
[User Input] ──> [Diagnosis Node] ──> [Generator Node] ──> [Verification Node] ──> [END]
                        │                                           │
                        ▼                                           ▼
         Tool 1: sympy_step_verifier          Tool 2: sympy_problem_validator
```

### 2. 三層推論容錯路由（Multi-Layer Fallback Routing）
為確保 Agent 在不同測試環境與網路條件下皆能穩定運作不崩潰，系統依序採用以下優先級路由：
1. **第一順位（地端推論）**：連線至本機 **Ollama**（預設 `qwen3.5:4b`，容器內透過 `http://host.containers.internal:11434` 存取），免金鑰且支援完全離線生成。
2. **第二順位（雲端備援）**：若未啟動地端 Ollama 且 `.env` 設有 `GEMINI_API_KEY`（或 OpenAI / Anthropic Key），自動切換至對應雲端大模型。
3. **第三順位（離線保底）**：若無任何外部模型可用，自動降級為 **Deterministic Fallback** 內建規則庫，確保核心診斷與出題流程 100% 暢通。

---

## 3. Tool 定義（SymPy 雙重符號驗證工具）

### Tool 1：`sympy_step_verifier`（逐步算式等價性驗證器）
* **Tool 名稱**：`sympy_step_verifier`（位於 `src/tools.py`）
* **目的**：將學生的每一步解題推導轉為 SymPy 符號物件（支援純代數式、等式、聯立方程組與不等式），精準定位第一個破壞代數等價性的錯誤步驟，並對應 `CURRICULUM_GRAPH` 溯源先備單元。
* **輸入（Input）**：
  * `steps` (`list[str]`)：學生的逐步推導算式清單（例如 `["2(x - 3) = 4", "2x - 3 = 4", "x = 3.5"]`）。
  * `topic_id` (`str`)：所屬課綱單元代碼。
* **輸出（Output）**：
  * `dict` 結構，包含 `first_error_step` (`int`，首個出錯步驟索引)、`is_equivalent` (`bool`，是否全部等價) 與 `prerequisite_diagnosis` (`str`，先備知識盲點說明)。
* **Error Handling（錯誤處理）**：
  * 捕捉 `SympifyError` 與語法解析例外：若學生輸入包含非標準全形符號、未閉合括號或無法解析的算式片段，安全攔截例外並回傳格式提示訊息，不中斷整體診斷流程。

### Tool 2：`sympy_problem_validator`（變形題目課綱約束與正解守門員）
* **Tool 名稱**：`sympy_problem_validator`（位於 `src/tools.py`）
* **目的**：強制驗證 LLM 生成的變形練習題是否符合台灣國中課綱約束（如聯立方程唯一整數解、畢氏三元數正整數邊長、因式分解不可約乘積、一元二次實數根），並驗算標準答案正確性以消除數學幻覺。
* **輸入（Input）**：
  * `problem_data` (`dict`)：包含生成題目算式、預期解答與目標單元約束條件。
* **輸出（Output）**：
  * `dict` 結構，包含 `is_valid` (`bool`，是否通過課綱與正解驗證)、`verified_answer` (`str`，SymPy 算出的精確解) 與 `reject_reason` (`str`，退件原因)。
* **Error Handling（錯誤處理）**：
  * 若題目出現無解、無限多解、不符合國中課綱數域限制（如非預期的無理數解或負邊長），或答案與 SymPy 驗算不符，回傳 `is_valid: False` 並觸發 LangGraph 退回重生成或降級至安全題庫。


---
## 4. Agent 執行追蹤（Execution Trace）

以下為實際執行 Podman 容器（`python -m src.main`）時的完整狀態與雙工具呼叫追蹤流程：

```text
[1. User Input] 學生錯題輸入：「一元一次方程式 2(x - 3) = 4，推導步驟：2(x - 3) = 4 -> 2x - 3 = 4 -> x = 3.5」
       ↓
[2. Agent Decision (Diagnosis Node)] 決定呼叫 Tool 1 檢查算式每一步的代數等價性
       ↓
[3. Tool Call 1] 呼叫 sympy_step_verifier(steps=["2(x - 3) = 4", "2x - 3 = 4", "x = 3.5"], topic_id="3")
       ↓
[4. Observation 1] 回傳：{'first_error_step': 1, 'is_equivalent': False, 'prerequisite_diagnosis': '去括號分配律漏乘常數項，建議回溯複習先備單元「1. 整數的運算」'}
       ↓
[5. Agent Decision (Generator & Verification Node)] 針對「去括號分配律」生成同概念變形題 3(x - 2) = 9，並決定呼叫 Tool 2 進行課綱與正解守門驗證
       ↓
[6. Tool Call 2] 呼叫 sympy_problem_validator(problem_data={"equation": "3*(x - 2) = 9", "expected_answer": "5", "topic_id": "3"})
       ↓
[7. Observation 2] 回傳：{'is_valid': True, 'verified_answer': '5', 'reject_reason': None}
       ↓
[8. Agent Decision & Final Output] 兩道驗證閘門皆通過，組裝並輸出錯因解析、先備概念提醒、變形練習題 3(x - 2) = 9 與分步詳解
```
---

## 5.失敗情境分析（Failure Cases）

### 情境一：LLM 數學幻覺導致生成無解或答案錯誤的練習題
* **失敗狀況**：在生成變形題階段，語言模型產出方程式 `2*(x + 1) = 2*x + 5`，卻宣稱標準答案為 `x = 3`（實際上該方程式無解）。
* **原因**：大型語言模型本質為機率序列預測，缺乏嚴格的代數符號推演能力，容易在移項或係數化簡時發生算術幻覺。
* **解決方法**：在輸出前強制介入 `verify_math_problem`（SymPy 工具）進行代數求解。當工具回傳 `is_valid: False` 時，LangGraph 狀態機會攔截該錯誤題目並觸發重試機制；若連續重試仍未通過，則自動切換至經過預先驗證的 Deterministic 題庫確保輸出正確。

### 情境二：測試環境無 API Key 或網路隔離導致推論連線失敗
* **失敗狀況**：評測環境（如跨平台 Podman 離線測試機）未設定 `GEMINI_API_KEY`，且本機未啟動 Ollama 服務，導致容器內呼叫外部 LLM API 時發生 `ConnectionError` 或認證失敗。
* **原因**：容器化部署跨不同作業系統與網路環境時，外部推論端點的可用性與金鑰配置無法保證一致。
* **解決方法**：在 `src/agent.py` 實作三層推論容錯路由（地端 Ollama 優先 → 雲端 API 備援 → 離線 Deterministic Fallback）。當偵測到地端與雲端端點皆不可用時，系統自動捕捉連線例外並無縫降級為離線規則引擎，保證整體 Agent 工作流與 SymPy 驗證仍能 100% 正常執行完畢。



---


