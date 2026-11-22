from typing import TypedDict, List, Optional, Dict, Any

# 依據國中數學第 1~4 冊課綱順序與先備知識包含關係建立的完整代數知識圖譜（共 14 個細分節點）
CURRICULUM_GRAPH: Dict[str, Dict[str, Any]] = {
    # --- 第一冊：數與一元一次代數地基 ---
    "unit_01_integers": {
        "name": "1. 整數的運算",
        "book": "第一冊 單元1",
        "prerequisites": [],
    },
    "unit_02_fractions": {
        "name": "2. 分數的運算",
        "book": "第一冊 單元2",
        "prerequisites": ["unit_01_integers"],
    },
    "unit_03_linear_eq_1var": {
        "name": "3. 一元一次方程式",
        "book": "第一冊 單元3",
        "prerequisites": ["unit_01_integers", "unit_02_fractions"],
    },

    # --- 第二冊：二元一次、直角坐標、比例與不等式 ---
    "unit_04_linear_system": {
        "name": "4. 二元一次聯立方程式",
        "book": "第二冊 單元4",
        "prerequisites": ["unit_03_linear_eq_1var"],
    },
    "unit_05_linear_graph": {
        "name": "5. 二元一次方程式的圖形",
        "book": "第二冊 單元5",
        "prerequisites": ["unit_04_linear_system"],
    },
    "unit_06_ratio": {
        "name": "6. 比與比例式",
        "book": "第二冊 單元6",
        "prerequisites": ["unit_02_fractions", "unit_03_linear_eq_1var"],
    },
    "unit_07_linear_inequality": {
        "name": "7. 一元一次不等式",
        "book": "第二冊 單元7",
        "prerequisites": ["unit_03_linear_eq_1var"],
    },

    # --- 第三冊：二次代數、根式畢氏與一元二次方程式 ---
    "unit_10_1_multiplication_formula": {
        "name": "10-1. 乘法公式",
        "book": "第三冊 單元10 主題1",
        "prerequisites": ["unit_01_integers", "unit_03_linear_eq_1var"],
    },
    "unit_10_2_polynomial": {
        "name": "10-2. 多項式",
        "book": "第三冊 單元10 主題2",
        "prerequisites": ["unit_10_1_multiplication_formula"],
    },
    "unit_11_1_square_root": {
        "name": "11-1. 平方根與根式運算",
        "book": "第三冊 單元11 主題1",
        "prerequisites": ["unit_01_integers", "unit_10_1_multiplication_formula"],
    },
    "unit_11_2_pythagorean": {
        "name": "11-2. 畢氏定理",
        "book": "第三冊 單元11 主題2",
        "prerequisites": ["unit_11_1_square_root", "unit_10_2_polynomial"],
    },
    "unit_12_1_factorization": {
        "name": "12-1. 因式分解",
        "book": "第三冊 單元12 主題1",
        "prerequisites": ["unit_10_2_polynomial"],
    },
    "unit_12_2_quadratic_eq": {
        "name": "12-2. 一元二次方程式",
        "book": "第三冊 單元12 主題2",
        "prerequisites": ["unit_11_1_square_root", "unit_12_1_factorization"],
    },

    # --- 第四冊：數列與級數 ---
    "unit_13_sequences_series": {
        "name": "13. 數列與級數",
        "book": "第四冊 單元13",
        "prerequisites": ["unit_03_linear_eq_1var", "unit_04_linear_system"],
    },
}

# 快速查詢合法單元代碼對照表
SUPPORTED_TOPICS = {k: v["name"] for k, v in CURRICULUM_GRAPH.items()}


class AgentState(TypedDict):
    """單次任務生命週期內的短期工作狀態 (Short-term AgentState)"""

    # --- 1. 使用者輸入 ---
    topic: str                                      # 單元代碼 (需屬於 CURRICULUM_GRAPH 的 14 個節點之一)
    problem_expr: str                               # 原始題目表達式
    student_steps: List[str]                        # 學生的推導計算步驟列表

    # --- 2. 階段一：錯題診斷結果 ---
    step_verification: Optional[Dict[str, Any]]     # Tool 1 (sympy_step_verifier) 回傳結果
    misconception_tag: Optional[str]                # 迷思概念標籤（可依 prerequisites 溯源至先備單元）
    diagnosis_explanation: Optional[str]            # 白話錯題診斷解析

    # --- 3. 階段二：變形出題結果 (v1.0 單次生成) ---
    generated_problem: Optional[Dict[str, str]]     # 包含 new_problem, solution_steps, proposed_answer

    # --- 4. 階段三：品質驗證結果 ---
    problem_validation: Optional[Dict[str, Any]]    # Tool 2 (sympy_problem_validator) 回傳結果

    # --- 5. 系統狀態與追蹤軌跡 (對應作業二 6.6 Trace 要求) ---
    status: str                                     # "SUCCESS" | "OUT_OF_SCOPE" | "VALIDATION_FAILED"
    trace_logs: List[str]