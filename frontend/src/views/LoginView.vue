<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value   = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    error.value = err.response?.data?.error || 'Login gagal. Periksa username dan password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh]">
    <div class="card p-8 w-full max-w-md">

      <div class="text-center mb-8">
        <span class="text-4xl mb-2 block">🎫</span>
        <h1 class="text-2xl font-bold text-gray-800">Masuk ke TicketWar</h1>
        <p class="text-sm text-gray-500 mt-1">Masukkan akun untuk melanjutkan</p>
      </div>

      <!-- Error alert -->
      <div v-if="error" class="mb-4 p-3 rounded-lg bg-danger-50 text-danger-600 text-sm font-medium">
        {{ error }}
      </div>

      <form @submit.prevent="handleLogin" class="space-y-5">
        <div>
          <label class="label">Username</label>
          <input v-model="form.username" type="text" class="input" placeholder="johndoe" required autofocus />
        </div>

        <div>
          <label class="label">Password</label>
          <input v-model="form.password" type="password" class="input" placeholder="••••••••" required />
        </div>

        <button type="submit" class="btn-primary w-full" :disabled="loading">
          <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          {{ loading ? 'Memproses…' : 'Login' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-gray-500">
        Belum punya akun?
        <router-link to="/register" class="text-primary-600 font-semibold hover:underline">Daftar sekarang</router-link>
      </p>
    </div>
  </div>
</template>
