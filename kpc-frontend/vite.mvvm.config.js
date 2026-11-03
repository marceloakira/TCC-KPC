import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

/**
 * vite.mvvm.config.js - Configuração Vite para frontend MVVM
 * Permite desenvolvimento paralelo com frontend atual
 */
export default defineConfig({
  plugins: [react()],
  root: './src-mvvm',  // Definir src-mvvm como root
  base: '/',
  
  // Entry point para MVVM
  build: {
    outDir: '../dist-mvvm',  // Ajustar path relativo ao root
    emptyOutDir: true,       // outDir fica fora do root: limpar explicitamente
    rollupOptions: {
      // HTML dentro do diretório MVVM (caminho absoluto: um relativo seria
      // resolvido a partir da pasta onde o comando roda, e não do root)
      input: fileURLToPath(new URL('./src-mvvm/index.html', import.meta.url))
    }
  },
  
  // Servidor em porta diferente
  server: {
    port: 5174,
    host: true,
    open: true,
  },
  
  // Configurações de desenvolvimento
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    'process.env.MVVM_MODE': JSON.stringify('true')
  },
  
  // Resolve paths para MVVM (relativo ao root src-mvvm)
  resolve: {
    alias: {
      '@': '.',
      '@components': './views/components',
      '@layouts': './views/layouts',
      '@views': './views',
      '@models': './models',
      '@viewmodels': './viewmodels',
    }
  },
  
  // CSS config
  css: {
    modules: {
      localsConvention: 'camelCase'
    }
  },
  
  // Preview config para build. Para testar o build de produção localmente:
  //   VITE_API_BASE_URL=/api npm run build:mvvm && npm run preview:mvvm
  // /api é repassado ao backend local, como o Caddy faz no servidor.
  preview: {
    port: 4174,
    host: true,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:3132',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  }
})