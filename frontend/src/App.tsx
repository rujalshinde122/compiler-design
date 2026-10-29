import { Routes, Route } from "react-router"
import AppLayout from "./components/layout/AppLayout"
import CompilerPage from "./pages/CompilerPage"
import VisualizationsPage from "./pages/VisualizationsPage"
import ModernizerPage from "./pages/ModernizerPage"

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<CompilerPage />} />
        <Route path="visualizations" element={<VisualizationsPage />} />
        <Route path="modernizer" element={<ModernizerPage />} />
      </Route>
    </Routes>
  )
}

export default App
