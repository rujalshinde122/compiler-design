# pyrefly: ignore [missing-import]
import ply.lex as lex
from compiler.diagnostics import record_diagnostic

# List of token names
tokens = (
    'NUMBER',
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    'MOD',
    'LPAREN',
    'RPAREN',
    'IDENTIFIER',
    'EQ',
    'NEQ',
    'LTE',
    'GTE',
    'LT',
    'GT',
    'AND',
    'OR',
    'NOT',
    'ASSIGN',
    'SEMICOLON',
    'LBRACE',
    'RBRACE',
    'COMMA',
    'STRING',
)

# Reserved keywords
reserved = {
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'return': 'RETURN',
    'int': 'INT',
    'float': 'FLOAT',
    'char': 'CHAR',
    'void': 'VOID',
    'for': 'FOR'
}

tokens = tokens + tuple(reserved.values())

# Regular expression rules for multi-character tokens
t_EQ      = r'=='
t_NEQ     = r'!='
t_LTE     = r'<='
t_GTE     = r'>='
t_AND     = r'&&'
t_OR      = r'\|\|'

# Regular expression rules for simple tokens
t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_MOD     = r'%'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACE  = r'\{'
t_RBRACE  = r'\}'
t_ASSIGN  = r'='
t_LT      = r'<'
t_GT      = r'>'
t_NOT     = r'!'
t_SEMICOLON = r';'
t_COMMA   = r','
t_STRING  = r'\"([^\\\n]|(\\.))*?\"'

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'IDENTIFIER')
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)    
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore  = ' \t'

lex_errors = []

def t_error(t):
    # Calculate column
    line_start = t.lexer.lexdata.rfind('\n', 0, t.lexpos) + 1
    col = (t.lexpos - line_start) + 1
    lex_errors.append(record_diagnostic(
        message=f"Illegal character '{t.value[0]}'",
        line=t.lineno,
        col=col,
        severity="error",
        phase="Lexical Analysis",
        depth=1
    ))
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()

def tokenize_code(code: str):
    global lex_errors
    lex_errors = []
    
    # Crucial: Reset line number to 1 on every run!
    lexer.lineno = 1
    lexer.input(code)
    
    token_list = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        
        line_start = code.rfind('\n', 0, tok.lexpos) + 1
        col = (tok.lexpos - line_start) + 1
        
        token_list.append({
            "type": tok.type,
            "value": str(tok.value),
            "line": tok.lineno,
            "col": col,
            "pos": tok.lexpos,
            "len": len(str(tok.value))
        })
        
    return token_list, lex_errors
