<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import WaitingModal from '@/components/WaitingModal.vue'

const route  = useRoute()
const router = useRouter()

// ── State ────────────────────────────────────────────────────────
const concert        = ref(null)
const selectedCatId  = ref(null)
const quantity       = ref(1)
const loading        = ref(true)
const submitting     = ref(false)
const error          = ref('')

// Waiting room
const showModal      = ref(false)
const invoiceNumber  = ref('')
const orderStatus    = ref('queued')

// Countdown timer
const countdown = ref({ days: 0, hours: 0, minutes: 0, seconds: 0 })
let countdownTimer = null
let pollTimer = null

function updateCountdown() {
  if (!concert.value?.concert_date) return
  const target = new Date(concert.value.concert_date).getTime()
  const now = Date.now()
  const diff = Math.max(0, target - now)

  countdown.value = {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((diff / (1000 * 60)) % 60),
    seconds: Math.floor((diff / 1000) % 60),
  }
}

// ── Lifecycle ────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const { data } = await api.get('/concerts')
    const found = (data.concerts || []).find(c => c.id === Number(route.params.id))
    if (!found) {
      error.value = 'Konser tidak ditemukan'
      return
    }
    concert.value = found
    updateCountdown()
    countdownTimer = setInterval(updateCountdown, 1000)

    // Pre-select first available category
    const first = found.categories.find(c => c.available_quota > 0)
    if (first) selectedCatId.value = first.id
  } catch {
    error.value = 'Gagal memuat data konser'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (countdownTimer) clearInterval(countdownTimer)
})

// ── Helpers ──────────────────────────────────────────────────────
function formatPrice(n) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(n)
}

function selectedCategory() {
  return concert.value?.categories.find(c => c.id === selectedCatId.value)
}

// ── Reserve ticket ───────────────────────────────────────────────
async function reserveTicket() {
  if (!selectedCatId.value) return
  error.value    = ''
  submitting.value = true

  try {
    const { data, status } = await api.post('/orders/reserve', {
      category_id: selectedCatId.value,
      quantity:    quantity.value,
    })

    if (status === 202) {
      invoiceNumber.value = data.invoice_number
      orderStatus.value   = 'queued'
      showModal.value     = true
      startPolling()
    }
  } catch (err) {
    error.value = err.response?.data?.error || 'Gagal memesan tiket'
  } finally {
    submitting.value = false
  }
}

// ── Polling ──────────────────────────────────────────────────────
function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const { data } = await api.get(`/orders/status/${invoiceNumber.value}`)
      orderStatus.value = data.payment_status

      if (data.payment_status === 'completed' || data.payment_status === 'paid') {
        clearInterval(pollTimer)
        pollTimer = null
        // Short delay so user sees success state
        setTimeout(() => {
          router.push(`/orders/${invoiceNumber.value}`)
        }, 1200)
      } else if (data.payment_status === 'failed') {
        clearInterval(pollTimer)
        pollTimer = null
      }
    } catch {
      // Polling error – keep trying
    }
  }, 1500)
}

