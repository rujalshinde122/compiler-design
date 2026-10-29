from compiler.diagnostics import record_diagnostic

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.symbol_table = []
        self.errors = []
        self.ast = {"id": "root", "type": "Program", "body": []}
        self.node_counter = 0

    def _report_error(self, message: str, line: int, col: int = 1, severity: str = "error"):
        diag = record_diagnostic(
            message=message,
            line=line,
            col=col,
            severity=severity,
            phase="Syntax Analysis",
            depth=2
        )
        self.errors.append(diag)

    def get_next_node_id(self):
        self.node_counter += 1
        return f"node_{self.node_counter}"

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset=0):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def match(self, expected_type):
        tok = self.current_token()
        if tok and tok['type'] == expected_type:
            self.pos += 1
            return tok
        return None

    def expect(self, expected_type, context=""):
        tok = self.current_token()
        if tok and tok['type'] == expected_type:
            self.pos += 1
            return tok

        prev_tok = self.tokens[self.pos - 1] if self.pos > 0 and self.tokens else None
        line = prev_tok['line'] if (not tok and prev_tok) else (tok['line'] if tok else 1)
        col = (prev_tok.get('col', 1) + prev_tok.get('len', 1)) if (not tok and prev_tok) else (tok.get('col', 1) if tok else 1)
        found = f"'{tok['value']}'" if tok else "end of input"

        msg = f"Syntax Error at line {line}:{col}: expected '{expected_type}' {context}, but found {found}"
        self._report_error(msg, line, col)
        return None

    def parse(self):
        self.errors = []
        while self.pos < len(self.tokens):
            old_pos = self.pos
            stmt = self.parse_statement()
            if stmt:
                self.ast["body"].append(stmt)
            elif self.pos == old_pos:
                tok = self.current_token()
                if tok:
                    self._report_error(
                        f"Syntax Error at line {tok['line']}:{tok.get('col', 1)}: unexpected token '{tok['value']}'",
                        tok['line'],
                        tok.get('col', 1)
                    )
                    self.pos += 1
        return self.ast, self.symbol_table, self.errors

    def parse_statement(self):
        tok = self.peek()
        if not tok:
            return None

        if tok['type'] in ['INT', 'FLOAT', 'CHAR', 'VOID']:
            return self.parse_declaration_or_function()
        elif tok['type'] == 'WHILE':
            return self.parse_while()
        elif tok['type'] == 'FOR':
            return self.parse_for()
        elif tok['type'] == 'IF':
            return self.parse_if()
        elif tok['type'] == 'RETURN':
            return self.parse_return()
        elif tok['type'] == 'IDENTIFIER':
            if self.peek(1) and self.peek(1)['type'] == 'LPAREN':
                return self.parse_function_call_stmt()
            else:
                return self.parse_assignment()
        elif tok['type'] == 'LBRACE':
            return self.parse_block()
        
        return None

    def parse_declaration_or_function(self):
        data_type = self.current_token()
        self.pos += 1  # consume type
        
        ident = self.expect('IDENTIFIER', 'after type specifier')
        if not ident:
            return None

        # Check if function declaration
        if self.peek() and self.peek()['type'] == 'LPAREN':
            self.match('LPAREN')
            params = []
            while self.peek() and self.peek()['type'] != 'RPAREN':
                if self.peek()['type'] in ['INT', 'FLOAT', 'CHAR', 'VOID']:
                    p_type = self.current_token()['value']
                    self.pos += 1
                    p_name = ""
                    if self.peek() and self.peek()['type'] == 'IDENTIFIER':
                        p_name = self.current_token()['value']
                        self.pos += 1
                    params.append({"type": p_type, "name": p_name})
                    if self.peek() and self.peek()['type'] == 'COMMA':
                        self.match('COMMA')
                else:
                    self.pos += 1
            self.expect('RPAREN', 'after parameter list')
            
            self.symbol_table.append({
                "name": ident['value'],
                "type": f"function returning {data_type['value']}",
                "scope": "global",
                "line": ident['line']
            })

            body = self.parse_block()
            return {
                "id": self.get_next_node_id(),
                "type": "FunctionDeclaration",
                "name": ident['value'],
                "returnType": data_type['value'],
                "params": params,
                "body": body,
                "line": ident['line']
            }
        else:
            # Variable declaration
            self.symbol_table.append({
                "name": ident['value'],
                "type": data_type['value'],
                "scope": "local",
                "line": ident['line']
            })
            
            node = {
                "id": self.get_next_node_id(),
                "type": "VariableDeclaration",
                "dataType": data_type['value'],
                "identifier": ident['value'],
                "value": None,
                "line": ident['line']
            }
            if self.match('ASSIGN'):
                val = self.parse_expression()
                if not val:
                    prev_tok = self.tokens[self.pos - 1] if self.pos > 0 else ident
                    self._report_error(
                        f"Syntax Error at line {prev_tok['line']}:{prev_tok.get('col', 1) + 1}: expected expression after '='",
                        prev_tok['line'],
                        prev_tok.get('col', 1) + 1
                    )
                node["value"] = val
            
            # Check for extra garbage tokens before semicolon
            self._check_extra_expression_tokens()

            self.expect('SEMICOLON', 'at end of variable declaration')
            return node

    def parse_assignment(self):
        ident = self.match('IDENTIFIER')
        if not ident:
            return None
        line = ident['line']
        if self.match('ASSIGN'):
            val = self.parse_expression()
            if not val:
                prev_tok = self.tokens[self.pos - 1] if self.pos > 0 else ident
                self._report_error(
                    f"Syntax Error at line {prev_tok['line']}:{prev_tok.get('col', 1) + 1}: expected expression after '='",
                    prev_tok['line'],
                    prev_tok.get('col', 1) + 1
                )
            self._check_extra_expression_tokens()
            self.expect('SEMICOLON', 'after assignment')
            return {
                "id": self.get_next_node_id(),
                "type": "Assignment",
                "identifier": ident['value'],
                "value": val,
                "line": line
            }
        return None

    def _check_extra_expression_tokens(self):
        """Detect trailing stray operands (e.g. `int b = a 2;`)"""
        curr = self.current_token()
        if curr and curr['type'] in ['NUMBER', 'IDENTIFIER', 'STRING']:
            self._report_error(
                f"Syntax Error at line {curr['line']}:{curr.get('col', 1)}: unexpected token '{curr['value']}'; missing operator before expression",
                curr['line'],
                curr.get('col', 1)
            )
            # Advance stray tokens until semicolon or statement boundary
            while self.current_token() and self.current_token()['type'] not in ['SEMICOLON', 'RBRACE', 'INT', 'FLOAT', 'CHAR', 'VOID', 'RETURN', 'IF', 'WHILE', 'FOR']:
                self.pos += 1

    def parse_function_call_stmt(self):
        ident = self.match('IDENTIFIER')
        self.match('LPAREN')
        args = []
        while self.peek() and self.peek()['type'] != 'RPAREN':
            arg = self.parse_expression()
            if arg:
                args.append(arg)
            if self.peek() and self.peek()['type'] == 'COMMA':
                self.match('COMMA')
        self.expect('RPAREN', 'after argument list')
        self.expect('SEMICOLON', 'after function call')
        return {
            "id": self.get_next_node_id(),
            "type": "FunctionCall",
            "name": ident['value'],
            "args": args,
            "line": ident['line']
        }

    def parse_while(self):
        tok = self.match('WHILE')
        self.expect('LPAREN', 'after while')
        cond = self.parse_expression()
        self.expect('RPAREN', 'after while condition')
        body = self.parse_statement_or_block()
        return {
            "id": self.get_next_node_id(),
            "type": "WhileStatement",
            "condition": cond,
            "body": body,
            "line": tok['line']
        }

    def parse_for(self):
        tok = self.match('FOR')
        self.expect('LPAREN', 'after for')
        init = None
        if self.peek() and self.peek()['type'] in ['INT', 'FLOAT', 'CHAR']:
            init = self.parse_declaration_or_function()
        elif self.peek() and self.peek()['type'] == 'IDENTIFIER':
            init = self.parse_assignment()
        else:
            self.match('SEMICOLON')
            
        cond = self.parse_expression()
        self.expect('SEMICOLON', 'after for condition')
        
        step = None
        if self.peek() and self.peek()['type'] != 'RPAREN':
            ident = self.match('IDENTIFIER')
            if ident and self.match('ASSIGN'):
                val = self.parse_expression()
                step = {
                    "id": self.get_next_node_id(),
                    "type": "Assignment",
                    "identifier": ident['value'],
                    "value": val,
                    "line": ident['line']
                }
        self.expect('RPAREN', 'after for step')
        body = self.parse_statement_or_block()
        
        return {
            "id": self.get_next_node_id(),
            "type": "ForStatement",
            "init": init,
            "condition": cond,
            "step": step,
            "body": body,
            "line": tok['line']
        }

    def parse_if(self):
        tok = self.match('IF')
        self.expect('LPAREN', 'after if')
        cond = self.parse_expression()
        self.expect('RPAREN', 'after if condition')
        body = self.parse_statement_or_block()
        
        else_body = None
        if self.peek() and self.peek()['type'] == 'ELSE':
            self.match('ELSE')
            if self.peek() and self.peek()['type'] == 'IF':
                else_body = [self.parse_if()]
            else:
                else_body = self.parse_statement_or_block()

        node = {
            "id": self.get_next_node_id(),
            "type": "IfStatement",
            "condition": cond,
            "body": body,
            "line": tok['line']
        }
        if else_body:
            node["elseBody"] = else_body
        return node

    def parse_statement_or_block(self):
        if self.peek() and self.peek()['type'] == 'LBRACE':
            return self.parse_block()
        stmt = self.parse_statement()
        return [stmt] if stmt else []

    def parse_return(self):
        tok = self.match('RETURN')
        val = None
        STATEMENT_BOUNDARIES = {'SEMICOLON', 'RBRACE', 'INT', 'FLOAT', 'CHAR', 'VOID', 'RETURN', 'IF', 'WHILE', 'FOR'}
        if self.peek() and self.peek()['type'] not in STATEMENT_BOUNDARIES:
            val = self.parse_expression()
        self._check_extra_expression_tokens()
        self.expect('SEMICOLON', 'after return statement')
        return {
            "id": self.get_next_node_id(),
            "type": "ReturnStatement",
            "value": val,
            "line": tok['line']
        }

    def parse_block(self):
        if self.match('LBRACE'):
            lbrace_tok = self.tokens[self.pos - 1]
            stmts = []
            while self.peek() and self.peek()['type'] != 'RBRACE':
                old_pos = self.pos
                stmt = self.parse_statement()
                if stmt:
                    stmts.append(stmt)
                elif self.pos == old_pos:
                    tok = self.current_token()
                    if tok and tok['type'] != 'RBRACE':
                        self._report_error(
                            f"Syntax Error at line {tok['line']}:{tok.get('col', 1)}: unexpected token '{tok['value']}'",
                            tok['line'],
                            tok.get('col', 1)
                        )
                        self.pos += 1
                    else:
                        break

            if not self.match('RBRACE'):
                self._report_error(
                    f"Syntax Error: unclosed '{{' at line {lbrace_tok['line']}, expected matching '}}' before end of file",
                    lbrace_tok['line'],
                    lbrace_tok.get('col', 1)
                )
            return stmts
        return []

    def parse_expression(self):
        tree, raw_tokens = self._parse_expr_logical_or()
        if not tree and not raw_tokens:
            return None
        expr_str = " ".join([t['value'] for t in raw_tokens])
        
        return {
            "id": self.get_next_node_id(),
            "type": "Expression",
            "value": expr_str,
            "tree": tree
        }

    def _parse_expr_logical_or(self):
        left, tokens = self._parse_expr_logical_and()
        while left and self.peek() and self.peek()['type'] == 'OR':
            op_tok = self.current_token()
            self.pos += 1
            tokens.append(op_tok)
            right, r_tokens = self._parse_expr_logical_and()
            if not right:
                self._report_error(
                    f"Syntax Error at line {op_tok['line']}:{op_tok.get('col', 1) + 1}: expected expression after '||'",
                    op_tok['line'],
                    op_tok.get('col', 1) + 1
                )
                break
            tokens.extend(r_tokens)
            left = {
                "type": "BinaryOp",
                "op": "||",
                "left": left,
                "right": right
            }
        return left, tokens

    def _parse_expr_logical_and(self):
        left, tokens = self._parse_expr_equality()
        while left and self.peek() and self.peek()['type'] == 'AND':
            op_tok = self.current_token()
            self.pos += 1
            tokens.append(op_tok)
            right, r_tokens = self._parse_expr_equality()
            if not right:
                self._report_error(
                    f"Syntax Error at line {op_tok['line']}:{op_tok.get('col', 1) + 1}: expected expression after '&&'",
                    op_tok['line'],
                    op_tok.get('col', 1) + 1
                )
                break
            tokens.extend(r_tokens)
            left = {
                "type": "BinaryOp",
                "op": "&&",
                "left": left,
                "right": right
            }
        return left, tokens

    def _parse_expr_equality(self):
        left, tokens = self._parse_expr_relational()
        while left and self.peek() and self.peek()['type'] in ['EQ', 'NEQ']:
            op_tok = self.current_token()
            self.pos += 1
            tokens.append(op_tok)
            right, r_tokens = self._parse_expr_relational()
            if not right:
                self._report_error(
                    f"Syntax Error at line {op_tok['line']}:{op_tok.get('col', 1) + 1}: expected expression after '{op_tok['value']}'",
                    op_tok['line'],
                    op_tok.get('col', 1) + 1
                )
                break
            tokens.extend(r_tokens)
            left = {
                "type": "BinaryOp",
                "op": op_tok['value'],
                "left": left,
                "right": right
            }
        return left, tokens

    def _parse_expr_relational(self):
        left, tokens = self._parse_expr_additive()
        while left and self.peek() and self.peek()['type'] in ['LT', 'GT', 'LTE', 'GTE']:
            op_tok = self.current_token()
            self.pos += 1
            tokens.append(op_tok)
            right, r_tokens = self._parse_expr_additive()
            if not right:
                self._report_error(
                    f"Syntax Error at line {op_tok['line']}:{op_tok.get('col', 1) + 1}: expected expression after '{op_tok['value']}'",
                    op_tok['line'],
                    op_tok.get('col', 1) + 1
                )
                break
            tokens.extend(r_tokens)
            left = {
                "type": "BinaryOp",
                "op": op_tok['value'],
                "left": left,
                "right": right
            }
        return left, tokens

    def _parse_expr_additive(self):
        left, tokens = self._parse_expr_multiplicative()
        while left and self.peek() and self.peek()['type'] in ['PLUS', 'MINUS']:
            op_tok = self.current_token()
            self.pos += 1
            tokens.append(op_tok)
            right, r_tokens = self._parse_expr_multiplicative()
            if not right:
                self._report_error(
                    f"Syntax Error at line {op_tok['line']}:{op_tok.get('col', 1) + 1}: expected expression after '{op_tok['value']}'",
                    op_tok['line'],
                    op_tok.get('col', 1) + 1
                )
                break
            tokens.extend(r_tokens)
            left = {
                "type": "BinaryOp",
                "op": op_tok['value'],
                "left": left,
                "right": right
            }
        return left, tokens

    def _parse_expr_multiplicative(self):
        left, tokens = self._parse_expr_primary()
        while left and self.peek() and self.peek()['type'] in ['TIMES', 'DIVIDE', 'MOD']:
            op_tok = self.current_token()
            self.pos += 1
            tokens.append(op_tok)
            right, r_tokens = self._parse_expr_primary()
            if not right:
                self._report_error(
                    f"Syntax Error at line {op_tok['line']}:{op_tok.get('col', 1) + 1}: expected expression after '{op_tok['value']}'",
                    op_tok['line'],
                    op_tok.get('col', 1) + 1
                )
                break
            tokens.extend(r_tokens)
            left = {
                "type": "BinaryOp",
                "op": op_tok['value'],
                "left": left,
                "right": right
            }
        return left, tokens

    def _parse_expr_primary(self):
        tok = self.peek()
        if not tok:
            return None, []

        STATEMENT_BOUNDARIES = {
            'SEMICOLON', 'RBRACE', 'RPAREN', 'COMMA',
            'RETURN', 'INT', 'FLOAT', 'CHAR', 'VOID',
            'IF', 'ELSE', 'WHILE', 'FOR'
        }
        if tok['type'] in STATEMENT_BOUNDARIES:
            # Do NOT consume statement keywords or delimiters as expression tokens!
            return None, []

        if tok['type'] == 'NUMBER':
            self.pos += 1
            return {"type": "Literal", "value": int(tok['value'])}, [tok]
        elif tok['type'] == 'STRING':
            self.pos += 1
            return {"type": "Literal", "value": tok['value']}, [tok]
        elif tok['type'] == 'IDENTIFIER':
            self.pos += 1
            return {"type": "Identifier", "value": tok['value']}, [tok]
        elif tok['type'] == 'LPAREN':
            self.pos += 1  # consume '('
            inside_tree, inside_tokens = self._parse_expr_logical_or()
            rparen = self.expect('RPAREN', 'to close parenthesis')
            all_toks = [tok] + inside_tokens + ([rparen] if rparen else [])
            return inside_tree, all_toks
        elif tok['type'] in ['PLUS', 'MINUS', 'NOT']:
            op_tok = self.current_token()
            self.pos += 1
            operand_tree, operand_tokens = self._parse_expr_primary()
            return {
                "type": "UnaryOp",
                "op": op_tok['value'],
                "operand": operand_tree
            }, [op_tok] + operand_tokens

        # Truly unexpected token in expression
        self._report_error(
            f"Syntax Error at line {tok['line']}:{tok.get('col', 1)}: unexpected token '{tok['value']}' in expression",
            tok['line'],
            tok.get('col', 1)
        )
        self.pos += 1
        return None, []

def parse_code(tokens):
    parser = Parser(tokens)
    ast, symbol_table, errors = parser.parse()
    return ast, errors
