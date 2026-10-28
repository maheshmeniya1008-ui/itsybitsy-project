# 🛍️ Itsybitsy Product Intelligence & Automated Scraping System
### Comprehensive Technical Architecture & Client Presentation Documentation

---

## 1. Executive Summary
The **ItsybitsyProject** is an enterprise-grade automated web scraping, data transformation, RESTful API, and business analytics solution tailored for e-commerce platforms (specifically **Itsybitsy.in**). 

The system continuously crawls and extracts real-time product data (names, brands, categories, stock availability, regular and promotional prices), persists structured records into **Microsoft SQL Server**, and exposes high-performance REST APIs secured with API keys. In addition, it features an interactive **Streamlit Analytics Dashboard** and an on-demand **Cloudflare Tunnel** for live, zero-configuration public client demonstrations.

---

## 2. Tools & Technology Stack

| Category | Tool / Technology | Purpose & Business Value |
|---|---|---|
| **Core Language** | Python 3.10+ | End-to-end scraper pipeline, database adapters, REST API, and data aggregation |
| **Database Engine** | Microsoft SQL Server (MS SQL) | Enterprise relational storage ensuring ACID compliance and relational integrity |
| **API Framework** | FastAPI & Uvicorn | High-throughput asynchronous REST API engine with automated OpenAPI (Swagger) generation |
| **Analytics & UI** | Streamlit & Plotly | Real-time interactive executive dashboard, charts, KPI meters, and business analytics |
| **Secure Tunneling** | Cloudflare Tunnel (`cloudflared.exe`) | Secure HTTPS public exposure without complex firewall or port-forwarding requirements |
| **Automation & Jobs** | Daily Job Pipeline / Background Scraper | Scheduled automated scrapers, price change detection, and audit logging |

---

## 3. Libraries & Dependencies

| Library | Role in Project |
|---|---|
| `fastapi` | Modern, high-performance web framework for building RESTful APIs with Pydantic validation |
| `uvicorn` | Production-grade lightning-fast ASGI web server implementation |
| `pyodbc` | Low-overhead ODBC driver interface connecting Python directly with Microsoft SQL Server |
| `beautifulsoup4` (`bs4`) | Robust HTML parser for extracting product meta details, schema JSON, and prices |
| `requests` | Resilient HTTP client for network requests, web crawling, and session handling |
| `python-dotenv` | Secure environment variable management keeping credentials and secrets safe (`.env`) |
| `streamlit` | Modern web application framework for rapid delivery of interactive data dashboards |
| `pandas` | High-efficiency tabular data manipulation, filtering, and aggregation |
| `plotly` | Interactive data visualization library for pricing trends, discount distributions, and stock charts |

---

## 4. Database Schema & Tables

Database Name: **`ItsybitsyDB`** (Schema: `dbo`)

1. **`dbo.Products`**:
   - Stores core product identity and metadata (`ProductID`, `SourceProductID`, `ProductName`, `Brand`, `Category`, `PackSize`, `Variation`, `CreatedAt`, `UpdatedAt`).
2. **`dbo.ProductPrices`**:
   - Stores current pricing information (`PriceID`, `ProductID`, `RegularPrice`, `PromotionalPrice`, `Currency`, `DiscountPercentage`, `UpdatedAt`).
3. **`dbo.ProductAvailability`**:
   - Tracks stock and fulfillment status (`AvailabilityID`, `ProductID`, `InStock`, `Retailer`, `DeliveryAvailable`, `PickupAvailable`, `City`, `ZipCode`).
4. **`dbo.ProductHistory`**:
   - Complete audit trail tracking historical price fluctuations and stock changes over time (`HistoryID`, `ProductID`, `ChangeType`, `OldValue`, `NewValue`, `ChangedAt`).
5. **`dbo.CollectionJobs`**:
   - Job monitoring and scheduler telemetry (`JobID`, `Status`, `StartedAt`, `CompletedAt`, `ItemsCollected`, `ErrorMessage`).
6. **`dbo.CollectionRecords`**:
   - Detailed per-item scraping log and execution status.
7. **`dbo.ApiKeys`**:
   - API client authentication and authorization token management (`KeyID`, `ApiKey`, `ClientName`, `IsActive`, `CreatedAt`).

---

## 5. REST API Architecture & Endpoints

