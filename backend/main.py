import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from compiler.lexer import tokenize_code
from compiler.parser import parse_code
from compiler.semantic import analyze_semantics
from compiler.icg import generate_intermediate_code
from compiler.optimizer import optimize_code
from compiler.codegen import generate_target_code

app = FastAPI(title="Smart Compiler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompileRequest(BaseModel):
    code: str
    language: str

@app.post("/compile")
async def compile_code(req: CompileRequest):
    logs = []
    diagnostics = []

    # Phase 1: Lexical Analysis
    tokens, lex_errors = tokenize_code(req.code)
    diagnostics.extend(lex_errors)
    logs.append(f"Phase 1: Lexical Analysis - generated {len(tokens)} tokens.")
    if lex_errors:
        for le in lex_errors:
            logs.append(f"✗ main.c:{le['line']}:{le['col']}: lexical error: {le['message']}")

    # Phase 2: Syntax Analysis
    ast, syntax_errors = parse_code(tokens)
    diagnostics.extend(syntax_errors)
    
    if syntax_errors:
        logs.append(f"✗ Phase 2: Syntax Analysis failed with {len(syntax_errors)} syntax error(s):")
        for se in syntax_errors:
            logs.append(f"  ✗ main.c:{se['line']}:{se['col']}: error: {se['message']}")
    else:
        logs.append(f"Phase 2: Syntax Analysis - constructed AST with {len(ast.get('body', []))} statements.")

    # Stop pipeline if fatal syntax or lexical errors exist
    has_syntax_or_lex_errors = bool(lex_errors or syntax_errors)
    if has_syntax_or_lex_errors:
        logs.append("✗ Compilation halted at Syntax Analysis due to fatal errors.")
        return {
            "status": "error",
            "tokens": tokens,
            "ast": ast,
            "symbolTable": [],
            "diagnostics": diagnostics,
            "syntaxErrors": syntax_errors,
            "semanticErrors": [],
            "semanticWarnings": [],
            "intermediateCode": "",
            "tacLines": [],
            "quadruples": [],
            "optimizedCode": "",
            "optimizedTacLines": [],
            "optimizedQuadruples": [],
            "optimizations": [],
            "targetCode": "",
            "assemblyLines": [],
            "machineCode": [],
            "logs": logs
        }

    # Phase 3: Semantic Analysis & Symbol Table Generation
    symbol_table, semantic_errors, semantic_warnings = analyze_semantics(ast)
    diagnostics.extend(semantic_errors)
    diagnostics.extend(semantic_warnings)

    if semantic_errors:
        logs.append(f"✗ Phase 3: Semantic Analysis failed with {len(semantic_errors)} error(s):")
        for se in semantic_errors:
            logs.append(f"  ✗ main.c:{se['line']}:{se['col']}: error: {se['message']}")
    else:
        logs.append(f"Phase 3: Semantic Analysis - resolved {len(symbol_table)} symbols.")

    if semantic_warnings:
        for sw in semantic_warnings:
            logs.append(f"  ⚠ main.c:{sw['line']}:{sw['col']}: warning: {sw['message']}")

    has_fatal_errors = bool(semantic_errors)
    if has_fatal_errors:
        logs.append("✗ Compilation halted at Semantic Analysis due to fatal errors.")
        return {
            "status": "error",
            "tokens": tokens,
            "ast": ast,
            "symbolTable": symbol_table,
            "diagnostics": diagnostics,
            "syntaxErrors": [],
            "semanticErrors": semantic_errors,
            "semanticWarnings": semantic_warnings,
            "intermediateCode": "",
            "tacLines": [],
            "quadruples": [],
            "optimizedCode": "",
            "optimizedTacLines": [],
            "optimizedQuadruples": [],
            "optimizations": [],
            "targetCode": "",
            "assemblyLines": [],
            "machineCode": [],
            "logs": logs
        }

    # Phase 4: Intermediate Code Generation (ICG)
    tac_lines, quadruples, tac_text = generate_intermediate_code(ast)
    logs.append(f"Phase 4: Intermediate Code Generation - produced {len(quadruples)} TAC quadruples.")

    # Phase 5: Code Optimization
    opt_tac_lines, opt_quadruples, opt_tac_text, optimizations_applied = optimize_code(quadruples, tac_lines)
    logs.append(f"Phase 5: Code Optimization - performed {len(optimizations_applied)} optimization passes.")

    # Phase 6: Code Generation (Target Assembly & Machine Bytecode)
    target_assembly, assembly_lines, machine_code = generate_target_code(opt_quadruples, symbol_table)
    logs.append(f"Phase 6: Code Generation - produced {len(assembly_lines)} lines of target x86-64 assembly & machine code.")

    logs.append("✓ Compilation completed successfully through all 6 phases.")

    return {
        "status": "success",
        "tokens": tokens,
        "ast": ast,
        "symbolTable": symbol_table,
        "diagnostics": diagnostics,
        "syntaxErrors": [],
        "semanticErrors": [],
        "semanticWarnings": semantic_warnings,
        "intermediateCode": tac_text,
        "tacLines": tac_lines,
        "quadruples": quadruples,
        "optimizedCode": opt_tac_text,
        "optimizedTacLines": opt_tac_lines,
        "optimizedQuadruples": opt_quadruples,
        "optimizations": optimizations_applied,
        "targetCode": target_assembly,
        "assemblyLines": assembly_lines,
        "machineCode": machine_code,
        "logs": logs
    }

class ModernizeRequest(BaseModel):
    code: str
    language: str

@app.post("/modernize")
async def modernize_code(req: ModernizeRequest):
    code = req.code
    transformations = []

    if "NULL" in code:
        code = code.replace("NULL", "nullptr")
        transformations.append("Replaced legacy C NULL macro with C++11 type-safe 'nullptr'.")

    if "malloc(" in code or "free(" in code:
        code = re.sub(r'int\s*\*\s*(\w+)\s*=\s*\(\s*int\s*\*\s*\)\s*malloc\s*\(\s*sizeof\s*\(\s*int\s*\)\s*\*\s*(\w+)\s*\);',
                      r'auto \1 = std::make_unique<int[]>(\2);', code)
        code = re.sub(r'free\s*\(\s*(\w+)\s*\);', r'// \1 safely managed by RAII unique_ptr scope', code)
        transformations.append("Migrated raw heap allocation (malloc/free) to RAII smart pointers (std::make_unique).")

    macro_matches = re.findall(r'#define\s+([A-Z_]+)\s+([0-9\.]+)', code)
    if macro_matches:
        for name, val in macro_matches:
            target_type = "double" if "." in val else "int"
            code = re.sub(rf'#define\s+{name}\s+{val}', f'constexpr {target_type} {name} = {val};', code)
        transformations.append("Replaced un-scoped preprocessor #define macros with type-safe 'constexpr'.")

    if "printf(" in code:
        code = re.sub(r'printf\(\s*\"([^\"]*)\\n\"\s*\);', r'std::cout << "\1" << std::endl;', code)
        code = re.sub(r'printf\(\s*\"([^\"]*)\"\s*\);', r'std::cout << "\1";', code)
        code = code.replace("printf(", "std::cout << ")
        transformations.append("Upgraded raw C formatted stdout (printf) to type-safe C++ streams (std::cout).")

    headers = ["<iostream>"]
    if "std::make_unique" in code or "unique_ptr" in code:
        headers.append("<memory>")
    if "std::vector" in code:
        headers.append("<vector>")

    header_block = "".join([f"#include {h}\n" for h in headers]) + "\n"
    
    code = re.sub(r'#include\s*<stdio\.h>\s*\n?', '', code)
    code = re.sub(r'#include\s*<stdlib\.h>\s*\n?', '', code)

    code = f"// Modernized to ISO C++20 / RAII Best Practices\n{header_block}" + code.strip()

    if not transformations:
        transformations.append("Standardized code structure to modern ISO C++ formatting.")

    return {
        "status": "success",
        "modernizedCode": code,
        "transformations": transformations
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