function closeModal() {
  showModal.value = false
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="text-center py-20">
      <div class="mx-auto w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
    </div>

    <!-- Error -->
    <div v-else-if="error && !concert" class="text-center py-20">
      <p class="text-danger-500 font-medium text-lg">{{ error }}</p>
      <router-link to="/" class="btn-outline mt-4 inline-block">← Kembali</router-link>
    </div>

    <!-- War Room -->
    <div v-else-if="concert" class="max-w-2xl mx-auto">

      <!-- Back link -->
      <router-link to="/" class="inline-flex items-center text-sm text-gray-500 hover:text-primary-600 mb-6 group">
        <span class="mr-1 group-hover:-translate-x-0.5 transition-transform">←</span> Kembali ke katalog
      </router-link>

      <!-- Concert header -->
      <div class="card overflow-hidden mb-6">
        <div class="bg-gradient-to-r from-primary-700 to-accent-600 px-6 py-6 text-white">
          <p class="text-primary-200 text-xs font-semibold uppercase tracking-wider mb-1">War Room</p>
          <h1 class="text-2xl font-bold">{{ concert.title }}</h1>
          <p class="text-primary-100 mt-1">{{ concert.artist }} · {{ concert.venue }}</p>

          <!-- Countdown Timer -->
          <div class="mt-4 pt-4 border-t border-white/20 flex flex-wrap items-center justify-between gap-3">
            <span class="text-xs uppercase tracking-wider text-primary-200 font-semibold flex items-center gap-1.5">
              <span>⏱️</span> Hitung Mundur Konser:
            </span>
            <div class="flex gap-2 text-center">
              <div class="bg-black/25 backdrop-blur-sm rounded-lg px-2.5 py-1 min-w-[44px]">
                <span class="text-base font-bold font-mono">{{ countdown.days }}</span>
                <span class="text-[10px] block opacity-80 uppercase">Hari</span>
              </div>
              <div class="bg-black/25 backdrop-blur-sm rounded-lg px-2.5 py-1 min-w-[44px]">
                <span class="text-base font-bold font-mono">{{ String(countdown.hours).padStart(2, '0') }}</span>
                <span class="text-[10px] block opacity-80 uppercase">Jam</span>
              </div>
              <div class="bg-black/25 backdrop-blur-sm rounded-lg px-2.5 py-1 min-w-[44px]">
                <span class="text-base font-bold font-mono">{{ String(countdown.minutes).padStart(2, '0') }}</span>
                <span class="text-[10px] block opacity-80 uppercase">Mnt</span>
              </div>
              <div class="bg-black/25 backdrop-blur-sm rounded-lg px-2.5 py-1 min-w-[44px]">
                <span class="text-base font-bold font-mono text-amber-300">{{ String(countdown.seconds).padStart(2, '0') }}</span>
                <span class="text-[10px] block opacity-80 uppercase">Dtk</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Category selection -->
      <div class="card p-6 mb-6">
        <h2 class="font-bold text-gray-800 mb-4">Pilih Kategori Tiket</h2>

        <div class="space-y-3">
          <label v-for="cat in concert.categories" :key="cat.id"
                 class="flex items-center gap-4 p-4 rounded-xl border-2 cursor-pointer transition-all"
                 :class="selectedCatId === cat.id
                   ? 'border-primary-500 bg-primary-50'
                   : 'border-gray-100 hover:border-gray-300 bg-white'"
                 :style="{ opacity: cat.available_quota <= 0 ? 0.5 : 1 }">
            <input type="radio" name="category"
                   :value="cat.id"
                   v-model="selectedCatId"
                   :disabled="cat.available_quota <= 0"
                   class="w-4 h-4 text-primary-600 focus:ring-primary-500" />
            <div class="flex-1">
              <div class="font-semibold text-gray-800">{{ cat.category_name }}</div>
              <div class="text-sm text-gray-500">{{ formatPrice(cat.price) }} / tiket</div>
            </div>
            <span class="text-xs font-medium px-2.5 py-1 rounded-full"
                  :class="cat.available_quota > 0 ? 'bg-success-50 text-success-600' : 'bg-danger-50 text-danger-600'">
              {{ cat.available_quota > 0 ? `Sisa ${cat.available_quota}` : 'Habis' }}
            </span>
          </label>
        </div>

        <!-- Quantity -->
        <div class="mt-5">
          <label class="label">Jumlah Tiket</label>
          <div class="flex items-center gap-3">
            <button @click="quantity = Math.max(1, quantity - 1)"
                    class="w-10 h-10 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 font-bold text-lg flex items-center justify-center">
              −
            </button>
            <span class="w-12 text-center text-xl font-bold text-gray-800">{{ quantity }}</span>
            <button @click="quantity = Math.min(4, quantity + 1)"
                    class="w-10 h-10 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 font-bold text-lg flex items-center justify-center">
              +
            </button>
            <span class="text-xs text-gray-400 ml-2">Maks. 4 tiket</span>
          </div>
        </div>

        <!-- Total -->
        <div v-if="selectedCategory()" class="mt-5 p-4 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-between">
          <span class="text-sm text-gray-600">Total</span>
          <span class="text-xl font-bold text-primary-700">
            {{ formatPrice(selectedCategory().price * quantity) }}
          </span>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="mb-4 p-3 rounded-lg bg-danger-50 text-danger-600 text-sm font-medium">
        {{ error }}
      </div>

      <!-- CTA -->
      <button @click="reserveTicket"
              class="w-full py-4 rounded-xl text-lg font-bold text-white
                     bg-gradient-to-r from-red-500 to-orange-500
                     hover:from-red-600 hover:to-orange-600
                     shadow-lg hover:shadow-xl
                     transition-all duration-200
                     disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center justify-center gap-2"
              :disabled="!selectedCatId || submitting">
        <svg v-if="submitting" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
        <span>🔥 AMBIL TIKET SEKARANG</span>
      </button>
    </div>

    <!-- Waiting Room Modal -->
    <WaitingModal
      :visible="showModal"
      :invoice-number="invoiceNumber"
      :status="orderStatus"
      @close="closeModal"
    />
  </div>
</template>
