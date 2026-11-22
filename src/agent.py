import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from src.state import AgentState, CURRICULUM_GRAPH
from src.tools import sympy_step_verifier, sympy_problem_validator

load_dotenv()

# 涵蓋 14 個國中代數單元的標準化變形練習題庫（供無 API Key 時的 Deterministic Fallback 使用）
FALLBACK_PROBLEM_TEMPLATES: Dict[str, Dict[str, str]] = {
    "unit_01_integers": {
        "new_problem": "(-12) + 5 * (-3) - (-7)",
        "solution_steps": "1. 先乘除後加減：5 * (-3) = -15\n2. 負負得正：- (-7) = +7\n3. 合併計算：-12 - 15 + 7 = -20",
        "proposed_answer": "-20",
    },
    "unit_02_fractions": {
        "new_problem": "3/4 - 5/6 + 1/2",
        "solution_steps": "1. 找分母 4, 6, 2 的最小公倍數 12\n2. 通分：9/12 - 10/12 + 6/12 = 5/12",
        "proposed_answer": "5/12",
    },
    "unit_03_linear_eq_1var": {
        "new_problem": "3*(x - 2) + 5 = 2*x + 7",
        "solution_steps": "1. 去括號：3x - 6 + 5 = 2x + 7\n2. 化簡：3x - 1 = 2x + 7\n3. 移項得 x = 8",
        "proposed_answer": "8",
    },
    "unit_04_linear_system": {
        "new_problem": "2*x + y = 11; x - y = 1",
        "solution_steps": "1. 兩式相加消去 y：3x = 12 => x = 4\n2. 代入第二式：4 - y = 1 => y = 3",
        "proposed_answer": "x=4, y=3",
    },
    "unit_05_linear_graph": {
        "new_problem": "2*x - 3*y = 6; x = 0",
        "solution_steps": "1. 求直線與 y 軸交點，令 x = 0\n2. 代入得 -3y = 6 => y = -2",
        "proposed_answer": "x=0, y=-2",
    },
    "unit_06_ratio": {
        "new_problem": "(2*x + 1)/5 = (x + 4)/3",
        "solution_steps": "1. 交叉相乘（內項積等於外項積）：3(2x + 1) = 5(x + 4)\n2. 展開：6x + 3 = 5x + 20 => x = 17",
        "proposed_answer": "17",
    },
    "unit_07_linear_inequality": {
        "new_problem": "4*x - 7 <= 2*x + 5",
        "solution_steps": "1. 移項：4x - 2x <= 5 + 7\n2. 化簡：2x <= 12 => x <= 6",
        "proposed_answer": "x <= 6",
    },
    "unit_10_1_multiplication_formula": {
        "new_problem": "(2*x - 3)**2",
        "solution_steps": "1. 套用差的平方公式 (a - b)^2 = a^2 - 2ab + b^2\n2. 展開：(2x)^2 - 2*(2x)*3 + 3^2 = 4x^2 - 12x + 9",
        "proposed_answer": "4*x**2 - 12*x + 9",
    },
    "unit_10_2_polynomial": {
        "new_problem": "(3*x**2 - 4*x + 5) - (x**2 - 6*x + 2)",
        "solution_steps": "1. 去括號注意變號：3x^2 - 4x + 5 - x^2 + 6x - 2\n2. 同類項合併：2x^2 + 2x + 3",
        "proposed_answer": "2*x**2 + 2*x + 3",
    },
    "unit_11_1_square_root": {
        "new_problem": "sqrt(18) + sqrt(8) - sqrt(2)",
        "solution_steps": "1. 化為最簡根式：3*sqrt(2) + 2*sqrt(2) - sqrt(2)\n2. 同類方根合併：4*sqrt(2)",
        "proposed_answer": "4*sqrt(2)",
    },
    "unit_11_2_pythagorean": {
        "new_problem": "5**2 + 12**2 = c**2",
        "solution_steps": "1. 依畢氏定理 a^2 + b^2 = c^2\n2. c^2 = 25 + 144 = 169 => 正整數斜邊 c = 13",
        "proposed_answer": "13",
    },
    "unit_12_1_factorization": {
        "new_problem": "x**2 - 5*x + 6",
        "solution_steps": "1. 使用十字交乘法尋找兩數相乘為 +6、相加為 -5\n2. 分解為 (x - 2)(x - 3)",
        "proposed_answer": "(x - 2)*(x - 3)",
    },
    "unit_12_2_quadratic_eq": {
        "new_problem": "x**2 - 7*x + 12 = 0",
        "solution_steps": "1. 因式分解：(x - 3)(x - 4) = 0\n2. 得兩實根 x = 3 或 x = 4",
        "proposed_answer": "[3, 4]",
    },
    "unit_13_sequences_series": {
        "new_problem": "3 + (8 - 1) * 4",
        "solution_steps": "1. 等差數列第 n 項公式 a_n = a_1 + (n - 1)d\n2. 首項 3、公差 4 的第 8 項為 3 + 7*4 = 31",
        "proposed_answer": "31",
    },
}


