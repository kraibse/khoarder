import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import ArticleView from '@/views/ArticleView.vue'
import SettingsView from '@/views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/article/:id',
      name: 'article',
      component: ArticleView,
      props: true,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
