import { useState, useMemo } from "react"
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  MarkerType,
} from "reactflow"
import "reactflow/dist/style.css"
import { useCompilerStore } from "@/store/useCompilerStore"
import { useTheme } from "@/components/theme-provider"

interface TreeNode {
  id: string
  title: string
  subtitle?: string
  children: TreeNode[]
  width: number
  x: number
  y: number
}

export default function VisualizationsPage() {
  const { ast, tacLines, quadruples } = useCompilerStore()
  const { theme } = useTheme()
  const [viewType, setViewType] = useState<"ast" | "cfg">("ast")

  // Generate AST Graph with tidy, non-overlapping tree layout
  const { astNodes, astEdges } = useMemo(() => {
    if (!ast) return { astNodes: [], astEdges: [] }

    let idCounter = 0

    // Step 1: Build a clean normalized tree structure
    const buildTree = (node: any): TreeNode | null => {
      if (!node || typeof node !== "object") return null
      const currentId = `ast_node_${++idCounter}`

      const nodeType = node.type || "ASTNode"
      let subtitle = ""
      if (node.type === "FunctionDeclaration") {
        subtitle = `${node.returnType || "void"} ${node.name || "main"}()`
      } else if (node.type === "VariableDeclaration") {
        subtitle = `${node.dataType || ""} ${node.identifier || ""}`.trim()
      } else if (node.type === "Assignment") {
        subtitle = `${node.identifier || ""} =`
      } else if (node.type === "ReturnStatement") {
        subtitle = "return"
      } else if (node.type === "BinaryOp") {
        subtitle = `op: ${node.op || ""}`
      } else if (node.type === "UnaryOp") {
        subtitle = `op: ${node.op || ""}`
      } else if (node.identifier) {
        subtitle = `${node.identifier}`
      } else if (node.name) {
        subtitle = `${node.name}`
      } else if (node.op) {
        subtitle = `op: ${node.op}`
      } else if (node.value !== undefined && typeof node.value !== "object") {
        subtitle = `${node.value}`
      }

      const rawChildren: any[] = []

      if (Array.isArray(node.body)) {
        rawChildren.push(...node.body)
      }
      if (node.condition) {
        rawChildren.push(node.condition)
      }
      if (Array.isArray(node.elseBody)) {
        rawChildren.push(...node.elseBody)
      }
      if (node.type === "Expression") {
        if (node.tree) rawChildren.push(node.tree)
      } else {
        if (node.value && typeof node.value === "object") {
          if (node.value.tree) {
            rawChildren.push(node.value.tree)
          } else {
            rawChildren.push(node.value)
          }
        }
      }
      if (node.left) rawChildren.push(node.left)
      if (node.right) rawChildren.push(node.right)
      if (node.operand) rawChildren.push(node.operand)
      if (node.init) rawChildren.push(node.init)
      if (node.step) rawChildren.push(node.step)
      if (Array.isArray(node.args)) rawChildren.push(...node.args)

      const children: TreeNode[] = []
      for (const child of rawChildren) {
        const built = buildTree(child)
        if (built) children.push(built)
      }

      return {
        id: currentId,
        title: nodeType,
        subtitle,
        children,
        width: 170,
        x: 0,
        y: 0,
      }
    }

    const root = buildTree(ast)
    if (!root) return { astNodes: [], astEdges: [] }

    // Step 2: Compute subtree widths
    const computeWidths = (tNode: TreeNode): number => {
      if (tNode.children.length === 0) {
        tNode.width = 170
        return 170
      }
      let totalChildrenWidth = 0
      tNode.children.forEach((child, i) => {
        totalChildrenWidth += computeWidths(child)
        if (i > 0) totalChildrenWidth += 24 // 24px horizontal gap between subtrees
      })
      tNode.width = Math.max(170, totalChildrenWidth)
      return tNode.width
    }

    computeWidths(root)

    // Step 3: Compute X & Y coordinates
    const assignPositions = (tNode: TreeNode, leftX: number, depth: number) => {
      tNode.y = depth * 100 + 40

      if (tNode.children.length === 0) {
        tNode.x = leftX + tNode.width / 2
        return
      }

      let curLeft = leftX
      tNode.children.forEach((child) => {
        assignPositions(child, curLeft, depth + 1)
        curLeft += child.width + 24
      })

      // Center parent over all its children
      const firstChild = tNode.children[0]
      const lastChild = tNode.children[tNode.children.length - 1]
      tNode.x = (firstChild.x + lastChild.x) / 2
    }

    assignPositions(root, 40, 0)

    // Step 4: Emit ReactFlow Nodes and Edges
    const nodes: Node[] = []
    const edges: Edge[] = []

    const flatten = (tNode: TreeNode, parentId: string | null = null) => {
      if (!tNode) return
      nodes.push({
        id: tNode.id,
        position: { x: tNode.x - 80, y: tNode.y },
        data: {
          label: (
            <div className="w-[160px] rounded-md border border-border bg-card p-2 text-center font-mono shadow-xs">
              <div className="text-[11px] font-semibold text-foreground truncate">{tNode.title}</div>
              {tNode.subtitle && (
                <div className="text-[10px] text-muted-foreground mt-0.5 truncate bg-secondary/50 rounded px-1 py-0.5">
                  {tNode.subtitle}
                </div>
              )}
            </div>
          ),
        },
      })

      if (parentId) {
        edges.push({
          id: `e-${parentId}-${tNode.id}`,
          source: parentId,
          target: tNode.id,
          style: { stroke: "hsl(var(--muted-foreground) / 0.5)", strokeWidth: 1.5 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "hsl(var(--muted-foreground) / 0.5)",
            width: 12,
            height: 12,
          },
        })
      }

      tNode.children.forEach((child) => {
        if (child) flatten(child, tNode.id)
      })
    }

    flatten(root)
    return { astNodes: nodes, astEdges: edges }
  }, [ast])

  // Generate Control Flow Graph (CFG) from clean TAC Lines with dynamic non-overlapping layout
  const { cfgNodes, cfgEdges } = useMemo(() => {
    const rawLines = tacLines && tacLines.length > 0 ? tacLines : (quadruples || []).map((q) => {
      if (q.op === "PROC") return `PROCEDURE ${q.arg1}:`
      if (q.op === "ENDPROC") return `END PROCEDURE ${q.arg1}`
      if (q.op === "=") return `${q.result} = ${q.arg1}`
      if (["+", "-", "*", "/"].includes(q.op)) return `${q.result} = ${q.arg1} ${q.op} ${q.arg2}`
      if (q.op === "return") return `return ${q.arg1 || ""}`
      return `${q.result} = ${q.op} ${q.arg1}`
    })

    if (!rawLines || rawLines.length === 0) return { cfgNodes: [], cfgEdges: [] }

    // Partition instructions into distinct Basic Blocks
    interface BasicBlock {
      id: string
      title: string
      instructions: string[]
    }

    const blocks: BasicBlock[] = []
    let currentBlock: BasicBlock = {
      id: "BB0",
      title: "Entry Block",
      instructions: [],
    }

    rawLines.forEach((line) => {
      const isStartProc = line.startsWith("PROCEDURE")
      const isEndProc = line.startsWith("END PROCEDURE")
      const isLabel = line.endsWith(":") && !isStartProc
      const isBranch = line.startsWith("if") || line.startsWith("goto") || line.startsWith("return")

      if ((isStartProc || isLabel) && currentBlock.instructions.length > 0) {
        blocks.push(currentBlock)
        currentBlock = {
          id: `BB${blocks.length}`,
          title: isStartProc ? line.replace(":", "") : `Block (${line})`,
          instructions: [],
        }
      }

      currentBlock.instructions.push(line)

      if ((isBranch || isEndProc) && currentBlock.instructions.length > 0) {
        blocks.push(currentBlock)
        currentBlock = {
          id: `BB${blocks.length}`,
          title: isEndProc ? "Exit Block" : `Block ${blocks.length}`,
          instructions: [],
        }
      }
    })

    if (currentBlock.instructions.length > 0) {
      blocks.push(currentBlock)
    }

    // Position blocks vertically with dynamic spacing so they NEVER overlap
    const nodes: Node[] = []
    const edges: Edge[] = []

    let currentY = 40

    blocks.forEach((bb, idx) => {
      // Estimated height: 36px header + 22px per instruction + 18px padding
      const approxHeight = 36 + bb.instructions.length * 22 + 18

      nodes.push({
        id: bb.id,
        position: { x: 240, y: currentY },
        data: {
          label: (
            <div className="w-[320px] rounded-md border border-border bg-card shadow-sm font-mono text-xs overflow-hidden">
              <div className="px-3 py-1.5 border-b border-border bg-secondary/30 font-semibold text-[11px] text-foreground flex items-center justify-between">
                <span>{bb.title}</span>
                <span className="text-[10px] text-muted-foreground font-normal">{bb.instructions.length} instrs</span>
              </div>
              <div className="p-2.5 space-y-1 text-xs">
                {bb.instructions.map((ins, i) => (
                  <div key={i} className="flex gap-2.5 items-baseline">
                    <span className="text-muted-foreground/40 select-none w-4 text-right text-[10px]">{i + 1}</span>
                    <span className="text-foreground leading-snug">{ins}</span>
                  </div>
                ))}
              </div>
            </div>
          ),
        },
      })

      if (idx < blocks.length - 1) {
        edges.push({
          id: `cfg-edge-${bb.id}-BB${idx + 1}`,
          source: bb.id,
          target: `BB${idx + 1}`,
          style: { stroke: "hsl(var(--muted-foreground) / 0.6)", strokeWidth: 1.5 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "hsl(var(--muted-foreground) / 0.6)",
            width: 14,
            height: 14,
          },
        })
      }

      // Increment Y by exact card height PLUS a generous 60px gap!
      currentY += approxHeight + 60
    })

    return { cfgNodes: nodes, cfgEdges: edges }
  }, [tacLines, quadruples])

  const nodes = viewType === "ast" ? astNodes : cfgNodes
  const edges = viewType === "ast" ? astEdges : cfgEdges

  if (!ast && (!quadruples || quadruples.length === 0)) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-8 bg-background text-xs">
        No graph available. Compile code first in the Compiler view.
      </div>
    )
  }

  return (
    <div className="h-full w-full flex flex-col bg-background overflow-hidden">
      {/* Calm Single Toolbar */}
      <div className="h-10 border-b border-border px-3 flex items-center justify-between shrink-0 bg-background text-xs">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setViewType("ast")}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              viewType === "ast"
                ? "bg-secondary text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
            }`}
          >
            AST Graph
          </button>
          <button
            onClick={() => setViewType("cfg")}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              viewType === "cfg"
                ? "bg-secondary text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
            }`}
          >
            Control Flow Graph
          </button>
        </div>

        <div className="text-[11px] font-mono text-muted-foreground">
          {nodes.length} nodes • {edges.length} edges
        </div>
      </div>

      {/* Clean Full-Bleed Canvas */}
      <div className="flex-1 w-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          className="transition-colors"
        >
          <Background color={theme === "dark" ? "hsl(25 6% 22%)" : "hsl(35 12% 82%)"} gap={20} size={1} />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={() => (theme === "dark" ? "hsl(25 15% 40%)" : "hsl(35 15% 70%)")}
            maskColor={theme === "dark" ? "rgba(25, 23, 22, 0.7)" : "rgba(250, 248, 245, 0.7)"}
            style={{
              backgroundColor: theme === "dark" ? "hsl(25 7% 13%)" : "hsl(35 25% 99%)",
              border: "1px solid hsl(var(--border))",
              borderRadius: 6,
            }}
          />
        </ReactFlow>
      </div>
    </div>
  )
}
