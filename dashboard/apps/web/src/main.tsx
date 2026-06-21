import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "@workspace/ui/globals.css"
import { App } from "./App.tsx"
import { MockDataProvider } from "@/components/mock-data-provider.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { Toaster } from "@/components/toaster.tsx"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="system">
      <MockDataProvider>
        <App />
        <Toaster richColors closeButton />
      </MockDataProvider>
    </ThemeProvider>
  </StrictMode>
)
