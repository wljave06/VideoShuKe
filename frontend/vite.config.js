export default {
  server: {
    host: '0.0.0.0',
    port: 9999, // 改成固定端口
    proxy: {
      '/api': {
        target: 'http://localhost:8888',
        changeOrigin: true,
        ws: true,
      },
    },
  },
};
