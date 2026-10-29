import { useState, useEffect, useRef } from "react"
import Editor, { type OnMount } from "@monaco-editor/react"
import {
  Play,
  RefreshCw,
  Copy,
  Check,
  AlertCircle,
  AlertTriangle,
  Terminal,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCode,
} from "lucide-react"
import { useCompilerStore, type DiagnosticItem } from "@/store/useCompilerStore"
import { useTheme } from "@/components/theme-provider"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { ScrollArea } from "@/components/ui/scroll-area"

export default function CompilerPage() {
  const {
    sourceCode,
    setSourceCode,
    language,
    isCompiling,
    compile,
    loadExample,
    compileStatus,
    diagnostics,
    logs,
    tokens,
    ast,
    symbolTable,
    semanticErrors,
    intermediateCode,
    quadruples,
    optimizedCode,
    optimizations,
    targetCode,
    machineCode,
    activeTab,
    setActiveTab,
  } = useCompilerStore()

  const { theme } = useTheme()
  const [copiedAsm, setCopiedAsm] = useState(false)
  const [copiedTac, setCopiedTac] = useState(false)
  const [activePreset, setActivePreset] = useState("basic")
  const [icgViewMode, setIcgViewMode] = useState<"tac" | "quads">("tac")
  const [codeGenViewMode, setCodeGenViewMode] = useState<"asm" | "machine">("asm")
  const [bottomTab, setBottomTab] = useState<"problems" | "output">("problems")
  const [bottomPanelOpen, setBottomPanelOpen] = useState(true)

  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)

  // Monaco editor mount handler
  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    updateMarkers(diagnostics)
  }

  // Update VS Code squiggly error markers in Monaco whenever diagnostics change
  const updateMarkers = (diags: DiagnosticItem[]) => {
    if (!editorRef.current || !monacoRef.current) return
    const model = editorRef.current.getModel()
    if (!model) return

    const markers = diags.map((d) => {
      let msg = d.message
      if (d.origin) {
        msg += `\n[Compiler detection: ${d.origin.file}:${d.origin.line} in ${d.origin.function}()]`
      }
      return {
        startLineNumber: d.line || 1,
        startColumn: d.col || 1,
        endLineNumber: d.line || 1,
        endColumn: (d.col || 1) + 6,
        message: msg,
        severity:
          d.severity === "error"
            ? monacoRef.current.MarkerSeverity.Error
            : monacoRef.current.MarkerSeverity.Warning,
      }
    })

    monacoRef.current.editor.setModelMarkers(model, "compiler", markers)
  }

  useEffect(() => {
    updateMarkers(diagnostics)
    // Automatically open bottom panel to Problems if errors were detected
    if (diagnostics.some((d) => d.severity === "error")) {
      setBottomTab("problems")
      setBottomPanelOpen(true)
    }
  }, [diagnostics])

  // Navigate directly to line in editor when clicking a problem
  const jumpToLine = (line: number, col: number = 1) => {
    if (!editorRef.current) return
    editorRef.current.revealLineInCenter(line)
    editorRef.current.setPosition({ lineNumber: line, column: col })
    editorRef.current.focus()
  }

  const handleCopyAsm = () => {
    if (targetCode) {
      navigator.clipboard.writeText(targetCode)
      setCopiedAsm(true)
      setTimeout(() => setCopiedAsm(false), 1500)
    }
  }

  const handleCopyTac = () => {
    if (intermediateCode) {
      navigator.clipboard.writeText(intermediateCode)
      setCopiedTac(true)
      setTimeout(() => setCopiedTac(false), 1500)
    }
  }

  const errorCount = diagnostics.filter((d) => d.severity === "error").length

  const tabs = [
    { id: "tokens", label: "Tokens" },
    { id: "ast", label: "AST" },
    { id: "symbol", label: "Semantic" },
    { id: "icg", label: "3AC" },
    { id: "opt", label: "Optimized" },
    { id: "codegen", label: "Assembly" },
  ]

  const presets = [
    { id: "basic", label: "Basic" },
    { id: "optimization", label: "Optimization" },
    { id: "loop", label: "Loop" },
    { id: "conditional", label: "Branching" },
  ]

  return (
    <div className="h-full flex flex-col bg-background text-foreground overflow-hidden">
      {/* Calm Single Toolbar */}
      <div className="h-10 border-b border-border px-3 flex items-center justify-between shrink-0 bg-background text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 font-mono text-muted-foreground text-xs">
            <FileCode className="h-3.5 w-3.5" />
            <span>main.c</span>
          </div>

          <div className="flex items-center gap-1 border-l border-border pl-3">
            <span className="text-[11px] text-muted-foreground mr-1">Presets:</span>
            {presets.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setActivePreset(p.id)
                  loadExample(p.id)
                  setTimeout(compile, 50)
                }}
                className={`px-2 py-0.5 rounded text-xs transition-colors ${
                  activePreset === p.id
                    ? "bg-secondary text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Right side status & action */}
        <div className="flex items-center gap-3">
          {compileStatus === "error" && (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-rose-500/10 text-rose-700 dark:text-rose-300 font-mono text-[11px]">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              <span>
                Build Failed ({errorCount} error{errorCount !== 1 ? "s" : ""})
              </span>
            </div>
          )}

          {compileStatus === "success" && (
            <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-mono text-[11px]">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span>Build Succeeded</span>
            </div>
          )}

          <button
            onClick={compile}
            disabled={isCompiling}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-foreground text-background font-medium hover:opacity-90 disabled:opacity-50 transition-opacity text-xs"
          >
            {isCompiling ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : (
              <Play className="h-3 w-3 fill-current" />
            )}
            <span>{isCompiling ? "Running..." : "Run"}</span>
          </button>
        </div>
      </div>

      {/* Main Split Panels */}
      <div className="flex-1 flex overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* Left: Code Editor with squiggly error markers */}
          <ResizablePanel defaultSize={48} minSize={25}>
            <div className="h-full w-full">
              <Editor
                height="100%"
                language={language}
                theme={theme === "dark" ? "vs-dark" : "light"}
                value={sourceCode}
                onMount={handleEditorMount}
                onChange={(val) => setSourceCode(val || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                  lineNumbers: "on",
                  glyphMargin: true,
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  padding: { top: 12, bottom: 12 },
                }}
              />
            </div>
          </ResizablePanel>

          <ResizableHandle className="bg-border w-px hover:w-1 hover:bg-muted-foreground/30 transition-all" />

          {/* Right: Compiler Output */}
          <ResizablePanel defaultSize={52} minSize={30}>
            <div className="h-full flex flex-col bg-background overflow-hidden">
              {/* Clean Output Tabs */}
              <div className="h-10 border-b border-border px-3 flex items-center justify-between shrink-0 bg-background">
                <div className="flex items-center gap-1">
                  {tabs.map((tab) => {
                    const isActive = activeTab === tab.id
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-2.5 py-1 rounded text-xs transition-colors ${
                          isActive
                            ? "bg-secondary text-foreground font-medium"
                            : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                        }`}
                      >
                        {tab.label}
                      </button>
                    )
                  })}
                </div>

                {/* Tab-specific actions */}
                {activeTab === "icg" && intermediateCode && (
                  <div className="flex items-center gap-2 text-xs">
                    <button
                      onClick={() => setIcgViewMode(icgViewMode === "tac" ? "quads" : "tac")}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      {icgViewMode === "tac" ? "View Table" : "View TAC"}
                    </button>
                    <button
                      onClick={handleCopyTac}
                      className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
                    >
                      {copiedTac ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                      <span>{copiedTac ? "Copied" : "Copy"}</span>
                    </button>
                  </div>
                )}

                {activeTab === "codegen" && targetCode && (
                  <div className="flex items-center gap-2 text-xs">
                    <button
                      onClick={() => setCodeGenViewMode(codeGenViewMode === "asm" ? "machine" : "asm")}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      {codeGenViewMode === "asm" ? "View Bytes" : "View Asm"}
                    </button>
                    <button
                      onClick={handleCopyAsm}
                      className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
                    >
                      {copiedAsm ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                      <span>{copiedAsm ? "Copied" : "Copy"}</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Tab Contents */}
              <div className="flex-1 overflow-hidden relative">
                {/* 1. TOKENS */}
                {activeTab === "tokens" && (
                  <ScrollArea className="h-full p-4">
                    {tokens.length > 0 ? (
                      <table className="w-full text-xs font-mono">
                        <thead>
                          <tr className="border-b border-border text-muted-foreground text-left">
                            <th className="pb-2 w-16">Line</th>
                            <th className="pb-2 w-32">Type</th>
                            <th className="pb-2">Value</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                          {tokens.map((t, i) => (
                            <tr key={i} className="hover:bg-muted/30">
                              <td className="py-1 text-muted-foreground">{t.line}</td>
                              <td className="py-1 text-muted-foreground">{t.type}</td>
                              <td className="py-1 text-foreground font-medium">{t.value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="text-xs text-muted-foreground py-8 text-center">No tokens generated.</div>
                    )}
                  </ScrollArea>
                )}

                {/* 2. AST */}
                {activeTab === "ast" && (
                  <ScrollArea className="h-full p-4 font-mono text-xs">
                    {ast ? (
                      <pre className="text-muted-foreground leading-relaxed">
                        {JSON.stringify(ast, null, 2)}
                      </pre>
                    ) : (
                      <div className="text-xs text-muted-foreground py-8 text-center">
                        No AST constructed. {compileStatus === "error" && "Fix syntax errors in the editor."}
                      </div>
                    )}
                  </ScrollArea>
                )}

                {/* 3. SEMANTIC */}
                {activeTab === "symbol" && (
                  <ScrollArea className="h-full p-4 text-xs font-mono">
                    {semanticErrors.length > 0 && (
                      <div className="mb-4 p-3 rounded border border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300">
                        <div className="font-semibold mb-1">Semantic Errors:</div>
                        <ul className="list-disc list-inside space-y-0.5">
                          {semanticErrors.map((err, i) => (
                            <li key={i}>{typeof err === "string" ? err : err.message}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {symbolTable && symbolTable.length > 0 ? (
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-border text-muted-foreground text-left">
                            <th className="pb-2">Identifier</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Scope</th>
                            <th className="pb-2">Offset</th>
                            <th className="pb-2 w-14">Line</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                          {symbolTable.map((s, i) => (
                            <tr key={i} className="hover:bg-muted/30">
                              <td className="py-1.5 font-semibold text-foreground">{s.name}</td>
                              <td className="py-1.5 text-muted-foreground">{s.type}</td>
                              <td className="py-1.5 text-muted-foreground">{s.scope}</td>
                              <td className="py-1.5 text-muted-foreground">{s.offset || "-"}</td>
                              <td className="py-1.5 text-muted-foreground">{s.line}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="text-xs text-muted-foreground py-8 text-center">
                        {compileStatus === "error"
                          ? "Semantic table could not be generated due to earlier compilation errors."
                          : "No symbols resolved."}
                      </div>
                    )}
                  </ScrollArea>
                )}

                {/* 4. THREE-ADDRESS CODE (ICG) */}
                {activeTab === "icg" && (
                  <ScrollArea className="h-full p-4 font-mono text-xs">
                    {intermediateCode ? (
                      icgViewMode === "tac" ? (
                        <div className="space-y-0.5 leading-relaxed">
                          {intermediateCode.split("\n").map((line, i) => (
                            <div key={i} className="flex gap-4 hover:bg-muted/30 px-1 py-0.5 rounded">
                              <span className="w-6 text-right text-muted-foreground/50 select-none">{i + 1}</span>
                              <span className="text-foreground">{line}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground text-left">
                              <th className="pb-2 w-10">#</th>
                              <th className="pb-2 w-24">Opcode</th>
                              <th className="pb-2">Arg 1</th>
                              <th className="pb-2">Arg 2</th>
                              <th className="pb-2">Result</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/40">
                            {quadruples.map((q, i) => (
                              <tr key={i} className="hover:bg-muted/30">
                                <td className="py-1 text-muted-foreground/60">{q.index}</td>
                                <td className="py-1 font-semibold">{q.op}</td>
                                <td className="py-1 text-muted-foreground">{q.arg1}</td>
                                <td className="py-1 text-muted-foreground">{q.arg2}</td>
                                <td className="py-1 text-foreground font-medium">{q.result}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )
                    ) : (
                      <div className="text-xs text-muted-foreground py-8 text-center">
                        {compileStatus === "error"
                          ? "Pipeline halted. Fix syntax & semantic errors to generate intermediate code."
                          : "No 3AC generated yet."}
                      </div>
                    )}
                  </ScrollArea>
                )}

                {/* 5. OPTIMIZATION */}
                {activeTab === "opt" && (
                  <ScrollArea className="h-full p-4 font-mono text-xs">
                    {compileStatus === "error" ? (
                      <div className="text-xs text-muted-foreground py-8 text-center">
                        Optimization pass halted due to compilation errors.
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {optimizations.length > 0 && (
                          <div className="p-3 rounded border border-border bg-secondary/30">
                            <div className="font-semibold text-foreground mb-2 text-xs">
                              Optimizations Applied ({optimizations.length}):
                            </div>
                            <ul className="space-y-1 text-muted-foreground text-[11px]">
                              {optimizations.map((item, idx) => (
                                <li key={idx} className="flex gap-2">
                                  <span className="text-foreground font-semibold">[{item.pass}]</span>
                                  <span>{item.detail}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3 rounded border border-border bg-secondary/10">
                            <div className="text-[11px] font-semibold text-muted-foreground mb-2">Original (3AC)</div>
                            <pre className="text-xs text-muted-foreground overflow-x-auto leading-relaxed">
                              {intermediateCode || "// None"}
                            </pre>
                          </div>
                          <div className="p-3 rounded border border-border bg-secondary/20">
                            <div className="text-[11px] font-semibold text-foreground mb-2">Optimized (3AC)</div>
                            <pre className="text-xs text-foreground overflow-x-auto leading-relaxed">
                              {optimizedCode || "// None"}
                            </pre>
                          </div>
                        </div>
                      </div>
                    )}
                  </ScrollArea>
                )}

                {/* 6. TARGET CODEGEN */}
                {activeTab === "codegen" && (
                  <ScrollArea className="h-full p-4 font-mono text-xs">
                    {compileStatus === "error" ? (
                      <div className="text-xs text-muted-foreground py-8 text-center">
                        Target code generation halted due to compilation errors.
                      </div>
                    ) : targetCode ? (
                      codeGenViewMode === "asm" ? (
                        <div className="space-y-0.5 leading-relaxed">
                          {targetCode.split("\n").map((line, i) => (
                            <div key={i} className="flex gap-4 hover:bg-muted/30 px-1 py-0.5 rounded">
                              <span className="w-6 text-right text-muted-foreground/50 select-none">{i + 1}</span>
                              <span
                                className={
                                  line.trim().startsWith("#") ? "text-muted-foreground italic" : "text-foreground"
                                }
                              >
                                {line}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground text-left">
                              <th className="pb-2 w-24">Address</th>
                              <th className="pb-2 w-32">Machine Bytes</th>
                              <th className="pb-2">Assembly</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/40">
                            {machineCode.map((m, i) => (
                              <tr key={i} className="hover:bg-muted/30">
                                <td className="py-1 text-muted-foreground">{m.address}</td>
                                <td className="py-1 text-muted-foreground font-semibold">{m.bytes}</td>
                                <td className="py-1 text-foreground">{m.assembly}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )
                    ) : (
                      <div className="text-xs text-muted-foreground py-8 text-center">No target code generated.</div>
                    )}
                  </ScrollArea>
                )}
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* VS Code-style Bottom Diagnostics / Problems Panel */}
      <div className="border-t border-border bg-background shrink-0 flex flex-col transition-all">
        {/* Panel Header Bar */}
        <div className="h-7 px-3 border-b border-border/80 flex items-center justify-between text-xs bg-muted/20 select-none">
          <div className="flex items-center gap-1 font-mono">
            <button
              onClick={() => {
                setBottomTab("problems")
                setBottomPanelOpen(true)
              }}
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] transition-colors ${
                bottomPanelOpen && bottomTab === "problems"
                  ? "bg-secondary text-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>Problems</span>
              {diagnostics.length > 0 && (
                <span
                  className={`px-1 rounded text-[10px] ${
                    errorCount > 0
                      ? "bg-rose-500/20 text-rose-700 dark:text-rose-300 font-bold"
                      : "bg-amber-500/20 text-amber-800 dark:text-amber-300"
                  }`}
                >
                  {diagnostics.length}
                </span>
              )}
            </button>

            <button
              onClick={() => {
                setBottomTab("output")
                setBottomPanelOpen(true)
              }}
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] transition-colors ${
                bottomPanelOpen && bottomTab === "output"
                  ? "bg-secondary text-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Terminal className="h-3 w-3" />
              <span>Console / Output</span>
            </button>
          </div>

          <button
            onClick={() => setBottomPanelOpen(!bottomPanelOpen)}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors"
            title={bottomPanelOpen ? "Collapse panel" : "Expand panel"}
          >
            {bottomPanelOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
          </button>
        </div>

        {/* Panel Drawer Contents */}
        {bottomPanelOpen && (
          <div className="h-40 overflow-hidden bg-background font-mono text-xs">
            {bottomTab === "problems" && (
              <ScrollArea className="h-full p-2">
                {diagnostics.length > 0 ? (
                  <div className="space-y-1">
                    {diagnostics.map((d, i) => (
                      <button
                        key={i}
                        onClick={() => jumpToLine(d.line, d.col)}
                        className="w-full text-left flex items-start gap-2.5 px-2.5 py-1.5 rounded hover:bg-muted/40 transition-colors group"
                      >
                        {d.severity === "error" ? (
                          <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                        )}
                        <span className="text-foreground flex-1 leading-relaxed">
                          {d.message}
                        </span>
                        <div className="flex items-center gap-2 shrink-0 text-muted-foreground text-[11px]">
                          {d.origin && (
                            <span
                              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-secondary/80 text-foreground/80 border border-border/50 font-mono"
                              title={`Compiler check location: ${d.origin.file}:${d.origin.line} in ${d.origin.function}()${d.origin.caller ? ` (called by ${d.origin.caller}())` : ''}`}
                            >
                              <span className="text-muted-foreground/70">at:</span>
                              <span className="font-semibold text-foreground">{d.origin.file}:{d.origin.line}</span>
                              <span className="opacity-40">·</span>
                              <span>{d.origin.function}()</span>
                            </span>
                          )}
                          {d.phase && (
                            <span className="bg-secondary/60 px-1.5 py-0.5 rounded text-[10px]">
                              {d.phase}
                            </span>
                          )}
                          <span className="text-muted-foreground/70 group-hover:text-foreground underline underline-offset-2">
                            main.c [{d.line}:{d.col || 1}]
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-xs py-8">
                    No problems have been detected in the workspace.
                  </div>
                )}
              </ScrollArea>
            )}

            {bottomTab === "output" && (
              <ScrollArea className="h-full p-3 font-mono text-[11px]">
                {logs.map((log, i) => (
                  <div
                    key={i}
                    className={`py-0.5 leading-relaxed ${
                      log.includes("✗") || log.includes("Error")
                        ? "text-rose-600 dark:text-rose-400 font-semibold"
                        : log.includes("⚠") || log.includes("Warning")
                        ? "text-amber-600 dark:text-amber-400"
                        : log.includes("✓")
                        ? "text-emerald-600 dark:text-emerald-400 font-medium"
                        : "text-muted-foreground"
                    }`}
                  >
                    {log}
                  </div>
                ))}
              </ScrollArea>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