def _get_llm_client():
    """依序偵測環境變數中的可用 LLM API Key，皆無時回傳 None 啟動 Deterministic Fallback"""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ("Gemini (gemini-2.5-flash)", ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2))

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        from langchain_openai import ChatOpenAI
        return ("OpenAI (gpt-4o-mini)", ChatOpenAI(model="gpt-4o-mini", temperature=0.2))

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        from langchain_anthropic import ChatAnthropic
        return ("Anthropic (claude-3-5-haiku-latest)", ChatAnthropic(model="claude-3-5-haiku-latest", temperature=0.2))

    return (None, None)


def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """從 LLM 回覆文字中安全擷取 JSON 物件"""
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None


# ==============================================================================
# Node 1: 錯題診斷節點 (Diagnostic Node)
# ==============================================================================
def diagnosis_node(state: AgentState) -> Dict[str, Any]:
    traces = list(state.get("trace_logs", []))
    topic = state["topic"]
    problem_expr = state["problem_expr"]
    student_steps = state["student_steps"]

    traces.append(f"[1. User Input] 單元={topic} | 原題={problem_expr} | 學生步驟={student_steps}")

    # 課綱邊界守門
    if topic not in CURRICULUM_GRAPH:
        msg = f"單元 '{topic}' 超出支援的 14 個國中數學代數課綱範圍，系統拒絕處理。"
        traces.append(f"[2. Decision -> Guardrail] {msg}")
        return {
            "status": "OUT_OF_SCOPE",
            "diagnosis_explanation": msg,
            "trace_logs": traces,
        }

    topic_meta = CURRICULUM_GRAPH[topic]
    traces.append(f"[2. Decision] 呼叫外部確定性工具 `sympy_step_verifier` 驗證逐步代數等價性 ({topic_meta['book']} {topic_meta['name']})")

    # 強制呼叫 Tool 1
    verify_res = sympy_step_verifier(topic, problem_expr, student_steps)
    traces.append(f"[3. Observation (Tool 1)] {json.dumps(verify_res, ensure_ascii=False)}")

    # 組合錯題診斷解析（優先使用 LLM，無金鑰時自動切換為教學規則診斷）
    provider_name, llm = _get_llm_client()
    if verify_res.get("error_code"):
        tag = verify_res["error_code"]
        explanation = verify_res["expected_hint"]
    elif verify_res["is_all_correct"]:
        tag = "NO_ERROR_VERIFIED"
        explanation = f"你的每一步推導在代數上皆完全等價正確！已掌握「{topic_meta['name']}」核心運算。"
    else:
        err_step = verify_res["first_error_step"]
        wrong_expr = verify_res["wrong_step_content"]
        prereqs = " -> ".join(verify_res.get("prerequisite_chain", [])) or "基礎四則運算"

        if llm is not None:
            prompt = (
                f"你是台灣國中數學專業家教。目前單元為「{topic_meta['book']} {topic_meta['name']}」，"
                f"先備知識鏈為：{prereqs}。\n"
                f"原題：{problem_expr}\n學生算式：{student_steps}\n"
                f"SymPy 工具已精準抓出第 {err_step} 步「{wrong_expr}」開始不等價（{verify_res['expected_hint']}）。\n"
                f"請用繁體中文回覆嚴格 JSON 格式（不要有多餘文字）："
                f'{{"misconception_tag": "簡短迷思概念英文代碼", "diagnosis_explanation": "兩句話以內的白話錯誤原因與先備觀念提醒"}}'
            )
            try:
                resp = llm.invoke(prompt)
                parsed = _extract_json_block(resp.content)
                if parsed and "diagnosis_explanation" in parsed:
                    tag = parsed.get("misconception_tag", "ALGEBRAIC_STEP_ERROR")
                    explanation = f"[{provider_name}] {parsed['diagnosis_explanation']}"
                else:
                    raise ValueError("LLM 未回傳預期 JSON")
            except Exception:
                tag = "ALGEBRAIC_EQUIVALENCE_BREAK"
                explanation = (
                    f"第 {err_step} 步（{wrong_expr}）出現代數不等價錯誤（常見於符號變號、去括號或公式展開遺漏）。"
                    f"建議回頭檢查先備單元：【{prereqs}】，{verify_res['expected_hint']}。"
                )
        else:
            tag = "ALGEBRAIC_EQUIVALENCE_BREAK"
            explanation = (
                f"[Deterministic Fallback] 第 {err_step} 步（{wrong_expr}）出現代數不等價錯誤（常見於負號分配、移項變號或公式展開遺漏）。"
                f"依據課綱先備知識鏈【{prereqs}】，{verify_res['expected_hint']}。"
            )

    return {
        "step_verification": verify_res,
        "misconception_tag": tag,
        "diagnosis_explanation": explanation,
        "trace_logs": traces,
    }


