export default defineNuxtConfig({
  compatibilityDate: '2026-06-05',
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      apiToken: process.env.NUXT_PUBLIC_API_TOKEN || '',
    },
  },
})
