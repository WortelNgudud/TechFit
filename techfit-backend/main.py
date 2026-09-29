import os
import json
import time
import itertools
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI(
    title="TechFit Core Engine",
    description="Deterministic Budget Allocator + Gemini Multi-Tier Fallback Recommendation Engine"
)

# CORS Setup untuk Frontend (Vue.js / Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# 1. MULTI-ACCOUNT API KEY ROTATOR (15 RPM Per Tier)
# =========================================================================
# Mengambil daftar API Keys dari .env untuk memecah batasan Rate Limit per Project
api_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]

# Filter key yang benar-benar terisi
valid_keys = [k for k in api_keys if k]

if not valid_keys:
    raise RuntimeError("Minimal harus ada 1 GEMINI_API_KEY terpasang di .env!")

# Generator round-robin ganti API Key secara bergantian di setiap panggilan client
key_rotator = itertools.cycle(valid_keys)


def get_genai_client() -> genai.Client:
    """
    [FUNCTION] Rotating Client Instance Generator
    Mengambil instance genai.Client menggunakan API key giliran berikutnya.
    """
    current_key = next(key_rotator)
    return genai.Client(api_key=current_key)


# =========================================================================
# 2. MODEL HIERARCHY / FALLBACK CHAIN CONFIGURATION
# =========================================================================
# Urutan degradasi model dari yang paling presisi hingga jalur darurat
MODEL_FALLBACK_CHAIN = [
    # Tier 1: Flagship Precision (Sangat akurat, taat constraint, limit 5 RPM/key)
    {"name": "gemini-3.8-flash", "tier": "Tier 1: Presisi Maksimal (Standard)"},
    {"name": "gemini-3.7-flash", "tier": "Tier 1: Presisi Maksimal (Standard)"},
    {"name": "gemini-3.6-flash", "tier": "Tier 1: Presisi Maksimal (Standard)"},
    {"name": "gemini-3.5-flash", "tier": "Tier 1: Presisi Standar"},
    
    # Tier 2: Mid & Workhorse (Bagus, kuota badak, breakdown rajin tapi harga kadang offset)
    {"name": "gemini-3.5-flash-lite", "tier": "Tier 2: Mode Cepat (Toleransi Harga +5%)"},
    
    # Tier 3: Emergency Fallback (Sangat disiplin budget, tapi suka bundling/pemalas)
    {"name": "gemini-3.1-flash-lite", "tier": "Tier 3: Mode Hemat Cap Cepat (Item Bundled)"},
]


# =========================================================================
# 3. IN-MEMORY CACHE ENGINE
# =========================================================================
# Cache lokal di memori server untuk mencegah hit berulang ke Google API (0ms response)
RECOMMENDATION_CACHE: Dict[str, tuple[dict, float]] = {}
CACHE_TTL_SECONDS = 3600  # Waktu simpan cache: 1 Jam


def get_cache_key(budget: int, device_type: str, use_case: str) -> str:
    """
    [FUNCTION] Unique Cache Key Generator
    Format: {device_type}_{use_case}_{budget}
    """
    return f"{device_type.lower()}_{use_case.lower()}_{budget}"


# =========================================================================
# 4. PYDANTIC SCHEMAS (WITH METADATA FOR FRONTEND UI)
# =========================================================================
class BudgetRequest(BaseModel):
    total_budget: int = Field(..., ge=3000000, le=100000000, description="Budget Rp 3M - Rp 100M")
    device_type: str = Field(..., description="pc / laptop")
    use_case: str = Field(..., description="gaming / editing / office")

class HardwareItem(BaseModel):
    name: str = Field(..., description="Nama spesifik komponen/laptop")
    category: str = Field(..., description="Kategori item")
    price_min: int = Field(..., description="Harga batas bawah IDR")
    price_max: int = Field(..., description="Harga batas atas IDR")
    specs_summary: str = Field(..., description="Ringkasan spesifikasi")
    search_query: str = Field(..., description="Query pencarian presisi Tokopedia/Shopee")

class TechFitRecommendation(BaseModel):
    device_type: str
    use_case: str
    total_budget: int
    items: List[HardwareItem]
    allocation_reasoning: str
    # Field Tambahan untuk Badge/Disclaimer Gacha Model di UI Frontend:
    model_used: str = Field(default="Unknown", description="Nama model Gemini yang memproses request")
    tier_label: str = Field(default="Unknown", description="Label Tier model untuk UI Disclaimer")


