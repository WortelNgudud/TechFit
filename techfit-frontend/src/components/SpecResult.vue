<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  },
  userBudget: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['save-wishlist'])

// Helper format angka ke IDR
const formatRupiah = (number) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0
  }).format(number || 0)
}

// Helper styling badge mengikut Tier Model Gemini
const getTierBadgeStyle = (modelName) => {
  if (!modelName) return 'bg-slate-800 text-slate-300 border-slate-700'
  
  if (modelName.includes('3.8') || modelName.includes('3.7') || modelName.includes('3.6')) {
    return 'bg-emerald-950/80 text-emerald-400 border-emerald-500/30' // Tier 1 (Presisi Tinggi)
  } else if (modelName.includes('3.5-flash-lite')) {
    return 'bg-amber-950/80 text-amber-400 border-amber-500/30' // Tier 2 (Kuning/Cepat)
  } else {
    return 'bg-sky-950/80 text-sky-400 border-sky-500/30' // Tier 3 (Emergency/Bundled)
  }
}

// Hitung total estimasi batas atas dari semua item
const totalEstimatedMax = computed(() => {
  if (!props.result?.items) return 0
  return props.result.items.reduce((acc, item) => acc + (item.price_max || 0), 0)
})

// Hitung estimasi sisa budget
const remainingBudget = computed(() => {
  return props.userBudget - totalEstimatedMax.value
})

// Direct Link Generator
const getMarketplaceUrl = (query, platform) => {
  const encoded = encodeURIComponent(query)
  if (platform === 'tokopedia') {
    return `https://www.tokopedia.com/search?q=${encoded}`
  }
  if (platform === 'shopee') {
    return `https://shopee.co.id/search?keyword=${encoded}`
  }
  return '#'
}

const handleSave = () => {
  emit('save-wishlist', {
    id: Date.now(),
    date: new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }),
    userBudget: props.userBudget,
    totalMax: totalEstimatedMax.value,
    deviceType: props.result.device_type,
    useCase: props.result.use_case,
    items: props.result.items,
    modelUsed: props.result.model_used,
    tierLabel: props.result.tier_label
  })
}
</script>

<template>
  <div class="space-y-6">
    
    <!-- Top Summary Card (Budget vs Allocation) -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      <div class="absolute -right-10 -bottom-10 w-40 h-40 bg-sky-500/5 rounded-full blur-2xl pointer-events-none"></div>
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-400">Ringkasan Alokasi</span>
            
            <!-- BADGE METADATA GACHA AI -->
            <span 
              v-if="result.tier_label"
              class="text-[10px] font-mono px-2.5 py-0.5 rounded-full border font-semibold tracking-tight"
              :class="getTierBadgeStyle(result.model_used)"
            >
              ⚡ {{ result.tier_label }} ({{ result.model_used }})
            </span>
          </div>

          <h2 class="text-xl font-black text-white capitalize">
            {{ result.device_type === 'pc' ? 'PC Rakitan' : 'Laptop Unit' }} - Mode {{ result.use_case }}
          </h2>
        </div>

        <div class="flex flex-wrap items-center gap-3 text-xs sm:text-sm">
          <div class="bg-slate-950 border border-slate-800 px-3.5 py-2 rounded-xl">
            <span class="text-slate-400 block text-[10px] uppercase font-bold">Target Budget</span>
            <span class="font-extrabold text-white">{{ formatRupiah(userBudget) }}</span>
          </div>

          <div class="bg-slate-950 border border-slate-800 px-3.5 py-2 rounded-xl">
            <span class="text-slate-400 block text-[10px] uppercase font-bold">Est. Max Total</span>
            <span class="font-extrabold text-sky-400">{{ formatRupiah(totalEstimatedMax) }}</span>
          </div>

          <!-- Tombol Simpan Wishlist -->
          <button 
            @click="handleSave"
            class="bg-sky-500 hover:bg-sky-400 active:scale-95 text-slate-950 font-bold px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 shadow-lg shadow-sky-500/20 text-xs sm:text-sm cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
            Simpan Wishlist
          </button>
        </div>
      </div>

      <!-- AI Reasoning -->
      <div class="pt-5">
        <h4 class="text-xs font-bold uppercase tracking-wider text-sky-400 mb-1.5 flex items-center gap-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          Analisis Rasional Alokasi
        </h4>
        <p class="text-slate-300 text-xs sm:text-sm leading-relaxed font-normal">
          {{ result.allocation_reasoning }}
        </p>
      </div>
    </div>

    <!-- Component Grid List -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div 
        v-for="(item, index) in result.items" 
        :key="index"
        class="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition-all flex flex-col justify-between shadow-lg group"
      >
        <div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-[11px] font-extrabold uppercase tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/20 px-2.5 py-1 rounded-lg">
              {{ item.category }}
            </span>
            <span class="text-[11px] font-medium text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
              Est. Pasar
            </span>
          </div>

          <h3 class="text-base font-bold text-white mb-1.5 group-hover:text-sky-300 transition-colors">
            {{ item.name }}
          </h3>
          
          <p class="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-3">
            {{ item.specs_summary }}
          </p>
        </div>

        <div>
          <div class="pt-3 border-t border-slate-800/80 mb-4 flex items-baseline justify-between">
            <span class="text-[11px] text-slate-400 font-medium">Rentang Harga</span>
            <div class="text-sm font-extrabold text-emerald-400">
              {{ formatRupiah(item.price_min) }} <span class="text-slate-500 font-normal">-</span> {{ formatRupiah(item.price_max) }}
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <a
              :href="getMarketplaceUrl(item.search_query, 'tokopedia')"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center justify-center gap-1.5 text-center text-xs font-bold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 py-2.5 rounded-xl transition-all border border-emerald-500/20 active:scale-[0.98]"
            >
              <span>Tokopedia</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
            </a>

            <a
              :href="getMarketplaceUrl(item.search_query, 'shopee')"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center justify-center gap-1.5 text-center text-xs font-bold bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 py-2.5 rounded-xl transition-all border border-orange-500/20 active:scale-[0.98]"
            >
              <span>Shopee</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
            </a>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>