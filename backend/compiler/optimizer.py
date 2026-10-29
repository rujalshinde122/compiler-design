import re

class CodeOptimizer:
    def __init__(self, quadruples, tac_lines):
        self.quadruples = [dict(q) for q in quadruples]
        self.tac_lines = list(tac_lines)
        self.optimizations_applied = []

    def optimize(self):
        self.optimizations_applied = []
        
        # Iteratively apply optimization passes until convergence or max iterations reached
        changed = True
        iterations = 0
        max_iterations = 5

        while changed and iterations < max_iterations:
            iterations += 1
            changed = False

            # Pass 1: Constant Folding & Algebraic Simplification
            if self._pass_constant_folding_and_algebraic():
                changed = True

            # Pass 2: Constant Propagation & Copy Propagation
            if self._pass_propagation():
                changed = True

            # Pass 3: Dead Code Elimination (unreachable instructions & unused temporaries)
            if self._pass_dead_code_elimination():
                changed = True

        # Rebuild TAC lines and quadruples from the optimized state
        optimized_tac, optimized_quads = self._rebuild_results()
        return optimized_tac, optimized_quads, self.optimizations_applied

    def _is_number(self, val):
        if not val or not isinstance(val, str):
            return False
        if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
            return True
        try:
            float(val)
            return True
        except ValueError:
            return False

    def _eval_binary(self, op, v1, v2):
        n1 = int(v1) if '.' not in v1 else float(v1)
        n2 = int(v2) if '.' not in v2 else float(v2)

        if op == '+': return str(n1 + n2)
        if op == '-': return str(n1 - n2)
        if op == '*': return str(n1 * n2)
        if op == '/': return str(n1 // n2) if n2 != 0 else "0"
        if op == '%': return str(n1 % n2) if n2 != 0 else "0"
        if op == '<': return "1" if n1 < n2 else "0"
        if op == '>': return "1" if n1 > n2 else "0"
        if op == '<=': return "1" if n1 <= n2 else "0"
        if op == '>=': return "1" if n1 >= n2 else "0"
        if op == '==': return "1" if n1 == n2 else "0"
        if op == '!=': return "1" if n1 != n2 else "0"
        return None

    def _pass_constant_folding_and_algebraic(self):
        applied = False
        for q in self.quadruples:
            op = q["op"]
            arg1 = q["arg1"]
            arg2 = q["arg2"]
            res = q["result"]

            # Constant folding: both args are numbers
            if op in ['+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!=']:
                if self._is_number(arg1) and self._is_number(arg2):
                    folded_val = self._eval_binary(op, arg1, arg2)
                    if folded_val is not None:
                        old_expr = f"{arg1} {op} {arg2}"
                        q["op"] = "="
                        q["arg1"] = folded_val
                        q["arg2"] = "-"
                        self.optimizations_applied.append({
                            "pass": "Constant Folding",
                            "detail": f"Evaluated '{old_expr}' into '{folded_val}' for '{res}'",
                            "result": res,
                            "value": folded_val
                        })
                        applied = True
                        continue

            # Algebraic Simplification & Strength Reduction
            if op == '+':
                if arg1 == '0':
                    q["op"] = "="
                    q["arg1"] = arg2
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Algebraic Simplification",
                        "detail": f"Simplified '0 + {arg2}' to '{arg2}'",
                        "result": res
                    })
                    applied = True
                elif arg2 == '0':
                    q["op"] = "="
                    q["arg1"] = arg1
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Algebraic Simplification",
                        "detail": f"Simplified '{arg1} + 0' to '{arg1}'",
                        "result": res
                    })
                    applied = True

            elif op == '-':
                if arg2 == '0':
                    q["op"] = "="
                    q["arg1"] = arg1
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Algebraic Simplification",
                        "detail": f"Simplified '{arg1} - 0' to '{arg1}'",
                        "result": res
                    })
                    applied = True
                elif arg1 == arg2 and arg1 != "-":
                    q["op"] = "="
                    q["arg1"] = "0"
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Algebraic Simplification",
                        "detail": f"Simplified '{arg1} - {arg2}' to '0'",
                        "result": res
                    })
                    applied = True

            elif op == '*':
                if arg1 == '1':
                    q["op"] = "="
                    q["arg1"] = arg2
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Strength Reduction",
                        "detail": f"Simplified '1 * {arg2}' to '{arg2}'",
                        "result": res
                    })
                    applied = True
                elif arg2 == '1':
                    q["op"] = "="
                    q["arg1"] = arg1
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Strength Reduction",
                        "detail": f"Simplified '{arg1} * 1' to '{arg1}'",
                        "result": res
                    })
                    applied = True
                elif arg1 == '0' or arg2 == '0':
                    q["op"] = "="
                    q["arg1"] = "0"
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Strength Reduction",
                        "detail": f"Simplified multiplication by 0 to '0'",
                        "result": res
                    })
                    applied = True

            elif op == '/':
                if arg2 == '1':
                    q["op"] = "="
                    q["arg1"] = arg1
                    q["arg2"] = "-"
                    self.optimizations_applied.append({
                        "pass": "Strength Reduction",
                        "detail": f"Simplified '{arg1} / 1' to '{arg1}'",
                        "result": res
                    })
                    applied = True

        return applied

    def _pass_propagation(self):
        applied = False
        # Propagate constants and copies within straight-line basic blocks
        constants = {}  # var -> const_val

        for i, q in enumerate(self.quadruples):
            op = q["op"]
            arg1 = q["arg1"]
            arg2 = q["arg2"]
            res = q["result"]

            # Clear mappings across labels/jumps for safety
            if op in ["label", "PROC", "ENDPROC", "goto", "ifFalse", "if"]:
                constants.clear()
                continue

            # Replace arg1 if known constant
            if arg1 in constants:
                new_arg1 = constants[arg1]
                q["arg1"] = new_arg1
                self.optimizations_applied.append({
                    "pass": "Constant Propagation",
                    "detail": f"Substituted known constant '{arg1} = {new_arg1}' in statement",
                    "result": res
                })
                applied = True

            # Replace arg2 if known constant
            if arg2 in constants:
                new_arg2 = constants[arg2]
                q["arg2"] = new_arg2
                self.optimizations_applied.append({
                    "pass": "Constant Propagation",
                    "detail": f"Substituted known constant '{arg2} = {new_arg2}' in statement",
                    "result": res
                })
                applied = True

            # Record newly assigned constant
            if op == "=" and self._is_number(q["arg1"]):
                constants[res] = q["arg1"]
            elif res in constants:
                # Value overwritten
                del constants[res]

        return applied

    def _pass_dead_code_elimination(self):
        applied = False
        new_quads = []
        is_dead = False

        # Phase A: Remove instructions after unconditional jump or return before the next label
        for q in self.quadruples:
            op = q["op"]

            if op in ["label", "PROC", "ENDPROC"]:
                is_dead = False
                new_quads.append(q)
                continue

            if is_dead:
                self.optimizations_applied.append({
                    "pass": "Dead Code Elimination",
                    "detail": f"Removed unreachable instruction '{op} {q['arg1']} {q['arg2']} -> {q['result']}'",
                    "result": q["result"]
                })
                applied = True
                continue

            new_quads.append(q)

            if op in ["goto", "return"]:
                is_dead = True

        # Phase B: Remove assignments to temporary variables (t0, t1...) that are never read
        # Count reads of each identifier
        read_counts = {}
        for q in new_quads:
            for arg in [q["arg1"], q["arg2"]]:
                if arg and arg != "-":
                    read_counts[arg] = read_counts.get(arg, 0) + 1

        cleaned_quads = []
        for q in new_quads:
            res = q["result"]
            op = q["op"]
            # If result is a temporary (starts with 't' followed by digits) and never read
            if res.startswith("t") and res[1:].isdigit() and op not in ["return", "PROC", "ENDPROC", "label", "ifFalse", "goto"]:
                if read_counts.get(res, 0) == 0:
                    self.optimizations_applied.append({
                        "pass": "Dead Code Elimination",
                        "detail": f"Removed dead temporary assignment '{res}' (never used)",
                        "result": res
                    })
                    applied = True
                    continue
            cleaned_quads.append(q)

        self.quadruples = cleaned_quads
        return applied

    def _rebuild_results(self):
        rebuilt_tac = []
        rebuilt_quads = []

        for idx, q in enumerate(self.quadruples):
            op = q["op"]
            arg1 = q["arg1"]
            arg2 = q["arg2"]
            res = q["result"]

            if op == "PROC":
                tac = f"PROCEDURE {arg1}:"
            elif op == "ENDPROC":
                tac = f"END PROCEDURE {arg1}"
            elif op == "DECLARE":
                tac = f"DECLARE {arg1}"
            elif op == "=":
                tac = f"{res} = {arg1}"
            elif op == "label":
                tac = f"{res}:"
            elif op == "goto":
                tac = f"goto {res}"
            elif op == "ifFalse":
                tac = f"ifFalse {arg1} goto {res}"
            elif op == "return":
                tac = f"return {arg1}" if arg1 != "-" else "return"
            elif op in ['+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!=']:
                tac = f"{res} = {arg1} {op} {arg2}"
            else:
                tac = f"{res} = {op} {arg1} {arg2}"

            rebuilt_tac.append(tac)
            rebuilt_quads.append({
                "index": idx,
                "op": op,
                "arg1": arg1,
                "arg2": arg2,
                "result": res
            })

        return rebuilt_tac, rebuilt_quads

def optimize_code(quadruples, tac_lines):
    optimizer = CodeOptimizer(quadruples, tac_lines)
    opt_tac, opt_quads, applied = optimizer.optimize()
    opt_tac_text = "\n".join(opt_tac)
    return opt_tac, opt_quads, opt_tac_text, applied