# ==============================================================================
# Node 2: 變形出題節點 (Generator Node - v1.0 單次生成，無重試迴圈)
# ==============================================================================
def generator_node(state: AgentState) -> Dict[str, Any]:
    traces = list(state.get("trace_logs", []))
    if state.get("status") == "OUT_OF_SCOPE":
        return {"trace_logs": traces}

    topic = state["topic"]
    topic_meta = CURRICULUM_GRAPH[topic]
    provider_name, llm = _get_llm_client()

    if llm is not None:
        traces.append(f"[4. Decision] 使用 {provider_name} 針對「{topic_meta['name']}」生成一道同結構變形練習題（v1.0 單次生成）")
        prompt = (
            f"你是台灣國中數學命題老師。請針對「{topic_meta['book']} {topic_meta['name']}」設計一道新的變形練習題，"
            f"原題為：{state['problem_expr']}。\n"
            f"命題規範：\n"
            f"1. 題目必須是純 SymPy 可解析算式（變數用 x, y 或 c；乘方用 **；聯立方程用分號 ; 隔開；畢氏定理請寫成 a**2 + b**2 = c**2 形式）。\n"
            f"2. 答案必須符合國中課綱（整數解、有理數解或實數根，不得出現虛根）。\n"
            f"請嚴格回傳以下 JSON 格式（不要有其他文字）：\n"
            f'{{"new_problem": "新題目算式", "solution_steps": "完整解題步驟", "proposed_answer": "最終標準答案"}}'
        )
        try:
            resp = llm.invoke(prompt)
            parsed = _extract_json_block(resp.content)
            if parsed and all(k in parsed for k in ("new_problem", "solution_steps", "proposed_answer")):
                gen_prob = {
                    "new_problem": str(parsed["new_problem"]),
                    "solution_steps": str(parsed["solution_steps"]),
                    "proposed_answer": str(parsed["proposed_answer"]),
                }
                traces.append(f"[5. Observation (Generator)] 生成題目={gen_prob['new_problem']} | 擬定答案={gen_prob['proposed_answer']}")
                return {"generated_problem": gen_prob, "trace_logs": traces}
        except Exception as exc:
            traces.append(f"[5. Warning] LLM 生成解析異常 ({exc})，切換至單元標準變形模板")

    # Deterministic Fallback 模板
    gen_prob = FALLBACK_PROBLEM_TEMPLATES[topic]
    traces.append(f"[4. Decision] 無外部 API Key，啟用 Deterministic Fallback 變形題庫（單元：{topic_meta['name']}）")
    traces.append(f"[5. Observation (Generator)] 載入題目={gen_prob['new_problem']} | 擬定答案={gen_prob['proposed_answer']}")
    return {"generated_problem": gen_prob, "trace_logs": traces}


# ==============================================================================
# Node 3: 品質驗證節點 (Verification Node - Tool 2 強制把關)
# ==============================================================================
def verification_node(state: AgentState) -> Dict[str, Any]:
    traces = list(state.get("trace_logs", []))
    if state.get("status") == "OUT_OF_SCOPE":
        return {"trace_logs": traces}

    topic = state["topic"]
    gen_prob = state.get("generated_problem") or {}
    new_q = gen_prob.get("new_problem", "")
    ans = gen_prob.get("proposed_answer", "")

    traces.append(f"[6. Decision] 呼叫外部確定性工具 `sympy_problem_validator` 驗證變形題合法性與課綱難度約束")
    val_res = sympy_problem_validator(topic, new_q, ans)
    traces.append(f"[7. Observation (Tool 2)] {json.dumps(val_res, ensure_ascii=False)}")

    final_status = "SUCCESS" if val_res.get("is_valid") else "VALIDATION_FAILED"
    traces.append(f"[8. Final Output] 任務結束狀態={final_status}")

    return {
        "problem_validation": val_res,
        "status": final_status,
        "trace_logs": traces,
    }


def build_math_tutor_graph():
    """建構 v1.0 單向直線 LangGraph 狀態機 (Diagnosis -> Generator -> Verification)"""
    workflow = StateGraph(AgentState)
    workflow.add_node("diagnosis", diagnosis_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("verification", verification_node)

    workflow.set_entry_point("diagnosis")
    workflow.add_edge("diagnosis", "generator")
    workflow.add_edge("generator", "verification")
    workflow.add_edge("verification", END)

    return workflow.compile()