<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import SpecResult from './components/SpecResult.vue'

// Reactive state
const budget = ref(8000000)
const deviceType = ref('pc')
const useCase = ref('gaming')

const loading = ref(false)
const errorMessage = ref('')
const resultData = ref(null)

// State Wishlist
const wishlist = ref([])
const showWishlistModal = ref(false)
const notification = ref('')

const budgetPresets = [3000000, 5000000, 8000000, 12000000, 15000000, 20000000]

// Load Wishlist dari localStorage pas aplikasi pertama kali dimuat
onMounted(() => {
  const saved = localStorage.getItem('techfit_wishlist')
  if (saved) {
    try {
      wishlist.value = JSON.parse(saved)
    } catch (e) {
      console.error('Gagal parse wishlist dari localStorage')
    }
  }
})

// Simpan ke localStorage
const saveWishlistToStorage = () => {
  localStorage.setItem('techfit_wishlist', JSON.stringify(wishlist.value))
}

const handleAddWishlist = (itemData) => {
  wishlist.value.unshift(itemData)
  saveWishlistToStorage()
  
  // Tampilkan notifikasi toast singkat
  notification.value = 'Rekomendasi berhasil disimpan ke Wishlist!'
  setTimeout(() => { notification.value = '' }, 3000)
}

const handleRemoveWishlist = (id) => {
  wishlist.value = wishlist.value.filter(item => item.id !== id)
  saveWishlistToStorage()
}

const formattedBudgetInput = computed({
  get() {
    return new Intl.NumberFormat('id-ID').format(budget.value || 0)
  },
  set(newValue) {
    const rawValue = Number(newValue.replace(/\D/g, ''))
    budget.value = rawValue
  }
})

const formatRupiah = (number) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0
  }).format(number || 0)
}

