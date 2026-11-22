import re
from typing import List, Dict, Any
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
from src.state import CURRICULUM_GRAPH

# 啟用隱式乘法解析（讓 "2x" 或 "(x+1)(x-1)" 能自動轉為 SymPy 表達式）
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


def _normalize_expr_str(raw: str) -> str:
    """將常見輸入符號標準化為 SymPy 可解析格式"""
    cleaned = raw.strip().replace("^", "**").replace("＝", "=").replace("－", "-").replace("＋", "+")
    return cleaned


def _parse_single_relation(raw_str: str):
    """解析單一算式、等式 (=) 或不等式 (<, <=, >, >=)，回傳標準化後的 SymPy 物件"""
    s = _normalize_expr_str(raw_str)

    # 處理不等式 (單元 7)
    for op, func in [("<=", sp.Le), (">=", sp.Ge), ("<", sp.Lt), (">", sp.Gt)]:
        if op in s:
            lhs_str, rhs_str = s.split(op, 1)
            lhs = parse_expr(lhs_str, transformations=TRANSFORMATIONS)
            rhs = parse_expr(rhs_str, transformations=TRANSFORMATIONS)
            return ("inequality", func(lhs, rhs))

    # 處理等式 (單元 3, 4, 5, 6, 11-2, 12-2)
    if "=" in s:
        lhs_str, rhs_str = s.split("=", 1)
        lhs = parse_expr(lhs_str, transformations=TRANSFORMATIONS)
        rhs = parse_expr(rhs_str, transformations=TRANSFORMATIONS)
        return ("equation", sp.Eq(lhs, rhs))

    # 處理純代數式 (單元 1, 2, 10-1, 10-2, 11-1, 12-1, 13)
    expr = parse_expr(s, transformations=TRANSFORMATIONS)
    return ("expression", expr)


def _check_step_equivalence(base_raw: str, step_raw: str) -> bool:
    """比對兩行算式在代數或解集合上是否等價（支援跨單元通用運算）"""
    # 若為聯立方程式（以分號 ';' 區隔多條方程式）
    if ";" in base_raw or ";" in step_raw:
        base_eqs = [_parse_single_relation(part)[1] for part in base_raw.split(";") if part.strip()]
        step_eqs = [_parse_single_relation(part)[1] for part in step_raw.split(";") if part.strip()]
        symbols = list(set().union(*(eq.free_symbols for eq in base_eqs + step_eqs)))
        sol_base = sp.solve(base_eqs, symbols, dict=True)
        sol_step = sp.solve(step_eqs, symbols, dict=True)
        return sol_base == sol_step

    kind_base, obj_base = _parse_single_relation(base_raw)
    kind_step, obj_step = _parse_single_relation(step_raw)

    # 純代數式化簡 / 展開 / 根式 / 因式分解比較
    if kind_base == "expression" and kind_step == "expression":
        diff = sp.simplify(sp.expand(obj_base) - sp.expand(obj_step))
        return diff == 0

    # 方程式同解集比較
    if kind_base == "equation" and kind_step == "equation":
        syms = list(obj_base.free_symbols.union(obj_step.free_symbols))
        if not syms:
            return sp.simplify(obj_base.lhs - obj_base.rhs) == sp.simplify(obj_step.lhs - obj_step.rhs)
        return sp.solve(obj_base, syms) == sp.solve(obj_step, syms)

    # 不等式解區間比較
    if kind_base == "inequality" and kind_step == "inequality":
        syms = list(obj_base.free_symbols.union(obj_step.free_symbols))
        if len(syms) == 1:
            return sp.reduce_inequalities(obj_base, syms[0]) == sp.reduce_inequalities(obj_step, syms[0])

    return False


