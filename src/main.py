import json
from src.agent import build_math_tutor_graph
from src.tools import sympy_problem_validator


def run_demo_case(graph, case_title: str, topic: str, problem_expr: str, student_steps: list[str]):
    """執行單一測試案例並印出完整 Trace 與結構化輸出"""
    print("=" * 80)
    print(f"【{case_title}】")
    print("=" * 80)

    initial_state = {
        "topic": topic,
        "problem_expr": problem_expr,
        "student_steps": student_steps,
        "step_verification": None,
        "misconception_tag": None,
        "diagnosis_explanation": None,
        "generated_problem": None,
        "problem_validation": None,
        "status": "RUNNING",
        "trace_logs": [],
    }

    final_state = graph.invoke(initial_state)

    print("\n--- 執行軌跡 (Execution Trace) ---")
    for line in final_state["trace_logs"]:
        print(f"  {line}")

    print("\n--- 結構化診斷與出題結果 (Structured Output) ---")
    output_summary = {
        "status": final_state["status"],
        "topic": final_state["topic"],
        "misconception_tag": final_state.get("misconception_tag"),
        "diagnosis_explanation": final_state.get("diagnosis_explanation"),
        "generated_problem": final_state.get("generated_problem"),
        "problem_validation": final_state.get("problem_validation"),
    }
    print(json.dumps(output_summary, ensure_ascii=False, indent=2))
    print()


def main():
    print("\n>>> 啟動國中數學錯題診斷與變形出題 Agent (v1.0 Baseline) <<<")
    print(">>> 支援課綱：國中第 1~4 冊共 14 個代數與數列細分單元 <<<\n")

    tutor_graph = build_math_tutor_graph()

    # --------------------------------------------------------------------------
    # Case 1: 第三冊 單元 10-1 乘法公式（漏掉交叉項 2ab 的典型迷思）
    # --------------------------------------------------------------------------
    run_demo_case(
        graph=tutor_graph,
        case_title="Case 1: 乘法公式錯題診斷與變形出題 (unit_10_1_multiplication_formula)",
        topic="unit_10_1_multiplication_formula",
        problem_expr="(x - 3)**2",
        student_steps=[
            "x**2 + 9",  # 常見錯誤：誤以為 (a - b)^2 = a^2 + b^2，漏掉 -6x
        ],
    )

    # --------------------------------------------------------------------------
    # Case 2: 第二冊 單元 4 二元一次聯立方程式（加減消去法計算錯誤）
    # --------------------------------------------------------------------------
    run_demo_case(
        graph=tutor_graph,
        case_title="Case 2: 二元一次聯立方程式錯題診斷 (unit_04_linear_system)",
        topic="unit_04_linear_system",
        problem_expr="x + y = 5; x - y = 1",
        student_steps=[
            "2*x = 6; x - y = 1",  # 第 1 步正確（兩式相加得 2x = 6）
            "x = 3; y = 4",        # 第 2 步錯誤（3 - y = 1 應得 y = 2，學生移項寫成 4）
        ],
    )

    # --------------------------------------------------------------------------
    # Case 3 (Failure Case 1): 課綱邊界超綱防呆攔截（輸入高中微積分）
    # --------------------------------------------------------------------------
    run_demo_case(
        graph=tutor_graph,
        case_title="Case 3 (Failure Case 1): 超出國中課綱範圍攔截測試 (calculus)",
        topic="calculus_derivative",
        problem_expr="x**3 + 2*x",
        student_steps=["3*x**2 + 2"],
    )

    # --------------------------------------------------------------------------
    # Case 4 (Failure Case 2): Tool 2 驗證攔截非畢氏三元數（v1.0 無自動重試機制）
    # --------------------------------------------------------------------------
    print("=" * 80)
    print("【Case 4 (Failure Case 2): Tool 2 驗證攔截非畢氏三元數與虛根題目】")
    print("=" * 80)
    non_triple_check = sympy_problem_validator(
        topic="unit_11_2_pythagorean",
        generated_problem="2**2 + 3**2 = c**2",
        proposed_answer="sqrt(13)",
    )
    print("  [測試輸入] 單元=unit_11_2_pythagorean | 生成題目: 2**2 + 3**2 = c**2")
    print(f"  [Tool 2 攔截結果] {json.dumps(non_triple_check, ensure_ascii=False)}")

    complex_root_check = sympy_problem_validator(
        topic="unit_12_2_quadratic_eq",
        generated_problem="x**2 + 4 = 0",
        proposed_answer="2*I",
    )
    print("  [測試輸入] 單元=unit_12_2_quadratic_eq | 生成題目: x**2 + 4 = 0")
    print(f"  [Tool 2 攔截結果] {json.dumps(complex_root_check, ensure_ascii=False)}")
    print("\n>>> 所有測試案例執行完畢 <<<\n")


if __name__ == "__main__":
    main()