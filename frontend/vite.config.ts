/**
 * @file vite.config.ts
 * @path frontend/
 * @description Vite 构建配置
 */

import { defineConfig, type PluginOption } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import fs from 'fs'

function serveDocsPlugin(): PluginOption {
  return {
    name: 'serve-docs',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url && req.url.startsWith('/docs/')) {
          const decodedUrl = decodeURIComponent(req.url)
          const docsPath = resolve(__dirname, '..', decodedUrl.replace(/^\//, ''))
          if (fs.existsSync(docsPath)) {
            const content = fs.readFileSync(docsPath, 'utf-8')
            res.setHeader('Content-Type', 'text/markdown; charset=utf-8')
            res.end(content)
            return
          }
        }
        next()
      })
    },
  }
}

export default defineConfig(({ mode }) => {
  const isAnalyze = mode === 'analyze'
  const isProduction = mode === 'production'

  const plugins: PluginOption[] = [serveDocsPlugin(), vue()]

  if (isAnalyze) {
    plugins.push(
      visualizer({
        open: true,
        gzipSize: true,
        brotliSize: true,
        filename: 'stats.html',
      })
    )
  }

  return {
    plugins,
    base: './',
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
          silenceDeprecations: ['legacy-js-api'],
        },
      },
    },
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: !isProduction,
      minify: 'esbuild',
      esbuild: {
        drop: isProduction ? ['console', 'debugger'] : [],
      },
      modulePreload: {
        polyfill: true,
      },
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            if (id.includes('node_modules')) {
              if (id.includes('echarts') || id.includes('zrender')) {
                return 'charts'
              }
              if (id.includes('ant-design-vue') || id.includes('@ant-design')) {
                return 'ui-antd'
              }
              if (id.includes('element-plus') || id.includes('@element-plus')) {
                return 'ui-element'
              }
              if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
                return 'vue-core'
              }
              return 'vendor'
            }
            return undefined
          },
          chunkFileNames: 'js/[name]-[hash].js',
          entryFileNames: 'js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const name = assetInfo.name ?? ''
            if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(name)) {
              return 'img/[name]-[hash][extname]'
            }
            if (/\.(woff2?|eot|ttf|otf)$/i.test(name)) {
              return 'fonts/[name]-[hash][extname]'
            }
            return 'assets/[name]-[hash][extname]'
          },
        },
      },
      cssCodeSplit: true,
      assetsInlineLimit: 4096,
      reportCompressedSize: true,
      chunkSizeWarningLimit: 1000,
    },
    server: {
      port: 5173,
      host: true,
      strictPort: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://127.0.0.1:8000',
          ws: true,
        },
      },
    },
    define: {
      __APP_VERSION__: JSON.stringify('4.0.0'),
      __APP_ENV__: JSON.stringify(mode),
    },
    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'pinia',
        'vue-i18n',
        'ant-design-vue',
        '@ant-design/icons-vue',
        'element-plus',
        '@element-plus/icons-vue',
        'echarts',
        'vue-echarts',
        'axios',
      ],
    },
  }
})
