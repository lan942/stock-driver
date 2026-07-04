<template>
  <div class="app-container">
    <header class="app-header">
      <div class="logo">
        <h1>股票分析工具</h1>
      </div>
      <nav class="nav">
        <router-link to="/" class="nav-link">股票列表</router-link>
        <router-link to="/top" class="nav-link">涨跌排行</router-link>
        <router-link to="/data-summary" class="nav-link">数据概览</router-link>
        <router-link to="/portfolio" class="nav-link">持仓管理</router-link>
        <router-link to="/crawler" class="nav-link">数据爬取</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  color: white;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.logo h1 {
  font-size: 24px;
  font-weight: 600;
}

.nav {
  display: flex;
  gap: 24px;
}

.nav-link {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-size: 16px;
  padding: 8px 16px;
  border-radius: 4px;
  transition: all 0.3s;
}

.nav-link:hover,
.nav-link.router-link-active {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
}

.app-main {
  flex: 1;
  padding: 24px;
}
</style>
