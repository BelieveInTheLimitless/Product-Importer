# 📦 Product Importer

A fast, Docker-powered CSV product importer built with **FastAPI**, **Celery**, **PostgreSQL**, and **Redis**, featuring a clean, minimal web UI.

🔗 **Live Deployment:**  
https://product-importer-ppsn.onrender.com

---

## 🚀 Features

- 📤 Upload CSV files (`name, sku, description, active-inactive status`)
- ⚙️ Background processing using Celery
- ⏳ Real-time import status polling
- 🔍 Product search + pagination
- 🔄 Active / Inactive toggle
- 🗑️ Bulk delete all products
- 🖥️ Simple HTML + JS frontend served by FastAPI

---

## 🛠️ Tech Stack

- **FastAPI**
- **PostgreSQL**
- **Redis**
- **Celery**
- **Docker & Docker Compose**
- **SQLAlchemy**
- **HTML / CSS / JavaScript**

---

## 🐳 Local Setup (Docker Only)

### 1. Clone the repo
```bash
git clone https://github.com/BelieveInTheLimitless/Product-Importer.git
cd Product-Importer
```

### 2. Create `.env`
```env
DATABASE_URL=postgresql://postgres:pass123@db:5432/product_db
REDIS_URL=redis://redis:6379/0
```

### 3. Start everything
```bash
docker compose up --build
```

Your app is now running at:
```
http://localhost:8000
```

---

## 📄 CSV Format

```csv
name,sku,description
Product A,SKU001,Sample description
Product B,SKU002,Another description
```

---

## 🔌 Key API Endpoints

| Method | Endpoint                          | Description |
|--------|------------------------------------|-------------|
| POST   | `/api/uploads/`                    | Upload a CSV file |
| GET    | `/api/uploads/status/{task_id}`    | Check import status |
| GET    | `/api/products/`                   | List products |
| DELETE | `/api/products/delete-all`         | Bulk delete all products |
| PATCH  | `/api/products/{id}/toggle`        | Toggle active state |

---