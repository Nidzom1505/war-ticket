<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth     = useAuthStore()
const router   = useRouter()
const concerts = ref([])
const loading  = ref(true)
const error    = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get('/concerts')
    concerts.value = data.concerts || []
  } catch (err) {
    error.value = 'Gagal memuat daftar konser.'
  } finally {
    loading.value = false
  }
})

function formatPrice(n) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(n)
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function goToWar(concertId) {
  if (!auth.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: `/concerts/${concertId}/war` } })
    return
  }
  router.push(`/concerts/${concertId}/war`)
}
</script>

<template>
  <div>
    <!-- Hero -->
    <div class="text-center mb-10">
      <h1 class="text-3xl sm:text-4xl font-extrabold text-gray-900">
        🎵 Konser <span class="text-primary-600">Tersedia</span>
      </h1>
      <p class="mt-2 text-gray-500 max-w-lg mx-auto">Pilih konser favoritmu dan bersiaplah untuk war tiket!</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid gap-6 sm:grid-cols-2">
      <div v-for="n in 2" :key="n" class="card p-6 animate-pulse">
        <div class="h-6 bg-gray-200 rounded w-3/4 mb-3" />
        <div class="h-4 bg-gray-100 rounded w-1/2 mb-6" />
        <div class="h-10 bg-gray-100 rounded w-full" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-16">
      <p class="text-danger-500 font-medium">{{ error }}</p>
    </div>

    <!-- Empty -->
    <div v-else-if="concerts.length === 0" class="text-center py-16 text-gray-400">
      <span class="text-5xl block mb-3">🎤</span>
      <p class="text-lg font-medium">Belum ada konser tersedia.</p>
    </div>

    <!-- Concert cards -->
    <div v-else class="grid gap-6 sm:grid-cols-2">
      <div v-for="concert in concerts" :key="concert.id" class="card overflow-hidden">

        <!-- Header gradient -->
        <div class="bg-gradient-to-r from-primary-600 to-accent-600 px-6 py-5 text-white">
          <h2 class="text-xl font-bold leading-tight">{{ concert.title }}</h2>
          <p class="text-primary-100 text-sm mt-1">{{ concert.artist }}</p>
        </div>

        <div class="p-6">
          <!-- Meta -->
          <div class="flex flex-col gap-2 text-sm text-gray-600 mb-5">
            <div class="flex items-center gap-2">
              <span>📍</span><span>{{ concert.venue }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span>📅</span><span>{{ formatDate(concert.concert_date) }}</span>
            </div>
          </div>

          <!-- Categories -->
          <div class="space-y-2 mb-6">
            <div v-for="cat in concert.categories" :key="cat.id"
                 class="flex items-center justify-between p-3 rounded-lg bg-gray-50 border border-gray-100">
              <div>
                <span class="font-semibold text-gray-800">{{ cat.category_name }}</span>
                <span class="ml-2 text-sm font-medium text-primary-600">{{ formatPrice(cat.price) }}</span>
              </div>
              <span class="text-xs font-medium px-2.5 py-1 rounded-full"
                    :class="cat.available_quota > 0 ? 'bg-success-50 text-success-600' : 'bg-danger-50 text-danger-600'">
                {{ cat.available_quota > 0 ? `Sisa ${cat.available_quota}` : 'Habis' }}
              </span>
            </div>
          </div>

          <!-- CTA -->
          <button @click="goToWar(concert.id)"
                  class="btn-accent w-full text-base py-3"
                  :disabled="concert.categories.every(c => c.available_quota <= 0)">
            🔥 Ikuti War Tiket
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
