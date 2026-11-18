import os
import json
import time
import itertools
from collections import OrderedDict
from typing import Dict, List, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================================
# ENVIRONMENT
# ============================================================================

load_dotenv()


# ============================================================================
# FASTAPI
# ============================================================================

app = FastAPI(
    title="TechFit Core Engine",
    description=(
        "Deterministic Budget Allocator + Gemini Recommendation Engine"
    )
)


# ============================================================================
# CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 1. GEMINI API KEY ROTATOR
# ============================================================================
#
# Key tetap diputar round-robin untuk membagi quota.
#
# Bedanya dengan versi lama:
# - Client tidak dibuat ulang setiap request.
# - Satu client disimpan untuk setiap API key.
#
# ============================================================================

api_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]

valid_keys = [key for key in api_keys if key]

if not valid_keys:
    raise RuntimeError(
        "Minimal harus ada 1 GEMINI_API_KEY terpasang!"
    )


# Iterator untuk round-robin API key
key_rotator = itertools.cycle(range(len(valid_keys)))


# Client dibuat SEKALI untuk setiap API key.
# Tidak perlu membuat genai.Client baru pada setiap request.
GENAI_CLIENTS: List[genai.Client] = [
    genai.Client(api_key=key)
    for key in valid_keys
]


def get_genai_client() -> Tuple[genai.Client, int]:
    """
    Mengambil client berdasarkan rotasi API key.

    Return:
        (client, key_index)
    """

    key_index = next(key_rotator)

    return GENAI_CLIENTS[key_index], key_index


# ============================================================================
# 2. MODEL CONFIGURATION
# ============================================================================
#
# Sengaja hanya 2 level.
#
# Primary:
#   Model utama dengan kualitas terbaik.
#
# Fallback:
#   Model yang lebih ringan untuk kondisi 429 / 503 / unavailable.
#
# ============================================================================

PRIMARY_MODEL = "gemini-3.8-flash"

FALLBACK_MODEL = "gemini-3.5-flash-lite"


MODEL_METADATA = {
    PRIMARY_MODEL: {
        "tier": "Tier 1: Presisi Maksimal"
    },

    FALLBACK_MODEL: {
        "tier": "Tier 2: Fast Fallback"
    }
}


# ============================================================================
# 3. IN-MEMORY CACHE
# ============================================================================
#
# Cache ini hanya L1 cache.
#
# Kelebihan:
# - Sangat cepat.
# - Tidak perlu database/Redis.
#
# Kekurangan:
# - Hilang ketika Render restart/redeploy/sleep.
#
# ============================================================================

RECOMMENDATION_CACHE = OrderedDict()

CACHE_TTL_SECONDS = 3600          # 1 jam
MAX_CACHE_ENTRIES = 200           # batas RAM


def get_cache_key(
    budget: int,
    device_type: str,
    use_case: str
) -> str:

    return (
        f"{device_type.strip().lower()}"
        f"_{use_case.strip().lower()}"
        f"_{budget}"
    )


def get_cached_result(cache_key: str):

    cached = RECOMMENDATION_CACHE.get(cache_key)

    if cached is None:
        return None

    data, timestamp = cached

    current_time = time.time()

    # Expired
    if current_time - timestamp >= CACHE_TTL_SECONDS:

        del RECOMMENDATION_CACHE[cache_key]

        return None

    # LRU:
    # Entry yang baru digunakan dipindahkan ke belakang.
    RECOMMENDATION_CACHE.move_to_end(cache_key)

    return data


def set_cached_result(cache_key: str, data: dict):

    # Kalau key sudah ada, hapus dulu supaya urutan LRU benar.
    if cache_key in RECOMMENDATION_CACHE:
        del RECOMMENDATION_CACHE[cache_key]

    RECOMMENDATION_CACHE[cache_key] = (
        data,
        time.time()
    )

    # Buang entry paling lama kalau cache terlalu besar.
    while len(RECOMMENDATION_CACHE) > MAX_CACHE_ENTRIES:
        RECOMMENDATION_CACHE.popitem(last=False)


# ============================================================================
# 4. PYDANTIC SCHEMAS
# ============================================================================

class BudgetRequest(BaseModel):

    total_budget: int = Field(
        ...,
        ge=3_000_000,
        le=100_000_000,
        description="Budget Rp 3M - Rp 100M"
    )

    device_type: str = Field(
        ...,
        description="pc / laptop"
    )

    use_case: str = Field(
        ...,
        description="gaming / editing / office"
    )


class HardwareItem(BaseModel):

    name: str = Field(
        ...,
        description="Nama spesifik komponen/laptop"
    )

    category: str = Field(
        ...,
        description="Kategori item"
    )

    price_min: int = Field(
        ...,
        description="Harga batas bawah IDR"
    )

    price_max: int = Field(
        ...,
        description="Harga batas atas IDR"
    )

    specs_summary: str = Field(
        ...,
        description="Ringkasan spesifikasi"
    )

    search_query: str = Field(
        ...,
        description="Query pencarian presisi Tokopedia/Shopee"
    )


