import sys
import os

def record_diagnostic(
    message: str,
    line: int,
    col: int = 1,
    severity: str = "error",
    phase: str = "Compiler",
    depth: int = 1
) -> dict:
    """
    Creates a structured diagnostic entry with automatic introspected
    origin metadata (file, line number, and function) from the compiler codebase.
    """
    frame = sys._getframe(depth)
    file_name = os.path.basename(frame.f_code.co_filename)
    func_name = frame.f_code.co_name
    src_line = frame.f_lineno
    
    caller_name = None
    if frame.f_back:
        c_name = frame.f_back.f_code.co_name
        if c_name not in ['<module>', 'parse', 'analyze', '_analyze_node', 'parse_statement', 'parse_code', 'tokenize_code']:
            caller_name = c_name

    return {
        "line": line,
        "col": col,
        "message": message,
        "severity": severity,
        "phase": phase,
        "origin": {
            "file": file_name,
            "line": src_line,
            "function": func_name,
            "caller": caller_name
        }
    }

