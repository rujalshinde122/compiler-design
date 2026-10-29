class ICGGenerator:
    def __init__(self):
        self.temp_count = 0
        self.label_count = 0
        self.tac_instructions = []  # list of strings
        self.quadruples = []        # list of dicts: {index, op, arg1, arg2, result}

    def new_temp(self):
        t = f"t{self.temp_count}"
        self.temp_count += 1
        return t

    def new_label(self, prefix="L"):
        self.label_count += 1
        return f"{prefix}{self.label_count}"

    def emit(self, tac_str, op, arg1="-", arg2="-", result="-"):
        idx = len(self.quadruples)
        self.tac_instructions.append(tac_str)
        self.quadruples.append({
            "index": idx,
            "op": op,
            "arg1": str(arg1),
            "arg2": str(arg2),
            "result": str(result)
        })

    def generate(self, ast):
        self.temp_count = 0
        self.label_count = 0
        self.tac_instructions = []
        self.quadruples = []

        if not ast or not isinstance(ast, dict):
            return self.tac_instructions, self.quadruples

        for stmt in ast.get("body", []):
            self._gen_statement(stmt)

        return self.tac_instructions, self.quadruples

    def _gen_statement(self, node):
        if not node:
            return

        ntype = node.get("type")

        if ntype == "FunctionDeclaration":
            name = node.get("name")
            self.emit(f"PROCEDURE {name}:", "PROC", name, "-", "-")
            for s in node.get("body", []):
                self._gen_statement(s)
            self.emit(f"END PROCEDURE {name}", "ENDPROC", name, "-", "-")

        elif ntype == "VariableDeclaration":
            ident = node.get("identifier")
            val_node = node.get("value")
            if val_node:
                res = self._gen_expression(val_node)
                self.emit(f"{ident} = {res}", "=", res, "-", ident)
            else:
                self.emit(f"DECLARE {ident}", "DECLARE", ident, "-", "-")

        elif ntype == "Assignment":
            ident = node.get("identifier")
            val_node = node.get("value")
            if val_node:
                res = self._gen_expression(val_node)
                self.emit(f"{ident} = {res}", "=", res, "-", ident)

        elif ntype == "IfStatement":
            cond_node = node.get("condition")
            cond_res = self._gen_expression(cond_node)
            else_body = node.get("elseBody")

            if else_body:
                lbl_else = self.new_label("L_ELSE_")
                lbl_end = self.new_label("L_ENDIF_")

                self.emit(f"ifFalse {cond_res} goto {lbl_else}", "ifFalse", cond_res, "-", lbl_else)
                for s in node.get("body", []):
                    self._gen_statement(s)
                self.emit(f"goto {lbl_end}", "goto", "-", "-", lbl_end)

                self.emit(f"{lbl_else}:", "label", "-", "-", lbl_else)
                for s in else_body:
                    self._gen_statement(s)
                self.emit(f"{lbl_end}:", "label", "-", "-", lbl_end)
            else:
                lbl_end = self.new_label("L_ENDIF_")
                self.emit(f"ifFalse {cond_res} goto {lbl_end}", "ifFalse", cond_res, "-", lbl_end)
                for s in node.get("body", []):
                    self._gen_statement(s)
                self.emit(f"{lbl_end}:", "label", "-", "-", lbl_end)

        elif ntype == "WhileStatement":
            lbl_start = self.new_label("L_WHILE_START_")
            lbl_end = self.new_label("L_WHILE_END_")

            self.emit(f"{lbl_start}:", "label", "-", "-", lbl_start)
            cond_res = self._gen_expression(node.get("condition"))
            self.emit(f"ifFalse {cond_res} goto {lbl_end}", "ifFalse", cond_res, "-", lbl_end)
            for s in node.get("body", []):
                self._gen_statement(s)
            self.emit(f"goto {lbl_start}", "goto", "-", "-", lbl_start)
            self.emit(f"{lbl_end}:", "label", "-", "-", lbl_end)

        elif ntype == "ForStatement":
            if node.get("init"):
                self._gen_statement(node["init"])
            lbl_start = self.new_label("L_FOR_START_")
            lbl_end = self.new_label("L_FOR_END_")

            self.emit(f"{lbl_start}:", "label", "-", "-", lbl_start)
            if node.get("condition"):
                cond_res = self._gen_expression(node["condition"])
                self.emit(f"ifFalse {cond_res} goto {lbl_end}", "ifFalse", cond_res, "-", lbl_end)
            for s in node.get("body", []):
                self._gen_statement(s)
            if node.get("step"):
                self._gen_statement(node["step"])
            self.emit(f"goto {lbl_start}", "goto", "-", "-", lbl_start)
            self.emit(f"{lbl_end}:", "label", "-", "-", lbl_end)

        elif ntype == "ReturnStatement":
            val_node = node.get("value")
            if val_node:
                res = self._gen_expression(val_node)
                self.emit(f"return {res}", "return", res, "-", "-")
            else:
                self.emit("return", "return", "-", "-", "-")

        elif ntype == "FunctionCall":
            arg_results = []
            for arg in node.get("args", []):
                r = self._gen_expression(arg)
                arg_results.append(r)
            for r in arg_results:
                self.emit(f"param {r}", "param", r, "-", "-")
            name = node.get("name")
            self.emit(f"call {name}, {len(arg_results)}", "call", name, str(len(arg_results)), "-")

    def _gen_expression(self, expr_node):
        if not expr_node:
            return "0"

        tree = expr_node.get("tree")
        if tree:
            return self._gen_tree(tree)

        # Fallback to literal/identifier from raw string
        val = str(expr_node.get("value", "")).strip()
        return val if val else "0"

    def _gen_tree(self, tree):
        if not tree or not isinstance(tree, dict):
            return "0"

        ttype = tree.get("type")

        if ttype == "Literal":
            return str(tree.get("value"))

        elif ttype == "Identifier":
            return str(tree.get("value"))

        elif ttype == "UnaryOp":
            op = tree.get("op")
            operand = self._gen_tree(tree.get("operand"))
            temp = self.new_temp()
            self.emit(f"{temp} = {op} {operand}", op, operand, "-", temp)
            return temp

        elif ttype == "BinaryOp":
            op = tree.get("op")
            left_res = self._gen_tree(tree.get("left"))
            right_res = self._gen_tree(tree.get("right"))
            temp = self.new_temp()
            self.emit(f"{temp} = {left_res} {op} {right_res}", op, left_res, right_res, temp)
            return temp

        return "0"

def generate_intermediate_code(ast):
    generator = ICGGenerator()
    tac_lines, quadruples = generator.generate(ast)
    tac_text = "\n".join(tac_lines)
    return tac_lines, quadruples, tac_text