class TechFitRecommendation(BaseModel):

    device_type: str

    use_case: str

    total_budget: int

    items: List[HardwareItem]

    allocation_reasoning: str

    model_used: str = Field(
        default="Unknown",
        description="Nama model Gemini yang memproses request"
    )

    tier_label: str = Field(
        default="Unknown",
        description="Label tier model"
    )


# ============================================================================
# 5. PROMPT BUILDER
# ============================================================================
#
# Prompt dibuat sekali.
# Tidak ada perubahan besar terhadap logic original lu.
#
# ============================================================================

def build_prompt(
    budget: int,
    device_type: str,
    use_case: str,
    gpu_limit: int,
    cpu_limit: int,
    ram_storage_limit: int
) -> str:

    return f"""
Tindak sebagai pakar hardware PC/Laptop di Indonesia.

Berikan rekomendasi perakitan atau unit laptop bekas/baru
yang REALISTIS di pasar Indonesia saat ini.

BATASAN MUTLAK (HARD CONSTRAINTS):

- Tipe Perangkat: {device_type}
- Kebutuhan Utama: {use_case}
- Total Budget Maksimal: Rp {budget:,}
- Alokasi Maksimal GPU: Rp {gpu_limit:,}
- Alokasi Maksimal CPU: Rp {cpu_limit:,}
- Alokasi Maksimal RAM & Storage: Rp {ram_storage_limit:,}

ATURAN KHUSUS:

1. Harga HARUS dalam bentuk range:
   price_min dan price_max.

2. Sertakan search_query yang presisi
   agar pengguna bisa langsung copy/paste
   ke marketplace seperti Tokopedia/Shopee.

3. Total estimasi harga tidak boleh melebihi
   total budget.

4. Prioritaskan hardware yang realistis ditemukan
   di pasar Indonesia.

5. Jangan memberikan komponen yang jelas-jelas
   melampaui batas alokasi kecuali ada alasan
   kuat dan tetap tidak melampaui total budget.

6. Jangan mengarang harga yang terlalu spesifik.
   Gunakan price range yang realistis.

7. Berikan rekomendasi yang konkret,
   bukan sekadar kategori seperti
   "gunakan GPU kelas menengah".

Keluarkan response dalam format JSON
sesuai schema yang diberikan.
"""


# ============================================================================
# 6. DETERMINISTIC BUDGET ALLOCATION
# ============================================================================
#
# Bagian ini TIDAK menggunakan AI.
# Ini tetap dikontrol oleh backend.
#
# ============================================================================

def calculate_budget_allocation(
    budget: int,
    use_case: str
):

    if use_case == "gaming":

        gpu_ratio = 0.40
        cpu_ratio = 0.25
        ram_storage_ratio = 0.35

    elif use_case == "editing":

        gpu_ratio = 0.30
        cpu_ratio = 0.35
        ram_storage_ratio = 0.35

    else:

        gpu_ratio = 0.15
        cpu_ratio = 0.45
        ram_storage_ratio = 0.40

    gpu_limit = int(budget * gpu_ratio)

    cpu_limit = int(budget * cpu_ratio)

    ram_storage_limit = int(
        budget * ram_storage_ratio
    )

    return (
        gpu_limit,
        cpu_limit,
        ram_storage_limit
    )


# ============================================================================
# 7. ERROR CLASSIFICATION
# ============================================================================

def is_retryable_gemini_error(error: Exception) -> bool:

    error_string = str(error).upper()

    retryable_errors = [
        "429",
        "RESOURCE_EXHAUSTED",
        "503",
        "UNAVAILABLE",
        "404",
        "NOT_FOUND"
    ]

    return any(
        error_code in error_string
        for error_code in retryable_errors
    )


def get_http_error_from_gemini(error: Exception):

    error_string = str(error).upper()

    if (
        "429" in error_string
        or "RESOURCE_EXHAUSTED" in error_string
    ):
        return HTTPException(
            status_code=429,
            detail=(
                "Quota Gemini sedang mencapai batas. "
                "Silakan coba lagi beberapa saat."
            )
        )

    if (
        "503" in error_string
        or "UNAVAILABLE" in error_string
    ):
        return HTTPException(
            status_code=503,
            detail=(
                "Server Gemini sedang tidak tersedia. "
                "Silakan coba lagi."
            )
        )

    return HTTPException(
        status_code=500,
        detail=f"Gagal memproses rekomendasi: {str(error)}"
    )


# ============================================================================
# 8. GEMINI REQUEST
# ============================================================================

