<template>
  <footer class="footer-container">
    <div class="footer-content">
      <p class="footer-text">© 2026 网易云解析工具. All rights reserved.</p>
      <p class="footer-text">开源项目 | 仅供学习</p>
      <p class="footer-text">Version 1.3.6 · 构建时间: 2026.5.24</p>
    </div>
  </footer>
</template>

<script setup>
</script>

<style scoped>
.footer-container {
  width: 100%;
  margin-top: auto;
  background: transparent;
}

.footer-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 var(--padding-desktop);
  text-align: center;
  padding-top: 3rem;
  padding-bottom: 3rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.footer-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-body-sm);
  margin: 0;
}

@media (max-width: 768px) {
  .footer-content {
    padding: 0 var(--padding-mobile);
    padding-top: 2rem;
    padding-bottom: 2rem;
  }
}
</style>