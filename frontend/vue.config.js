const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 9999,
    host: '0.0.0.0',
    // 解决Watchpack错误
    watchFiles: {
      options: {
        usePolling: true,
        interval: 1000,
        ignored: [
          '**/node_modules/**',
          '**/.git/**',
          '**/dist/**',
          '**/public/**',
          '**/assets/**',
          '**/C:/pagefile.sys', // 忽略系统文件
          '**/C:/**/*.{sys,dll}', // 忽略系统文件
          '**/C:/Windows/**', // 忽略Windows系统目录
          '**/C:/Program Files/**', // 忽略程序文件目录
          '**/C:/Program Files (x86)/**' // 忽略程序文件目录
        ]
      }
    }
  },
  // 配置Webpack忽略系统文件
  configureWebpack: {
    watchOptions: {
      ignored: [
        '**/node_modules/**',
        '**/.git/**',
        '**/dist/**',
        '**/public/**',
        '**/assets/**',
        '**/C:/pagefile.sys', // 忽略系统文件
        '**/C:/**/*.{sys,dll}', // 忽略系统文件
        '**/C:/Windows/**', // 忽略Windows系统目录
        '**/C:/Program Files/**', // 忽略程序文件目录
        '**/C:/Program Files (x86)/**' // 忽略程序文件目录
      ]
    }
  },
  // 生产环境关闭source map
  productionSourceMap: false
})