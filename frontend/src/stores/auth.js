/**
 * TicketWar – Pinia Auth Store
 *
 * Manages JWT token, user info, login / register / logout.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  // ── State ────────────────────────────────────────────────────────
  const token = ref(localStorage.getItem('token') || '')
  const user  = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // ── Getters ──────────────────────────────────────────────────────
  const isLoggedIn = computed(() => !!token.value)
  const username   = computed(() => user.value?.username ?? '')
  const role       = computed(() => user.value?.role ?? '')

  // ── Actions ──────────────────────────────────────────────────────

  async function login(username, password) {
    const { data } = await api.post('/auth/login', { username, password })
    _persist(data.token, data.user)
    return data
  }

  async function register(payload) {
    const { data } = await api.post('/auth/register', payload)
    return data
  }

  function logout() {
    token.value = ''
    user.value  = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // ── Internal ─────────────────────────────────────────────────────
  function _persist(jwt, userInfo) {
    token.value = jwt
    user.value  = userInfo
    localStorage.setItem('token', jwt)
    localStorage.setItem('user', JSON.stringify(userInfo))
  }

  return { token, user, isLoggedIn, username, role, login, register, logout }
})
