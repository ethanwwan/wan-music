<template>
  <div class="hero-header">
    <h1 class="hero-title">{{ title }}</h1>
    <p class="hero-subtitle">{{ subtitle }}</p>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

defineProps({
  title: {
    type: String,
    default: '网易云音乐解析工具'
  },
  subtitle: {
    type: String,
    default: '实时解析网易云音乐单曲、获取真实下载地址及封面信息。'
  }
})
</script>

<style scoped>
.hero-header {
  text-align: center;
  margin-bottom: 40px;
}

.hero-title {
  font-size: var(--font-size-headline-lg);
  font-weight: 700;
  line-height: var(--line-height-headline-lg);
  margin-bottom: 8px;
  color: var(--color-on-surface);
  font-family: var(--font-family);
}

.hero-subtitle {
  font-size: var(--font-size-body-lg);
  line-height: var(--line-height-body-lg);
  font-weight: 400;
  color: var(--color-text-muted);
  margin: 0;
  font-family: var(--font-family);
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
  }
  
  .hero-subtitle {
    font-size: var(--font-size-body-md);
    line-height: var(--line-height-body-md);
  }
}
</style>