# =========================================================================
# 5. CORE ALLOCATION ENDPOINT (WITH CASCADING FALLBACK)
# =========================================================================
@app.post("/api/allocate", response_model=TechFitRecommendation)
def allocate_and_recommend(request: BudgetRequest):
    budget = request.total_budget
    device_type = request.device_type.lower()
    use_case = request.use_case.lower()

    # ---------------------------------------------------------
    # STEP A: CEK IN-MEMORY CACHE
    # ---------------------------------------------------------
    cache_key = get_cache_key(budget, device_type, use_case)
    now = time.time()

    if cache_key in RECOMMENDATION_CACHE:
        cached_data, timestamp = RECOMMENDATION_CACHE[cache_key]
        if now - timestamp < CACHE_TTL_SECONDS:
            print(f"[CACHE HIT] Returning cached result for key: {cache_key}")
            return cached_data

    # ---------------------------------------------------------
    # STEP B: DETERMINISTIC ALLOCATION RATIO ENGINE
    # ---------------------------------------------------------
    if use_case == "gaming":
        gpu_ratio, cpu_ratio, ram_storage_ratio = 0.40, 0.25, 0.35
    elif use_case == "editing":
        gpu_ratio, cpu_ratio, ram_storage_ratio = 0.30, 0.35, 0.35
    else:
        gpu_ratio, cpu_ratio, ram_storage_ratio = 0.15, 0.45, 0.40

    gpu_limit = int(budget * gpu_ratio)
    cpu_limit = int(budget * cpu_ratio)
    ram_storage_limit = int(budget * ram_storage_ratio)

    prompt = f"""
    Tindak sebagai pakar hardware PC/Laptop di Indonesia.
    Berikan rekomendasi perakitan atau unit laptop bekas/baru yang REALISTIS di pasar Indonesia saat ini.
    
    BATASAN MUTLAK (HARD CONSTRAINTS):
    - Tipe Perangkat: {device_type}
    - Kebutuhan Utama: {use_case}
    - Total Budget Maksimal: Rp {budget:,}
    - Alokasi Maksimal GPU: Rp {gpu_limit:,}
    - Alokasi Maksimal CPU: Rp {cpu_limit:,}
    - Alokasi Maksimal RAM & Storage: Rp {ram_storage_limit:,}
    
    ATURAN KHUSUS METODE REFERENSI:
    1. Harga HARUS dalam bentuk range (price_min & price_max) untuk mengantisipasi fluktuasi pasar.
    2. Sertakan 'search_query' yang presisi agar pengguna bisa langsung copy/paste ke marketplace.
    3. Pastikan total estimasi harga tidak melebihi total budget.
    """

    # ---------------------------------------------------------
    # STEP C: CASCADING MODEL FALLBACK EXECUTION
    # ---------------------------------------------------------
    last_error_msg = ""
    
    # Loop mencoba setiap model di dalam hirarki (Tier 1 -> Tier 2 -> Tier 3)
    for model_info in MODEL_FALLBACK_CHAIN:
        target_model = model_info["name"]
        tier_label = model_info["tier"]
        
        try:
            # Ambil client baru dengan Key hasil rotasi round-robin
            client = get_genai_client()
            
            print(f"[EXECUTE] Trying model '{target_model}' ({tier_label})...")

            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TechFitRecommendation,
                    temperature=0.2,
                ),
            )

            # Parsing JSON response dari Gemini
            recommendation_data = json.loads(response.text)
            
            # Inject Metadata Model & Tier untuk UI Frontend
            recommendation_data["model_used"] = target_model
            recommendation_data["tier_label"] = tier_label

            # Simpan hasil sukses ke cache
            RECOMMENDATION_CACHE[cache_key] = (recommendation_data, now)
            
            print(f"[SUCCESS] Recommendation generated using model: '{target_model}'")
            return recommendation_data

        except Exception as e:
            error_str = str(e)
            last_error_msg = error_str
            
            # Jika kena 429 (Rate Limit), 503 (Server Busy), atau 404 (Model Not Found) -> Lanjut ke model berikutnya!
            if any(err in error_str for err in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "404", "NOT_FOUND"]):
                print(f"[FALLBACK TRIGGERED] Model '{target_model}' failed/limited ({error_str[:60]}...). Moving to next model in chain.")
                continue
            else:
                # Jika error sintaks/fatal yang bukan dari API limit
                print(f"[FATAL ERROR] Non-recoverable error on model '{target_model}': {error_str}")
                break

    # ---------------------------------------------------------
    # STEP D: EXHAUSTION HANDLER (Jika semua model & key habis)
    # ---------------------------------------------------------
    if "429" in last_error_msg or "RESOURCE_EXHAUSTED" in last_error_msg:
        raise HTTPException(
            status_code=429,
            detail="Seluruh model AI sedang mencapai batas kuota (Rate Limit). Tunggu sekitar 15-30 detik lalu coba lagi."
        )
    elif "503" in last_error_msg or "UNAVAILABLE" in last_error_msg:
        raise HTTPException(
            status_code=503,
            detail="Server Google AI sedang padat di semua tier. Silakan coba sebentar lagi."
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses rekomendasi di seluruh rantai model: {last_error_msg}"
        )