<template>
  <div class="not-found-page">
    <section class="not-found-card">
      <p class="kicker">404</p>
      <h1>页面不存在</h1>
      <p class="subtitle">你访问的地址没有对应页面，可能链接写错了，或者这个入口已经被调整。</p>

      <div class="actions">
        <router-link to="/encyclopedia" class="primary-link">回到图鉴首页</router-link>
        <router-link to="/vision" class="secondary-link">去识别页</router-link>
      </div>
    </section>
  </div>
</template>

<style scoped>
.not-found-page {
  min-height: calc(100vh - 68px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(116, 172, 0, 0.12) 0%, transparent 32%),
    radial-gradient(circle at bottom right, rgba(183, 138, 42, 0.14) 0%, transparent 30%),
    linear-gradient(180deg, #f5f7f4 0%, #edf1ec 100%);
}

.not-found-card {
  width: min(100%, 560px);
  padding: 28px;
  border: 1px solid #d9e0d4;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 36px rgba(34, 48, 37, 0.08);
}

.kicker {
  margin: 0;
  color: #81916f;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.not-found-card h1 {
  margin: 10px 0 0;
  color: #243326;
  font-size: 34px;
}

.subtitle {
  margin: 12px 0 0;
  color: #667360;
  font-size: 15px;
  line-height: 1.8;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

.primary-link,
.secondary-link {
  height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 14px;
}

.primary-link {
  background: #75ad00;
  color: #fff;
}

.secondary-link {
  border: 1px solid #d5ddd0;
  background: #fff;
  color: #425042;
}

@media (max-width: 820px) {
  .not-found-page {
    min-height: calc(100vh - 58px);
    padding: 14px;
  }

  .not-found-card {
    padding: 22px 18px;
  }

  .not-found-card h1 {
    font-size: 28px;
  }

  .actions {
    flex-direction: column;
  }

  .primary-link,
  .secondary-link {
    width: 100%;
  }
}
</style>