def call_gemini(
    model_name: str,
    prompt: str
) -> dict:

    client, key_index = get_genai_client()

    print(
        f"[EXECUTE] Model={model_name} "
        f"KeyIndex={key_index}"
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,

        config=types.GenerateContentConfig(
            response_mime_type="application/json",

            response_schema=TechFitRecommendation,

            temperature=0.2,
        )
    )

    if not response.text:
        raise RuntimeError(
            "Gemini mengembalikan response kosong."
        )

    try:

        recommendation_data = json.loads(
            response.text
        )

    except json.JSONDecodeError as e:

        raise RuntimeError(
            f"Response Gemini bukan JSON valid: {e}"
        )

    # Validasi ulang menggunakan schema Pydantic.
    validated = TechFitRecommendation.model_validate(
        recommendation_data
    )

    result = validated.model_dump()

    # Metadata backend
    result["model_used"] = model_name

    result["tier_label"] = (
        MODEL_METADATA[model_name]["tier"]
    )

    return result


# ============================================================================
# 9. CORE ENDPOINT
# ============================================================================

@app.post(
    "/api/allocate",
    response_model=TechFitRecommendation
)
def allocate_and_recommend(
    request: BudgetRequest
):

    # ------------------------------------------------------------------------
    # STEP A — NORMALIZE INPUT
    # ------------------------------------------------------------------------

    budget = request.total_budget

    device_type = (
        request.device_type.strip().lower()
    )

    use_case = (
        request.use_case.strip().lower()
    )

    # ------------------------------------------------------------------------
    # STEP B — CACHE LOOKUP
    # ------------------------------------------------------------------------

    cache_key = get_cache_key(
        budget=budget,
        device_type=device_type,
        use_case=use_case
    )

    cached_result = get_cached_result(
        cache_key
    )

    if cached_result is not None:

        print(
            f"[CACHE HIT] {cache_key}"
        )

        return cached_result

    print(
        f"[CACHE MISS] {cache_key}"
    )

    # ------------------------------------------------------------------------
    # STEP C — DETERMINISTIC ALLOCATION
    # ------------------------------------------------------------------------

    (
        gpu_limit,
        cpu_limit,
        ram_storage_limit
    ) = calculate_budget_allocation(
        budget,
        use_case
    )

    print(
        "[ALLOCATION] "
        f"GPU=Rp {gpu_limit:,} | "
        f"CPU=Rp {cpu_limit:,} | "
        f"RAM+Storage=Rp {ram_storage_limit:,}"
    )

    # ------------------------------------------------------------------------
    # STEP D — BUILD PROMPT
    # ------------------------------------------------------------------------

    prompt = build_prompt(
        budget=budget,
        device_type=device_type,
        use_case=use_case,
        gpu_limit=gpu_limit,
        cpu_limit=cpu_limit,
        ram_storage_limit=ram_storage_limit
    )

    # ------------------------------------------------------------------------
    # STEP E — PRIMARY MODEL
    # ------------------------------------------------------------------------

    last_error = None

    try:

        result = call_gemini(
            model_name=PRIMARY_MODEL,
            prompt=prompt
        )

        # Cache hanya response yang benar-benar sukses.
        set_cached_result(
            cache_key,
            result
        )

        print(
            f"[SUCCESS] Primary model: "
            f"{PRIMARY_MODEL}"
        )

        return result

    except Exception as e:

        last_error = e

        print(
            f"[PRIMARY FAILED] "
            f"{PRIMARY_MODEL}: {str(e)[:200]}"
        )

        # Kalau error bukan jenis yang layak fallback,
        # langsung hentikan request.
        if not is_retryable_gemini_error(e):

            print(
                "[FATAL] Error bukan retryable. "
                "Tidak menjalankan fallback."
            )

            raise get_http_error_from_gemini(e)

    # ------------------------------------------------------------------------
    # STEP F — SINGLE FALLBACK
    # ------------------------------------------------------------------------
    #
    # Hanya dijalankan kalau primary gagal karena:
    # 429 / 503 / unavailable / model not found.
    #
    # Tidak ada fallback chain panjang lagi.
    #
    # ------------------------------------------------------------------------

    print(
        f"[FALLBACK] Switching to "
        f"{FALLBACK_MODEL}"
    )

    try:

        result = call_gemini(
            model_name=FALLBACK_MODEL,
            prompt=prompt
        )

        set_cached_result(
            cache_key,
            result
        )

        print(
            f"[SUCCESS] Fallback model: "
            f"{FALLBACK_MODEL}"
        )

        return result

    except Exception as fallback_error:

        print(
            f"[FALLBACK FAILED] "
            f"{FALLBACK_MODEL}: "
            f"{str(fallback_error)[:200]}"
        )

        # Kalau fallback juga gagal,
        # jangan mencoba model ketiga, keempat, dst.
        raise get_http_error_from_gemini(
            fallback_error
        )


# ============================================================================
# 10. HEALTH CHECK
# ============================================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "TechFit Core Engine",
        "primary_model": PRIMARY_MODEL,
        "fallback_model": FALLBACK_MODEL,
        "cache_entries": len(RECOMMENDATION_CACHE)
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "cache_entries": len(RECOMMENDATION_CACHE),
        "gemini_keys": len(valid_keys)
    }