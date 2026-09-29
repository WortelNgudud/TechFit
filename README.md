# ⚡ TechFit Core Engine

> **Deterministic Budget Allocator + Gemini Multi-Tier Fallback Recommendation System**

TechFit Core Engine adalah aplikasi pemodal & perekomendasi rakitan PC/Laptop berbasis web. Sistem ini menggabungkan presisi matematika deterministik (Python Backend) dengan kapabilitas AI (Google Gemini API) menggunakan arsitektur *graceful degradation* untuk menjamin *high availability* di atas pembatasan *Free Tier*.

---

## 🏗️ Technical Architecture & Key Features

1. **Deterministic Allocation Engine (Python):**
   * Menghitung batas anggaran GPU, CPU, dan RAM/Storage menggunakan rasio matematika pasti sebelum mengesekusi *prompt* AI.
   * Mencegah AI melenceng dari batasan alokasi awal.

2. **Cascading Model Fallback Chain:**
   * **Tier 1 (Flagship Precision):** `gemini-3.8-flash` ➔ `gemini-3.7-flash` ➔ `gemini-3.6-flash` ➔ `gemini-3.5-flash` *(Presisi tinggi, batas 5 RPM)*.
   * **Tier 2 (Mid-Tier Workhorse):** `gemini-3.5-flash-lite` *(Latensi kencang, kuota badak, breakdown lengkap)*.
   * **Tier 3 (Emergency Fallback):** `gemini-3.1-flash-lite` *(Disiplin budget, pemrosesan cepat)*.

3. **Multi-Account API Key Rotator:**
   * Rotasi kunci API berbasis *Round-Robin* (`itertools.cycle`) untuk membagi beban *Rate Limit* (RPM/RPD) secara dinamis.

4. **In-Memory Caching System:**
   * Menyimpan hasil eksekusi berdasarkan kombinasi `Device_UseCase_Budget` dengan TTL 1 jam untuk respon instant (0ms) pada kueri berulang.

5. **UI Metadata & Transparency (Vue 3):**
   * Menampilkan *Badge Gacha Status* secara dinamis pada komponen frontend (`SpecResult.vue`) untuk memberikan transparansi model/tier AI yang memproses data.

---

## 🛠️ Tech Stack

* **Backend:** FastAPI, Python 3.11+, Pydantic v2, `google-genai` SDK.
* **Frontend:** Vue 3 (Composition API / `<script setup>`), Tailwind CSS, Vite.
* **State & Storage:** Vue Reactive State, HTML5 `localStorage` (Wishlist System).

---

## 🚀 Quick Start (Local Setup)

### 1. Backend Setup (FastAPI)

```bash
# Clone repository & masuk ke direktori backend
cd backend

# Buat virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install fastapi uvicorn pydantic python-dotenv google-genai

# Buat file .env dan isi API Key Gemini lu
cat <<EOT> .env
GEMINI_API_KEY_1="AIzaSy..."
GEMINI_API_KEY_2="AIzaSy..."
GEMINI_API_KEY_3="AIzaSy..."
EOT

# Jalankan server FastAPI
uvicorn main:app --reload --port 8000