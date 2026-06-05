import { createApp } from 'vue'
// 导入Ant Design Vue
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// 全局样式与主题变量（统一管理）
import './styles/global.css'

import App from './App.vue'

const app = createApp(App)

// 注册Ant Design Vue组件
app.use(Antd)

app.mount('#app')