# ==============================================================================
# Tool 1: sympy_step_verifier（多步推導等價性與錯誤定位工具）
# ==============================================================================
def sympy_step_verifier(topic: str, problem_expr: str, student_steps: List[str]) -> Dict[str, Any]:
    """
    Tool 名稱: sympy_step_verifier
    目的: 逐行檢查學生算式與原題的代數/解集合等價性，精準定位第一個錯誤步驟，
          並提供課綱先備知識追蹤線索。
    """
    if topic not in CURRICULUM_GRAPH:
        return {
            "error_code": "OUT_OF_SYLLABUS_TOPIC",
            "is_all_correct": False,
            "first_error_step": None,
            "expected_hint": f"單元 '{topic}' 不在支援的 14 個國中代數課綱範圍內。",
        }

    if not student_steps:
        return {
            "error_code": "EMPTY_STEPS",
            "is_all_correct": False,
            "first_error_step": None,
            "expected_hint": "學生步驟列表為空，無法執行逐步驗證。",
        }

    topic_info = CURRICULUM_GRAPH[topic]
    prereq_names = [CURRICULUM_GRAPH[p]["name"] for p in topic_info["prerequisites"]]

    try:
        for idx, step in enumerate(student_steps, start=1):
            is_valid_step = _check_step_equivalence(problem_expr, step)
            if not is_valid_step:
                # 計算原題的標準化簡/求解參考提示
                if ";" in problem_expr:
                    eqs = [_parse_single_relation(p)[1] for p in problem_expr.split(";") if p.strip()]
                    syms = list(set().union(*(e.free_symbols for e in eqs)))
                    truth = str(sp.solve(eqs, syms, dict=True))
                else:
                    kind, obj = _parse_single_relation(problem_expr)
                    if kind == "expression":
                        truth = str(sp.factor(obj) if topic == "unit_12_1_factorization" else sp.simplify(sp.expand(obj)))
                    elif kind == "equation":
                        truth = str(sp.solve(obj))
                    else:
                        truth = str(sp.reduce_inequalities(obj))

                return {
                    "error_code": None,
                    "is_all_correct": False,
                    "first_error_step": idx,
                    "wrong_step_content": step,
                    "expected_hint": f"原式標準化簡/解為: {truth}",
                    "prerequisite_chain": prereq_names,
                }

        return {
            "error_code": None,
            "is_all_correct": True,
            "first_error_step": None,
            "wrong_step_content": None,
            "expected_hint": "所有推導步驟皆符合代數等價性。",
            "prerequisite_chain": prereq_names,
        }

    except Exception as exc:
        return {
            "error_code": "INVALID_EXPRESSION_SYNTAX",
            "is_all_correct": False,
            "first_error_step": None,
            "expected_hint": f"算式語法解析失敗（請確認括號與運算符號）：{str(exc)}",
        }


