<script setup>
/**
 * WaitingModal – Overlay shown after a successful 202 Accepted.
 *
 * Props:
 *   visible        – controls visibility
 *   invoiceNumber  – displayed to the user
 *   status         – current polling status ('queued' | 'processing' | 'completed' | 'failed')
 */
defineProps({
  visible:       { type: Boolean, default: false },
  invoiceNumber: { type: String,  default: '' },
  status:        { type: String,  default: 'queued' },
})

defineEmits(['close'])

const statusLabel = {
  queued:     'Menunggu antrian …',
  processing: 'Sedang diproses …',
  completed:  'Tiket berhasil! 🎉',
  failed:     'Gagal memproses pesanan.',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">

          <!-- Spinner -->
          <div v-if="status === 'queued' || status === 'processing'" class="mb-6">
            <div class="mx-auto w-16 h-16 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          </div>

          <!-- Success icon -->
          <div v-else-if="status === 'completed'" class="mb-6">
            <div class="mx-auto w-16 h-16 bg-success-50 rounded-full flex items-center justify-center">
              <svg class="w-8 h-8 text-success-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <!-- Failed icon -->
          <div v-else-if="status === 'failed'" class="mb-6">
            <div class="mx-auto w-16 h-16 bg-danger-50 rounded-full flex items-center justify-center">
              <svg class="w-8 h-8 text-danger-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          </div>

          <h2 class="text-xl font-bold text-gray-800 mb-1">Waiting Room</h2>
          <p class="text-sm text-gray-500 mb-4">Invoice: <span class="font-mono font-semibold text-primary-600">{{ invoiceNumber }}</span></p>

          <p class="text-base font-medium"
             :class="{
               'text-primary-600': status === 'queued' || status === 'processing',
               'text-success-600': status === 'completed',
               'text-danger-600':  status === 'failed',
             }">
            {{ statusLabel[status] || status }}
          </p>

          <!-- Close button (only on terminal states) -->
          <button v-if="status === 'failed'"
                  @click="$emit('close')"
                  class="mt-6 btn-outline text-sm px-6">
            Tutup
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
