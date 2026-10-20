/**
 * TicketWar – Vue Router Configuration
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'concerts',
    component: () => import('@/views/ConcertListView.vue'),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/concerts/:id/war',
    name: 'war-room',
    component: () => import('@/views/WarRoomView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/orders/:invoiceNumber',
    name: 'order-detail',
    component: () => import('@/views/OrderDetailView.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── Navigation guards ──────────────────────────────────────────────
router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Redirect logged-in users away from guest-only pages
  if (to.meta.guest && auth.isLoggedIn) {
    return { name: 'concerts' }
  }
})

export default router
