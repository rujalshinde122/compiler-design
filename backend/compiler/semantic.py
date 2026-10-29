from compiler.diagnostics import record_diagnostic

class SemanticAnalyzer:
    def __init__(self, ast):
        self.ast = ast
        self.symbol_table = []
        self.errors = []
        self.warnings = []
        self.current_scope = "global"
        self.scopes_stack = [{"global": {}}]
        self.declared_symbols = set()
        self.used_symbols = set()
        self.stack_offset = 0

    def _report_error(self, message: str, line: int, col: int = 1):
        diag = record_diagnostic(
            message=message,
            line=line,
            col=col,
            severity="error",
            phase="Semantic Analysis",
            depth=2
        )
        self.errors.append(diag)

    def _report_warning(self, message: str, line: int, col: int = 1):
        diag = record_diagnostic(
            message=message,
            line=line,
            col=col,
            severity="warning",
            phase="Semantic Analysis",
            depth=2
        )
        self.warnings.append(diag)

    def analyze(self):
        self.symbol_table = []
        self.errors = []
        self.warnings = []
        self.current_scope = "global"
        self.scopes_stack = [{"global": {}}]
        self.declared_symbols = set()
        self.used_symbols = set()
        self.stack_offset = 0

        # Traverse AST
        self._analyze_node(self.ast)

        # Check for declared but unused local variables
        for sym in self.symbol_table:
            name = sym["name"]
            scope = sym["scope"]
            if scope != "global" and "function" not in sym["type"]:
                if name not in self.used_symbols:
                    self._report_warning(
                        f"Semantic Warning: Variable '{name}' declared at line {sym['line']} is never used",
                        sym["line"],
                        1
                    )

        return self.symbol_table, self.errors, self.warnings

    def _enter_scope(self, name):
        self.current_scope = name
        self.scopes_stack.append({})

    def _exit_scope(self):
        if len(self.scopes_stack) > 1:
            self.scopes_stack.pop()
            self.current_scope = "global" if len(self.scopes_stack) == 1 else "local"

    def _lookup(self, name):
        for scope in reversed(self.scopes_stack):
            if name in scope:
                return scope[name]
        return None

    def _add_symbol(self, name, data_type, line, is_func=False):
        current_scope_dict = self.scopes_stack[-1]
        if name in current_scope_dict:
            self._report_error(
                f"Semantic Error: Redeclaration of identifier '{name}' in the same scope at line {line}",
                line,
                1
            )
            return

        size = 4
        if data_type == 'char':
            size = 1
        elif data_type == 'float':
            size = 8

        if not is_func:
            self.stack_offset += size
            offset_str = f"-[rbp-{self.stack_offset}]"
        else:
            offset_str = "0x0000"

        sym_entry = {
            "name": name,
            "type": data_type,
            "scope": self.current_scope,
            "line": line,
            "size": f"{size} bytes" if not is_func else "-",
            "offset": offset_str
        }

        current_scope_dict[name] = sym_entry
        self.symbol_table.append(sym_entry)
        self.declared_symbols.add(name)

    def _analyze_node(self, node):
        if not node or not isinstance(node, dict):
            return

        node_type = node.get("type")

        if node_type == "Program":
            for stmt in node.get("body", []):
                self._analyze_node(stmt)

        elif node_type == "FunctionDeclaration":
            name = node.get("name")
            ret_type = node.get("returnType", "int")
            line = node.get("line", 1)
            self._add_symbol(name, f"function returning {ret_type}", line, is_func=True)

            old_offset = self.stack_offset
            self.stack_offset = 0
            self._enter_scope(f"function:{name}")

            # Register parameters
            for param in node.get("params", []):
                p_type = param.get("type", "int")
                p_name = param.get("name")
                if p_name:
                    self._add_symbol(p_name, p_type, line)

            # Analyze function body
            for stmt in node.get("body", []):
                self._analyze_node(stmt)

            self._exit_scope()
            self.stack_offset = old_offset

        elif node_type == "VariableDeclaration":
            ident = node.get("identifier")
            data_type = node.get("dataType", "int")
            line = node.get("line", 1)
            self._add_symbol(ident, data_type, line)

            if node.get("value"):
                self._analyze_expression(node["value"], expected_type=data_type)

        elif node_type == "Assignment":
            ident = node.get("identifier")
            line = node.get("line", 1)
            sym = self._lookup(ident)
            if not sym:
                self._report_error(
                    f"Semantic Error: Identifier '{ident}' assigned at line {line} without prior declaration",
                    line,
                    1
                )
            else:
                self.used_symbols.add(ident)
            if node.get("value"):
                self._analyze_expression(node["value"], expected_type=sym.get("type") if sym else None)

        elif node_type == "IfStatement":
            if node.get("condition"):
                self._analyze_expression(node["condition"])
            for stmt in node.get("body", []):
                self._analyze_node(stmt)
            if node.get("elseBody"):
                for stmt in node.get("elseBody", []):
                    self._analyze_node(stmt)

        elif node_type == "WhileStatement":
            if node.get("condition"):
                self._analyze_expression(node["condition"])
            for stmt in node.get("body", []):
                self._analyze_node(stmt)

        elif node_type == "ForStatement":
            if node.get("init"):
                self._analyze_node(node["init"])
            if node.get("condition"):
                self._analyze_expression(node["condition"])
            if node.get("step"):
                self._analyze_node(node["step"])
            for stmt in node.get("body", []):
                self._analyze_node(stmt)

        elif node_type == "ReturnStatement":
            if node.get("value"):
                self._analyze_expression(node["value"])

        elif node_type == "FunctionCall":
            name = node.get("name")
            sym = self._lookup(name)
            if not sym and name not in ["printf", "scanf", "cout", "cin"]:
                self._report_warning(
                    f"Semantic Warning: Call to function '{name}' without prior prototype declaration",
                    node.get("line", 1),
                    1
                )
            for arg in node.get("args", []):
                self._analyze_expression(arg)

    def _analyze_expression(self, expr_node, expected_type=None):
        if not expr_node or not isinstance(expr_node, dict):
            return

        tree = expr_node.get("tree")
        if tree:
            self._walk_expr_tree(tree, expected_type)

    def _walk_expr_tree(self, tree, expected_type=None):
        if not tree or not isinstance(tree, dict):
            return

        t_type = tree.get("type")
        if t_type == "Identifier":
            name = tree.get("value")
            self.used_symbols.add(name)
            sym = self._lookup(name)
            if not sym:
                self._report_error(
                    f"Semantic Error: Use of undeclared identifier '{name}' in expression",
                    tree.get("line", 1),
                    1
                )
        elif t_type == "BinaryOp":
            self._walk_expr_tree(tree.get("left"), expected_type)
            self._walk_expr_tree(tree.get("right"), expected_type)
        elif t_type == "UnaryOp":
            self._walk_expr_tree(tree.get("operand"), expected_type)
        elif t_type == "Literal":
            val = tree.get("value")
            if expected_type == "int" and isinstance(val, str) and not val.isdigit():
                self._report_warning(
                    f"Semantic Warning: Assigning string literal to numeric type '{expected_type}'",
                    tree.get("line", 1),
                    1
                )

def analyze_semantics(ast):
    analyzer = SemanticAnalyzer(ast)
    return analyzer.analyze()