All external and client-facing endpoints can be authenticated via client API keys passed in headers, query parameters, or secured path tokens.

### A. Health & Diagnostics
- `GET /` — API service heartbeat and welcome banner.
- `GET /health/db` — Live Microsoft SQL Server database connectivity check.

### B. Core Product Management
- `GET /products` — Retrieve all products with pagination, search, brand, and category filters.
- `GET /products/{product_id}` — Retrieve complete details (info, price, stock) of a specific product.
- `POST /products` — Create a new product entry in the catalog.
- `PUT /products/{product_id}` — Update existing product metadata.
- `PUT /products/{product_id}/price` — Update price details for a product.
- `GET /products/{product_id}/price` — Retrieve current price for a product.
- `POST /products/{product_id}/availability` — Record real-time stock/availability details.

### C. Client & Partner Integration Endpoints
- `GET /itsy_bitsyAPI/{security_key}/products/categories` — List all scraped product categories.
- `GET /itsy_bitsyAPI/{security_key}/products/category/{category_slug}` — Fetch products by category (e.g., `mdf-collection`).
- `GET /itsy_bitsyAPI/{security_key}/products` — Authenticated full product catalog access.

### D. Business Intelligence & Price Alerts
- `GET /products/analytics/stats` — Executive KPI summary (average discount, catalog size, price dispersion).
- `GET /products/price-alerts` — List of products that recently encountered price drops or significant alterations.
- `GET /products/{product_id}/history` — Historical price trend analysis for competitor intelligence.

### E. Admin & On-Demand Execution
- `POST /scraper/trigger` — Trigger the background scraper pipeline asynchronously on demand.
- `POST /admin/api-keys` — Issue a new client access key.
- `GET /admin/api-keys` — List all active client keys.

---

## 6. How to Run the Project (Step-by-Step Guide)

### Prerequisites
- Python 3.10 or higher
- Microsoft SQL Server installed and running with `ItsybitsyDB` database configured
- Valid `.env` configuration file containing database credentials

---

### Step 1: Environment Activation & Dependencies
Open PowerShell or Command Prompt in the project root directory:
```powershell
# Activate Python Virtual Environment
.\venv\Scripts\activate

# Install required packages (if not already installed)
pip install -r requirements.txt
```

---

### Step 2: Data Scraping & Ingestion Pipeline
To crawl products and sync them into Microsoft SQL Server:
```powershell
# Run the complete automated daily job (collects URLs and updates database)
python daily_mdf_job.py

# Alternatively, run components separately:
python collect_mdf_urls.py          # Step 2a: Collect product URLs
python multi_product_collector.py   # Step 2b: Scrape details and persist to DB
```

---

### Step 3: Launch Local FastAPI Server
Run the RESTful API server:
```powershell
python -m uvicorn app:app --reload --port 8000
```
- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Database Health Check**: [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)

---

### Step 4: Launch Interactive Analytics Dashboard
To open the executive analytics and visualization dashboard:
```powershell
streamlit run dashboard.py
```
- The dashboard will automatically launch in your browser at: [http://localhost:8501](http://localhost:8501)
- Features include: KPI metrics, pricing charts, category filters, and product inspection tables.

---

### Step 5: Live Public Client Demonstration (Cloudflare Tunnel)
To demonstrate the live REST APIs to clients without deploying to cloud servers:
```powershell
python start_live_api.py
```
- This utility starts an encrypted Cloudflare Tunnel and prints a public HTTPS URL (e.g., `https://random-subdomain.trycloudflare.com`).
- The client can directly access the API endpoints and test integrations from anywhere on the internet.

---

## 7. Key Value Propositions for Client Presentation

1. **Automated Market Intelligence**: Zero manual effort required to track thousands of products, category listings, and price points.
2. **Historical Price & Stock Trend Tracking**: Allows clients to analyze pricing behavior, discounts, and competitor stock movements over time.
3. **Enterprise-Grade Architecture**: Built on robust technologies (MS SQL Server, FastAPI, Streamlit) guaranteeing stability, security, and auditability.
4. **Instant Integration Ready**: Standardized JSON RESTful APIs allowing seamless integration with ERP systems, mobile applications, or third-party platforms.
5. **Real-time Live Demonstration**: Instant remote demonstration capability via Cloudflare Tunnel, giving clients immediate confidence in the solution.
