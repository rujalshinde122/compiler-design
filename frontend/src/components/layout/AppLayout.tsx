import { Link, Outlet, useLocation } from "react-router"
import { Sun, Moon } from "lucide-react"
import { useTheme } from "../theme-provider"

export default function AppLayout() {
  const location = useLocation()
  const { theme, setTheme } = useTheme()

  const navItems = [
    { name: "Compiler", path: "/" },
    { name: "Visualizer", path: "/visualizations" },
    { name: "Modernizer", path: "/modernizer" },
  ]

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground overflow-hidden">
      {/* Clean, Calm Single Navbar */}
      <header className="h-11 border-b border-border px-4 flex items-center justify-between shrink-0 bg-background">
        <div className="flex items-center gap-6">
          <Link to="/" className="font-semibold text-xs tracking-tight text-foreground hover:opacity-80 transition-opacity">
            Compiler Design
          </Link>

          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-2.5 py-1 rounded text-xs transition-colors ${
                    isActive
                      ? "bg-secondary text-foreground font-medium"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                  }`}
                >
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>

        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          title="Toggle theme"
        >
          {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col overflow-hidden bg-background">
        <Outlet />
      </main>
    </div>
  )
}
