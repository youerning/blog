import { defineConfig } from 'umi';

export default defineConfig({
  nodeModulesTransform: {
    type: 'none',
  },
  layout: {},
  routes: [
    { path: '/', component: '@/pages/index' },
  ],
  fastRefresh: {},
  proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000/',
        changeOrigin: true,
      },
    },
  mfsu: {}
});
