<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth   = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <nav class="bg-white border-b border-gray-200 sticky top-0 z-50">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">

        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-2 group">
          <span class="text-2xl">🎫</span>
          <span class="text-xl font-extrabold text-primary-700 group-hover:text-primary-500 transition-colors">
            TicketWar
          </span>
        </router-link>

        <!-- Right side -->
        <div class="flex items-center gap-3">
          <template v-if="auth.isLoggedIn">
            <div class="hidden sm:flex items-center gap-2 text-sm text-gray-600">
              <div class="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center font-bold text-xs uppercase">
                {{ auth.username.charAt(0) }}
              </div>
              <span class="font-medium">{{ auth.username }}</span>
              <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-red-100 text-red-700':     auth.role === 'admin',
                      'bg-amber-100 text-amber-700': auth.role === 'eo',
                      'bg-blue-100 text-blue-700':   auth.role === 'customer',
                    }">
                {{ auth.role }}
              </span>
            </div>
            <button @click="handleLogout" class="btn text-sm px-3 py-1.5 text-gray-500 hover:text-danger-600 hover:bg-danger-50 rounded-lg">
              Logout
            </button>
          </template>
          <template v-else>
            <router-link to="/login"    class="btn text-sm px-4 py-1.5 text-primary-600 hover:bg-primary-50 rounded-lg font-medium">Login</router-link>
            <router-link to="/register" class="btn-primary text-sm px-4 py-1.5">Daftar</router-link>
          </template>
        </div>

      </div>
    </div>
  </nav>
</template>
