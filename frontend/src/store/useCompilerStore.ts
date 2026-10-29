import { create } from 'zustand'

export interface Token {
  type: string
  value: string
  line: number
  col?: number
}

export interface Quadruple {
  index: number
  op: string
  arg1: string
  arg2: string
  result: string
}

export interface OptimizationItem {
  pass: string
  detail: string
  result?: string
  value?: string
}

export interface MachineCodeItem {
  address: string
  bytes: string
  assembly: string
  description: string
}

export interface DiagnosticOrigin {
  file: string
  line: number
  function: string
  caller?: string | null
}

export interface DiagnosticItem {
  line: number
  col?: number
  message: string
  severity: 'error' | 'warning'
  phase?: string
  origin?: DiagnosticOrigin
}

export interface CompilerState {
  sourceCode: string
  setSourceCode: (code: string) => void
  language: string
  setLanguage: (lang: string) => void
  
  compileStatus: 'idle' | 'success' | 'error'
  diagnostics: DiagnosticItem[]

  // Phase 1: Lexical Analysis
  tokens: Token[]
  
  // Phase 2: Syntax Analysis
  ast: any | null
  
  // Phase 3: Semantic Analysis & Symbol Table
  symbolTable: any[] | null
  semanticErrors: any[]
  semanticWarnings: any[]
  
  // Phase 4: Intermediate Code Generation (ICG)
  intermediateCode: string
  tacLines: string[]
  quadruples: Quadruple[]
  
  // Phase 5: Code Optimization
  optimizedCode: string
  optimizedTacLines: string[]
  optimizedQuadruples: Quadruple[]
  optimizations: OptimizationItem[]
  
  // Phase 6: Target Code Generation & Machine Code
  targetCode: string
  assemblyLines: string[]
  machineCode: MachineCodeItem[]
  
  // Active UI tab
  activeTab: string
  setActiveTab: (tab: string) => void
  
  logs: string[]
  isCompiling: boolean
  
  compile: () => Promise<void>
  loadExample: (key: string) => void
}

const SAMPLE_CODES: Record<string, string> = {
  basic: `int main() {
  int a = 5 + 3;
  int b = a * 2;
  return b;
}`,
  optimization: `int main() {
  int a = 10 + 20;
  int b = a * 1;
  int c = a + 5;
  return b;
  int dead = 99;
}`,
  loop: `int main() {
  int count = 0;
  int sum = 0;
  while (count < 5) {
    sum = sum + count;
    count = count + 1;
  }
  return sum;
}`,
  conditional: `int main() {
  int x = 15;
  int y = 0;
  if (x > 10) {
    y = x * 2;
  } else {
    y = x - 5;
  }
  return y;
}`
};

export const useCompilerStore = create<CompilerState>((set, get) => ({
  sourceCode: SAMPLE_CODES.basic,
  setSourceCode: (code) => set({ sourceCode: code }),
  language: 'c',
  setLanguage: (lang) => set({ language: lang }),
  
  compileStatus: 'idle',
  diagnostics: [],

  tokens: [],
  ast: null,
  symbolTable: null,
  semanticErrors: [],
  semanticWarnings: [],
  intermediateCode: '',
  tacLines: [],
  quadruples: [],
  optimizedCode: '',
  optimizedTacLines: [],
  optimizedQuadruples: [],
  optimizations: [],
  targetCode: '',
  assemblyLines: [],
  machineCode: [],
  
  activeTab: 'tokens',
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  logs: ['Compiler pipeline ready.'],
  isCompiling: false,
  
  loadExample: (key: string) => {
    if (SAMPLE_CODES[key]) {
      set({ sourceCode: SAMPLE_CODES[key], diagnostics: [], compileStatus: 'idle' });
    }
  },

  compile: async () => {
    set({ isCompiling: true, logs: ['[Compiler] Invoking 6-phase pipeline...'] })
    
    try {
      const response = await fetch('http://localhost:8000/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: get().sourceCode,
          language: get().language
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      set({
        compileStatus: data.status,
        diagnostics: data.diagnostics || [],
        tokens: data.tokens || [],
        ast: data.ast || null,
        symbolTable: data.symbolTable || [],
        semanticErrors: data.semanticErrors || [],
        semanticWarnings: data.semanticWarnings || [],
        intermediateCode: data.intermediateCode || '',
        tacLines: data.tacLines || [],
        quadruples: data.quadruples || [],
        optimizedCode: data.optimizedCode || '',
        optimizedTacLines: data.optimizedTacLines || [],
        optimizedQuadruples: data.optimizedQuadruples || [],
        optimizations: data.optimizations || [],
        targetCode: data.targetCode || '',
        assemblyLines: data.assemblyLines || [],
        machineCode: data.machineCode || [],
        logs: data.logs || []
      });
      
    } catch (error: any) {
      set({
        compileStatus: 'error',
        diagnostics: [{
          line: 1,
          message: `Network/Backend Error: ${error.message}. Is backend server running on port 8000?`,
          severity: 'error'
        }],
        logs: [`✗ Compilation failed: ${error.message}`]
      });
    } finally {
      set({ isCompiling: false })
    }
  }
}))