# ==============================================================================
# Tool 2: sympy_problem_validator（變形題合法性與國中課綱約束驗證工具）
# ==============================================================================
def sympy_problem_validator(topic: str, generated_problem: str, proposed_answer: str) -> Dict[str, Any]:
    """
    Tool 名稱: sympy_problem_validator
    目的: 驗證變形題目是否具備唯一合法解（且符合國中整數解/實數解/因式乘積約束），
          並核對 LLM 提供的參考答案是否正確。
    """
    if topic not in CURRICULUM_GRAPH:
        return {
            "is_valid": False,
            "error_code": "OUT_OF_SYLLABUS_TOPIC",
            "sympy_ground_truth": None,
            "validation_message": f"FAIL: 單元 '{topic}' 超出支援範圍。",
        }

    try:
        # 1. 二元一次聯立方程式 (單元 4)：必須具備唯一整數解
        if topic == "unit_04_linear_system" or ";" in generated_problem:
            eqs = [_parse_single_relation(p)[1] for p in generated_problem.split(";") if p.strip()]
            syms = sorted(list(set().union(*(e.free_symbols for e in eqs))), key=str)
            sols = sp.solve(eqs, syms, dict=True)
            if len(sols) != 1:
                return {
                    "is_valid": False,
                    "error_code": "NO_UNIQUE_SOLUTION",
                    "sympy_ground_truth": str(sols),
                    "validation_message": "FAIL: 聯立方程組無解或無限多解。",
                }
            sol_dict = sols[0]
            all_integers = all(val.is_integer for val in sol_dict.values())
            truth_str = ", ".join(f"{k}={v}" for k, v in sol_dict.items())
            if not all_integers:
                return {
                    "is_valid": False,
                    "error_code": "NON_INTEGER_SOLUTION",
                    "sympy_ground_truth": truth_str,
                    "validation_message": f"FAIL: 產生非整數分數解 ({truth_str})，不符合國中基礎練習難度。",
                }
            return {
                "is_valid": True,
                "error_code": None,
                "sympy_ground_truth": truth_str,
                "validation_message": f"PASS: 具備唯一整數解 ({truth_str})。",
            }

        kind, obj = _parse_single_relation(generated_problem)

        # 2. 畢氏定理 (單元 11-2)：檢查斜邊/邊長是否為正整數（畢氏三元數）
        if topic == "unit_11_2_pythagorean" and kind == "equation":
            syms = list(obj.free_symbols)
            sols = [s for s in sp.solve(obj, syms[0]) if s.is_real and s > 0]
            if not sols or not sols[0].is_integer:
                return {
                    "is_valid": False,
                    "error_code": "NON_INTEGER_HYPOTENUSE",
                    "sympy_ground_truth": str(sols),
                    "validation_message": f"FAIL: 畢氏定理邊長非整數 ({sols})，非畢氏三元數。",
                }
            return {
                "is_valid": True,
                "error_code": None,
                "sympy_ground_truth": f"{syms[0]}={sols[0]}",
                "validation_message": f"PASS: 符合畢氏三元數正整數解 ({syms[0]}={sols[0]})。",
            }

        # 3. 因式分解 (單元 12-1)：驗證分解結果展開後與原式相等且包含乘積結構
        if topic == "unit_12_1_factorization" and kind == "expression":
            factored_truth = sp.factor(obj)
            _, ans_obj = _parse_single_relation(proposed_answer)
            is_equiv = sp.simplify(sp.expand(obj) - sp.expand(ans_obj)) == 0
            is_factored_form = isinstance(ans_obj, (sp.Mul, sp.Pow)) and str(ans_obj) != str(sp.expand(obj))
            if not (is_equiv and is_factored_form):
                return {
                    "is_valid": False,
                    "error_code": "INCOMPLETE_FACTORIZATION",
                    "sympy_ground_truth": str(factored_truth),
                    "validation_message": f"FAIL: 答案未完成因式分解或展開不等價（標準分解：{factored_truth}）。",
                }
            return {
                "is_valid": True,
                "error_code": None,
                "sympy_ground_truth": str(factored_truth),
                "validation_message": f"PASS: 因式分解驗證通過 ({factored_truth})。",
            }

        # 4. 一元二次方程式 (單元 12-2)：確保具備實數解（排除高中虛根）
        if topic == "unit_12_2_quadratic_eq" and kind == "equation":
            syms = list(obj.free_symbols)
            sols = sp.solve(obj, syms[0])
            if not sols or not all(s.is_real for s in sols):
                return {
                    "is_valid": False,
                    "error_code": "COMPLEX_ROOTS_OUT_OF_SCOPE",
                    "sympy_ground_truth": str(sols),
                    "validation_message": "FAIL: 一元二次方程式出現無實數解（虛根），超出國中課綱範圍。",
                }
            return {
                "is_valid": True,
                "error_code": None,
                "sympy_ground_truth": str(sols),
                "validation_message": f"PASS: 具備合法實數解 ({sols})。",
            }

        # 5. 其餘單元（整數、分數、一元一次、圖形、比例、不等式、乘法公式、多項式、根式、數列）
        if kind == "expression":
            truth = sp.simplify(sp.expand(obj))
            _, ans_obj = _parse_single_relation(proposed_answer)
            is_equiv = sp.simplify(truth - sp.expand(ans_obj)) == 0
            return {
                "is_valid": is_equiv,
                "error_code": None if is_equiv else "ANSWER_MISMATCH",
                "sympy_ground_truth": str(truth),
                "validation_message": f"{'PASS' if is_equiv else 'FAIL'}: 標準化簡結果為 {truth}。",
            }

        if kind == "equation":
            syms = list(obj.free_symbols)
            sols = sp.solve(obj, syms[0]) if syms else []
            return {
                "is_valid": len(sols) > 0,
                "error_code": None if sols else "NO_SOLUTION",
                "sympy_ground_truth": str(sols),
                "validation_message": f"PASS: 方程式求解結果為 {sols}。",
            }

        if kind == "inequality":
            syms = list(obj.free_symbols)
            sol_region = sp.reduce_inequalities(obj, syms[0])
            return {
                "is_valid": True,
                "error_code": None,
                "sympy_ground_truth": str(sol_region),
                "validation_message": f"PASS: 不等式解區間為 {sol_region}。",
            }

        return {
            "is_valid": False,
            "error_code": "UNSUPPORTED_FORMAT",
            "sympy_ground_truth": None,
            "validation_message": "FAIL: 無法識別的算式格式。",
        }

    except Exception as exc:
        return {
            "is_valid": False,
            "error_code": "INVALID_EXPRESSION_SYNTAX",
            "sympy_ground_truth": None,
            "validation_message": f"FAIL: 算式解析錯誤 ({str(exc)})。",
        }