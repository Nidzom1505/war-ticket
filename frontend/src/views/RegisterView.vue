<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth   = useAuthStore()
const router = useRouter()

const form = ref({ username: '', email: '', password: '', confirmPassword: '' })
const error   = ref('')
const success = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value   = ''
  success.value = ''

  if (form.value.password !== form.value.confirmPassword) {
    error.value = 'Konfirmasi password tidak cocok'
    return
  }

  loading.value = true
  try {
    const data = await auth.register({
      username: form.value.username,
      email:    form.value.email,
      password: form.value.password,
      role:     'customer',
    })
    success.value = data.message || 'Registrasi berhasil!'
    setTimeout(() => router.push('/login'), 1500)
  } catch (err) {
    error.value = err.response?.data?.error || 'Registrasi gagal. Coba lagi.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh]">
    <div class="card p-8 w-full max-w-md">

      <div class="text-center mb-8">
        <span class="text-4xl mb-2 block">✨</span>
        <h1 class="text-2xl font-bold text-gray-800">Buat Akun Baru</h1>
        <p class="text-sm text-gray-500 mt-1">Daftar untuk ikut war tiket</p>
      </div>

      <div v-if="error" class="mb-4 p-3 rounded-lg bg-danger-50 text-danger-600 text-sm font-medium">
        {{ error }}
      </div>
      <div v-if="success" class="mb-4 p-3 rounded-lg bg-success-50 text-success-600 text-sm font-medium">
        {{ success }}
      </div>

      <form @submit.prevent="handleRegister" class="space-y-5">
        <div>
          <label class="label">Username</label>
          <input v-model="form.username" type="text" class="input" placeholder="johndoe" required autofocus />
        </div>

        <div>
          <label class="label">Email</label>
          <input v-model="form.email" type="email" class="input" placeholder="john@email.com" required />
        </div>

        <div>
          <label class="label">Password</label>
          <input v-model="form.password" type="password" class="input" placeholder="••••••••" required minlength="5" />
        </div>

        <div>
          <label class="label">Konfirmasi Password</label>
          <input v-model="form.confirmPassword" type="password" class="input" placeholder="••••••••" required />
        </div>

        <button type="submit" class="btn-primary w-full" :disabled="loading">
          <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          {{ loading ? 'Memproses…' : 'Daftar' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-gray-500">
        Sudah punya akun?
        <router-link to="/login" class="text-primary-600 font-semibold hover:underline">Login di sini</router-link>
      </p>
    </div>
  </div>
</template>
