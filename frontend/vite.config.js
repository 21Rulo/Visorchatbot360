import { defineConfig } from 'vite'

export default defineConfig({
  base: '/visor_v2/',
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  }
})