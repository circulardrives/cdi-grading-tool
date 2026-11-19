import { readFileSync } from "fs"
import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv, type Plugin } from "vite"

/**
 * Demo build only: "CDI Health — Demo" page title. Deep links (/drives/…) are
 * served by the host's SPA fallback (wrangler.demo.jsonc:
 * not_found_handling = "single-page-application").
 */
function staticDemo(): Plugin {
  return {
    name: "cdi-static-demo",
    transformIndexHtml: (html) =>
      html.replace(/<title>[^<]*<\/title>/, "<title>CDI Health — Demo</title>"),
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const apiTarget = env.VITE_CDI_API_PROXY_TARGET ?? "http://127.0.0.1:8844"
  // Injected by the dev/preview proxy (Node side only); never exposed to the
  // browser. VITE_CDI_API_TOKEN is still accepted for older .env.local files.
  const apiToken = env.CDI_HEALTH_API_TOKEN || env.VITE_CDI_API_TOKEN || ""

  const { version: packageVersion } = JSON.parse(
    readFileSync(path.resolve(__dirname, "package.json"), "utf8")
  ) as { version: string }
  // Release builds stamp the tag version (VITE_APP_VERSION build arg in
  // Dockerfile.dashboard, set by release.yml); otherwise use package.json.
  const appVersion =
    (env.VITE_APP_VERSION ?? "").trim().replace(/^v/, "") || packageVersion

  // VITE_DEMO=1: static public demo (scripts/build-demo.sh). The API is
  // replaced by src/demo/backend.ts; normal builds never include it.
  const isDemo = env.VITE_DEMO === "1"

  return {
    plugins: [react(), tailwindcss(), ...(isDemo ? [staticDemo()] : [])],
    define: {
      // Shown in Settings › About.
      __APP_VERSION__: JSON.stringify(appVersion),
      __CDI_DEMO__: JSON.stringify(isDemo),
    },
    // The demo backend chunk carries the sample drives (~1 MB, ~90 kB gzip).
    build: isDemo
      ? { outDir: "dist-demo", chunkSizeWarningLimit: 1500 }
      : undefined,
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
  }
})
