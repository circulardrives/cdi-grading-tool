import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const apiTarget = env.VITE_CDI_API_PROXY_TARGET ?? "http://127.0.0.1:8844"
  const apiToken = env.VITE_CDI_API_TOKEN ?? ""

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: env.VITE_DEV_HOST ?? "127.0.0.1",
      port: Number(env.VITE_DEV_PORT ?? 3000),
      proxy: {
        "/api/cdi": {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (requestPath) => requestPath.replace(/^\/api\/cdi/, ""),
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => {
              if (apiToken) {
                proxyReq.setHeader("X-API-Token", apiToken)
              }
            })
          },
        },
      },
    },
    preview: {
      host: env.VITE_DEV_HOST ?? "127.0.0.1",
      port: Number(env.VITE_DEV_PORT ?? 3000),
    },
  }
})
