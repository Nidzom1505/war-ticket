<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const order   = ref(null)
const loading = ref(true)
const error   = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/orders/status/${route.params.invoiceNumber}`)
    order.value = data
  } catch (err) {
    error.value = err.response?.data?.error || 'Gagal memuat detail pesanan'
  } finally {
    loading.value = false
  }
})

function formatPrice(n) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(n)
}

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('id-ID', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const statusConfig = computed(() => {
  const s = order.value?.payment_status
  if (s === 'paid' || s === 'completed') return { label: 'Lunas',   class: 'bg-success-50 text-success-600 ring-success-500/20' }
  if (s === 'pending' || s === 'queued' || s === 'processing') return { label: 'Diproses', class: 'bg-amber-50 text-amber-600 ring-amber-500/20' }
  return { label: 'Gagal', class: 'bg-danger-50 text-danger-600 ring-danger-500/20' }
})

/**
 * Generate a deterministic QR-code placeholder SVG as a data URI.
 * In production, swap this for a real QR library (e.g. qrcode.vue).
 */
function qrPlaceholder(text) {
  // Simple grid-based visual hash
  let hash = 0
  for (let i = 0; i < text.length; i++) hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0

  const size = 9
  const cells = []
  let seed = Math.abs(hash)

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      seed = (seed * 16807 + 11) % 2147483647
      if (seed % 3 !== 0) {
        cells.push(`<rect x="${c * 10 + 5}" y="${r * 10 + 5}" width="9" height="9" rx="1.5" fill="#1e40af"/>`)
      }
    }
  }

  // Corner markers
  const marker = (x, y) =>
    `<rect x="${x}" y="${y}" width="25" height="25" rx="3" fill="none" stroke="#1e40af" stroke-width="3"/>` +
    `<rect x="${x + 7}" y="${y + 7}" width="11" height="11" rx="2" fill="#1e40af"/>`

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <rect width="100" height="100" fill="white" rx="4"/>
    ${cells.join('')}
    ${marker(5, 5)}
    ${marker(70, 5)}
    ${marker(5, 70)}
  </svg>`

  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="text-center py-20">
      <div class="mx-auto w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-20">
      <p class="text-danger-500 font-medium text-lg">{{ error }}</p>
      <router-link to="/" class="btn-outline mt-4 inline-block">← Kembali</router-link>
    </div>

    <!-- E-Ticket -->
    <div v-else-if="order" class="max-w-2xl mx-auto">

      <router-link to="/" class="inline-flex items-center text-sm text-gray-500 hover:text-primary-600 mb-6 group">
        <span class="mr-1 group-hover:-translate-x-0.5 transition-transform">←</span> Kembali ke katalog
      </router-link>

      <!-- Invoice header card -->
      <div class="card overflow-hidden mb-6">
        <div class="bg-gradient-to-r from-primary-700 to-primary-500 px-6 py-5 text-white flex items-center justify-between">
          <div>
            <p class="text-primary-200 text-xs font-semibold uppercase tracking-wider">E-Ticket</p>
            <h1 class="text-xl font-bold mt-0.5">{{ order.invoice_number }}</h1>
          </div>
          <span class="px-3 py-1 rounded-full text-xs font-bold ring-1"
                :class="statusConfig.class">
            {{ statusConfig.label }}
          </span>
        </div>

        <div class="p-6 space-y-4">
          <!-- Order info -->
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-gray-400 text-xs uppercase tracking-wide">Kategori</span>
              <p class="font-semibold text-gray-800">{{ order.category_name || '-' }}</p>
            </div>
            <div>
              <span class="text-gray-400 text-xs uppercase tracking-wide">Jumlah</span>
              <p class="font-semibold text-gray-800">{{ order.quantity }} tiket</p>
            </div>
            <div>
              <span class="text-gray-400 text-xs uppercase tracking-wide">Harga Satuan</span>
              <p class="font-semibold text-gray-800">{{ formatPrice(order.price || 0) }}</p>
            </div>
            <div>
              <span class="text-gray-400 text-xs uppercase tracking-wide">Total</span>
              <p class="font-semibold text-primary-700 text-lg">{{ formatPrice(order.total_amount || 0) }}</p>
            </div>
          </div>

          <div v-if="order.created_at" class="text-xs text-gray-400">
            Dipesan pada: {{ formatDate(order.created_at) }}
          </div>
        </div>
      </div>

      <!-- Ticket cards -->
      <div v-if="order.tickets && order.tickets.length" class="space-y-4">
        <h2 class="text-lg font-bold text-gray-800">🎟️ Tiket Anda</h2>

        <div v-for="(ticket, idx) in order.tickets" :key="ticket.ticket_code"
             class="card overflow-hidden flex flex-col sm:flex-row">

          <!-- QR code side -->
          <div class="sm:w-40 bg-gray-50 border-b sm:border-b-0 sm:border-r border-gray-100 flex items-center justify-center p-5">
            <img :src="qrPlaceholder(ticket.ticket_code)"
                 :alt="`QR ${ticket.ticket_code}`"
                 class="w-28 h-28" />
          </div>

          <!-- Info side -->
          <div class="flex-1 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-semibold text-gray-400 uppercase tracking-wide">Tiket #{{ idx + 1 }}</span>
              <span v-if="ticket.is_used"
                    class="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-500">
                Sudah digunakan
              </span>
              <span v-else
                    class="px-2 py-0.5 rounded-full text-xs font-medium bg-success-50 text-success-600">
                Aktif
              </span>
            </div>

            <div class="space-y-2 text-sm">
              <div class="flex items-center gap-2">
                <span class="text-gray-400 w-24 shrink-0">Kursi</span>
                <span class="font-bold text-gray-800 text-base">{{ ticket.seat_number }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-gray-400 w-24 shrink-0">Kode Tiket</span>
                <span class="font-mono text-xs text-primary-600 bg-primary-50 px-2 py-1 rounded">{{ ticket.ticket_code }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Still processing -->
      <div v-else-if="order.payment_status === 'queued' || order.payment_status === 'processing'"
           class="card p-8 text-center">
        <div class="mx-auto w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mb-4" />
        <p class="text-gray-600 font-medium">Pesanan masih diproses. Silakan refresh halaman ini.</p>
      </div>
    </div>
  </div>
</template>
