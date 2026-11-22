# 國中數學錯題診斷與變形出題 Agent (v1.0 Baseline)

* **作者**：黃祺容（學號：`[請填入你的學號]`）
* **專案架構**：LangGraph 單向狀態機 + SymPy 確定性代數驗證引擎 + Podman 容器化部署

---

## 1. 系統概述與教學設計

本系統針對台灣國中數學第 1～4 冊核心代數與數列課程，建構一套具備「逐步算式等價驗證」與「變形練習題品質守門」的 AI 家教代理系統。

### 課綱知識圖譜（共 14 個螺旋遞進節點）
系統於 `src/state.py` 定義 `CURRICULUM_GRAPH`，完整保留章節先後順序與先備知識包含鏈（`prerequisites`）：
* **第一冊**：`1. 整數的運算` $\rightarrow$ `2. 分數的運算` $\rightarrow$ `3. 一元一次方程式`
* **第二冊**：`4. 二元一次聯立方程式`、`5. 二元一次方程式的圖形`、`6. 比與比例式`、`7. 一元一次不等式`
* **第三冊**：`10-1. 乘法公式` $\rightarrow$ `10-2. 多項式`、`11-1. 平方根與根式運算` $\rightarrow$ `11-2. 畢氏定理`、`12-1. 因式分解` $\rightarrow$ `12-2. 一元二次方程式`
* **第四冊**：`13. 數列與級數`

---

## 2. 系統架構與外部工具設計
sympy_step_verifier (Tool 1)：將學生每一步推導轉為 SymPy 符號物件（支援純代數式、等式、聯立方程組與不等式），精準定位第一個破壞代數等價性的步驟，並溯源先備單元。

sympy_problem_validator (Tool 2)：強制驗證變形題目是否符合國中課綱約束（如聯立方程唯一整數解、畢氏三元數正整數邊長、因式分解不可約乘積、一元二次實數根）。

多模型與無金鑰容錯 (Deterministic Fallback)：自動偵測 GEMINI_API_KEY、OPENAI_API_KEY 或 ANTHROPIC_API_KEY；若環境未提供任何金鑰，則自動啟用內建 14 單元標準教學模板引擎確保零當機運作。
### LangGraph 狀態機工作流 (`src/agent.py`)
```text
[User Input] ──> [Diagnosis Node] ──> [Generator Node] ──> [Verification Node] ──> [END]
                        │                                           │
                        ▼                                           ▼
         Tool 1: sympy_step_verifier          Tool 2:sympy_problem_validator
```

sympy_step_verifier (Tool 1)：將學生每一步推導轉為 SymPy 符號物件（支援純代數式、等式、聯立方程組與不等式），精準定位第一個破壞代數等價性的步驟，並溯源先備單元。

sympy_problem_validator (Tool 2)：強制驗證變形題目是否符合國中課綱約束（如聯立方程唯一整數解、畢氏三元數正整數邊長、因式分解不可約乘積、一元二次實數根）。

多模型與無金鑰容錯 (Deterministic Fallback)：自動偵測 GEMINI_API_KEY、OPENAI_API_KEY 或 ANTHROPIC_API_KEY；若環境未提供任何金鑰，則自動啟用內建 14 單元標準教學模板引擎確保零當機運作。

---
## 3. 本機執行方式 (Conda / Python)
1. 安裝相依套件
pip install -r requirements.txt

2. (選用) 複製並設定 API Key
cp .env.example .env

3. 執行內建 4 大測試案例與完整 Execution Trace
python -m src.main

---
## 4. Podman 容器化建置與執行

1. 建置容器映像檔
podman build -t math-tutor-agent:v1.0 -f Containerfile .

2. 執行容器（無 API Key 模式，自動啟用 Deterministic Fallback）
podman run --rm math-tutor-agent:v1.0

3. (選用) 帶入 .env 金鑰執行真實 LLM 推理模式
podman run --rm --env-file .env math-tutor-agent:v1.0