const handleRecommend = async () => {
  if (budget.value < 3000000) {
    errorMessage.value = 'Budget minimal Rp 3.000.000 agar alokasi komponen realistis.'
    return
  }

  loading.value = true
  errorMessage.value = ''
  resultData.value = null

  try {
    const response = await axios.post('http://127.0.0.1:8000/api/allocate', {
      total_budget: Number(budget.value),
      device_type: deviceType.value,
      use_case: useCase.value
    })
    
    resultData.value = response.data
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Gagal terhubung ke server backend FastAPI.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 py-12 px-4 sm:px-6 lg:px-8 font-sans antialiased selection:bg-sky-500 selection:text-slate-950 relative">
    
    <!-- Floating Notification Toast -->
    <div v-if="notification" class="fixed top-5 right-5 z-50 bg-emerald-500 text-slate-950 px-4 py-3 rounded-xl font-bold text-xs sm:text-sm shadow-2xl flex items-center gap-2 animate-bounce">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
      {{ notification }}
    </div>

    <div class="max-w-4xl mx-auto space-y-10">
      
      <!-- Header Section -->
      <header class="flex flex-col sm:flex-row items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div class="inline-flex items-center gap-2 bg-sky-500/10 border border-sky-500/20 px-3 py-1 rounded-full text-sky-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span class="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span>
            AI Decision Support System
          </div>
          <h1 class="text-3xl sm:text-4xl font-black tracking-tight text-white">
            Tech<span class="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-emerald-400">Fit</span>
          </h1>
        </div>

        <!-- Wishlist Button Counter -->
        <button 
          @click="showWishlistModal = true"
          class="bg-slate-900 border border-slate-800 hover:border-sky-500 text-slate-200 px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 text-xs sm:text-sm font-bold active:scale-95 cursor-pointer"
        >
          <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
          <span>Wishlist</span>
          <span class="bg-sky-500 text-slate-950 text-[11px] px-2 py-0.5 rounded-full font-black">
            {{ wishlist.length }}
          </span>
        </button>
      </header>

      <!-- Interactive Form Container -->
      <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-md">
        <form @submit.prevent="handleRecommend" class="space-y-8">
          
          <!-- 1. Selection Tipe Perangkat -->
          <div class="space-y-3">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-400">
              1. Pilih Tipe Perangkat
            </label>
            <div class="grid grid-cols-2 gap-4">
              <button
                type="button"
                @click="deviceType = 'pc'"
                :class="[
                  'flex items-center justify-center gap-3 p-4 rounded-xl font-bold border transition-all text-sm',
                  deviceType === 'pc' 
                    ? 'bg-sky-500/10 border-sky-500 text-sky-400 shadow-lg shadow-sky-500/10' 
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                ]"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                PC Rakitan
              </button>

              <button
                type="button"
                @click="deviceType = 'laptop'"
                :class="[
                  'flex items-center justify-center gap-3 p-4 rounded-xl font-bold border transition-all text-sm',
                  deviceType === 'laptop' 
                    ? 'bg-sky-500/10 border-sky-500 text-sky-400 shadow-lg shadow-sky-500/10' 
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                ]"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                Laptop Unit
              </button>
            </div>
          </div>

          <!-- 2. Selection Kebutuhan / Use Case -->
          <div class="space-y-3">
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-400">
              2. Kebutuhan Utama
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                @click="useCase = 'gaming'"
                :class="[
                  'p-4 rounded-xl border font-semibold text-left transition-all text-xs sm:text-sm flex flex-col justify-between gap-2',
                  useCase === 'gaming' 
                    ? 'bg-sky-500/10 border-sky-500 text-sky-300' 
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                ]"
              >
                <span class="font-bold text-white">Gaming</span>
                <span class="text-[11px] text-slate-400 font-normal">Prioritas alokasi performa GPU tinggi</span>
              </button>

              <button
                type="button"
                @click="useCase = 'editing'"
                :class="[
                  'p-4 rounded-xl border font-semibold text-left transition-all text-xs sm:text-sm flex flex-col justify-between gap-2',
                  useCase === 'editing' 
                    ? 'bg-sky-500/10 border-sky-500 text-sky-300' 
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                ]"
              >
                <span class="font-bold text-white">Editing / Render</span>
                <span class="text-[11px] text-slate-400 font-normal">Keseimbangan CPU & RAM ekstra</span>
              </button>

              <button
                type="button"
                @click="useCase = 'office'"
                :class="[
                  'p-4 rounded-xl border font-semibold text-left transition-all text-xs sm:text-sm flex flex-col justify-between gap-2',
                  useCase === 'office' 
                    ? 'bg-sky-500/10 border-sky-500 text-sky-300' 
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                ]"
              >
                <span class="font-bold text-white">Office / Sekolah</span>
                <span class="text-[11px] text-slate-400 font-normal">Efisiensi daya & produktivitas harian</span>
              </button>
            </div>
          </div>

          <!-- 3. Input Budget & Presets -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-400">
                3. Nominal Budget Target (IDR)
              </label>
              <span class="text-xs text-sky-400 font-medium">Min. Rp 3.000.000</span>
            </div>

            <div class="relative">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 font-bold text-sm">Rp</span>
              <input
                v-model="formattedBudgetInput"
                type="text"
                class="w-full bg-slate-950 border border-slate-800 rounded-xl pl-12 pr-4 py-3.5 text-white font-bold text-lg focus:outline-none focus:border-sky-500 transition-colors"
                placeholder="8.000.000"
                required
              />
            </div>

            <div class="flex flex-wrap gap-2 pt-1">
              <button
                v-for="preset in budgetPresets"
                :key="preset"
                type="button"
                @click="budget = preset"
                :class="[
                  'text-xs px-3 py-1.5 rounded-lg border transition-all font-medium',
                  budget === preset 
                    ? 'bg-slate-800 border-sky-500 text-sky-400' 
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                ]"
              >
                {{ (preset / 1000000).toFixed(0) }} Juta
              </button>
            </div>
          </div>

          <!-- Error Banner -->
          <div v-if="errorMessage" class="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs sm:text-sm font-medium flex items-center gap-2">
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>{{ errorMessage }}</span>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-gradient-to-r from-sky-500 to-emerald-500 hover:from-sky-400 hover:to-emerald-400 disabled:opacity-50 text-slate-950 font-black py-4 rounded-xl transition-all shadow-lg shadow-sky-500/20 flex items-center justify-center gap-2 cursor-pointer text-sm uppercase tracking-wider"
          >
            <span v-if="loading" class="animate-spin h-5 w-5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
            <span>{{ loading ? 'Mengkalkulasi Alokasi...' : 'Generasi Rekomendasi Fit' }}</span>
          </button>

        </form>
      </div>

      <!-- Skeleton Loading State -->
      <div v-if="loading" class="space-y-6 animate-pulse">
        <div class="h-20 bg-slate-900 border border-slate-800 rounded-xl"></div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="i in 6" :key="i" class="h-40 bg-slate-900 border border-slate-800 rounded-xl"></div>
        </div>
      </div>

      <!-- Result Display Component -->
      <div v-if="resultData && !loading">
        <SpecResult 
          :result="resultData" 
          :user-budget="budget" 
          @save-wishlist="handleAddWishlist"
        />
      </div>

      <!-- Footer Disclaimer -->
      <footer class="pt-8 border-t border-slate-800/80 text-center space-y-3">
        <div class="inline-flex items-center gap-2 text-amber-400 text-xs font-semibold bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
          Catatan & Batasan Referensi
        </div>
        <p class="text-xs text-slate-500 max-w-2xl mx-auto leading-relaxed">
          <strong class="text-slate-400">TechFit</strong> bukan merupakan toko online atau marketplace. Seluruh data estimasi harga dan spesifikasi bersifat simulasi referensi awal. Harga riil di Tokopedia/Shopee dapat berubah sewaktu-waktu sesuai kebijakan penjual dan kondisi stok pasar.
        </p>
      </footer>

    </div>

    <!-- MODAL WISHLIST TERSEMBUNYI -->
    <div v-if="showWishlistModal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
        
        <div class="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 class="text-lg font-bold text-white flex items-center gap-2">
            <svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
            Wishlist Tersimpan (Local Storage)
          </h3>
          <button @click="showWishlistModal = false" class="text-slate-400 hover:text-white font-bold p-1">
            ✕
          </button>
        </div>

        <div class="p-5 overflow-y-auto space-y-4 flex-1">
          <div v-if="wishlist.length === 0" class="text-center py-10 text-slate-500 text-sm">
            Belum ada rekomendasi yang disimpan. Klik "Simpan Wishlist" pada hasil pencarian.
          </div>

          <div 
            v-for="item in wishlist" 
            :key="item.id"
            class="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3 relative group"
          >
            <div class="flex items-center justify-between border-b border-slate-800/60 pb-2">
              <div>
                <span class="text-xs font-bold text-sky-400 capitalize">{{ item.deviceType }} - {{ item.useCase }}</span>
                <span class="text-[10px] text-slate-500 block">{{ item.date }}</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-xs font-extrabold text-emerald-400">{{ formatRupiah(item.userBudget) }}</span>
                <button 
                  @click="handleRemoveWishlist(item.id)" 
                  class="text-red-400 hover:text-red-300 text-xs font-bold bg-red-500/10 px-2 py-1 rounded border border-red-500/20"
                >
                  Hapus
                </button>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2 text-xs">
              <div v-for="(part, idx) in item.items" :key="idx" class="text-slate-300">
                <strong class="text-slate-400">{{ part.category }}:</strong> {{ part.name }}
              </div>
            </div>
          </div>
        </div>

        <div class="p-4 border-t border-slate-800 bg-slate-950 text-right">
          <button 
            @click="showWishlistModal = false" 
            class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-xs font-bold cursor-pointer"
          >
            Tutup
          </button>
        </div>

      </div>
    </div>

  </div>
</template>