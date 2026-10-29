import { useState } from "react"
import Editor from "@monaco-editor/react"
import { Copy, Check, RefreshCw } from "lucide-react"
import { useTheme } from "@/components/theme-provider"

const PRESETS = [
  {
    id: "io",
    label: "I/O (printf)",
    code: `#include <stdio.h>

int main() {
    printf("Hello from C\\n");
    return 0;
}`,
  },
  {
    id: "memory",
    label: "Memory (malloc)",
    code: `#include <stdio.h>
#include <stdlib.h>

int main() {
    int* data = (int*)malloc(sizeof(int) * 16);
    data[0] = 100;
    free(data);
    return 0;
}`,
  },
  {
    id: "macros",
    label: "Macros (#define)",
    code: `#define BUFFER_SIZE 512
#define FACTOR 2.5

int main() {
    int size = BUFFER_SIZE;
    return 0;
}`,
  },
]

export default function ModernizerPage() {
  const { theme } = useTheme()
  const [legacyCode, setLegacyCode] = useState(PRESETS[0].code)
  const [modernCode, setModernCode] = useState("")
  const [transformations, setTransformations] = useState<string[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [activePreset, setActivePreset] = useState("io")

  const handleModernize = async () => {
    setIsProcessing(true)
    try {
      const response = await fetch("http://localhost:8000/modernize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: legacyCode, language: "c" }),
      })
      const data = await response.json()
      if (data.status === "success") {
        setModernCode(data.modernizedCode)
        setTransformations(data.transformations || [])
      }
    } catch (e) {
      console.error(e)
      setModernCode("// Error connecting to modernizer backend.")
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCopy = () => {
    if (modernCode) {
      navigator.clipboard.writeText(modernCode)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  return (
    <div className="h-full flex flex-col bg-background text-foreground overflow-hidden">
      {/* Calm Single Toolbar */}
      <div className="h-10 border-b border-border px-3 flex items-center justify-between shrink-0 bg-background text-xs">
        <div className="flex items-center gap-1">
          <span className="text-[11px] text-muted-foreground mr-1">Presets:</span>
          {PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setActivePreset(p.id)
                setLegacyCode(p.code)
                setModernCode("")
                setTransformations([])
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

        <div className="flex items-center gap-2">
          {modernCode && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground text-xs"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
              <span>{copied ? "Copied" : "Copy C++"}</span>
            </button>
          )}

          <button
            onClick={handleModernize}
            disabled={isProcessing}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-foreground text-background font-medium hover:opacity-90 disabled:opacity-50 transition-opacity text-xs"
          >
            {isProcessing && <RefreshCw className="h-3 w-3 animate-spin" />}
            <span>{isProcessing ? "Modernizing..." : "Modernize"}</span>
          </button>
        </div>
      </div>

      {/* Side-by-side Editors */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left: C Code */}
        <div className="w-full md:w-1/2 flex flex-col border-b md:border-b-0 md:border-r border-border">
          <div className="h-7 px-3 border-b border-border bg-secondary/10 flex items-center text-[11px] font-mono text-muted-foreground">
            Legacy C
          </div>
          <div className="flex-1">
            <Editor
              height="100%"
              language="c"
              theme={theme === "dark" ? "vs-dark" : "light"}
              value={legacyCode}
              onChange={(val) => setLegacyCode(val || "")}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                padding: { top: 10, bottom: 10 },
              }}
            />
          </div>
        </div>

        {/* Right: Modern C++ */}
        <div className="w-full md:w-1/2 flex flex-col bg-background">
          <div className="h-7 px-3 border-b border-border bg-secondary/10 flex items-center text-[11px] font-mono text-muted-foreground">
            Modern C++ (RAII)
          </div>
          <div className="flex-1">
            <Editor
              height="100%"
              language="cpp"
              theme={theme === "dark" ? "vs-dark" : "light"}
              value={modernCode || "// Click 'Modernize' to convert to modern C++"}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                lineNumbers: "on",
                readOnly: true,
                scrollBeyondLastLine: false,
                automaticLayout: true,
                padding: { top: 10, bottom: 10 },
              }}
            />
          </div>
        </div>
      </div>

      {/* Subtle transformation summary footer if transformations occurred */}
      {transformations.length > 0 && (
        <div className="border-t border-border px-3 py-2 bg-secondary/10 text-xs font-mono text-muted-foreground flex items-center gap-2">
          <span className="font-semibold text-foreground">Transformations:</span>
          <span>{transformations.join(" • ")}</span>
        </div>
      )}
    </div>
  )
}
