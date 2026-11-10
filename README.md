# Brick Manufacturing Management System
**Django + SQLite3 | Lightweight Factory & Construction Material ERP**

A complete, production-ready, responsive business management web application built for brick and construction material manufacturing plants (producing hollow blocks, solid bricks, interlock pavers, etc.).

Designed specifically for zero-maintenance operation and turnkey deployment on **PythonAnywhere Free Tier**, using built-in Django components, SQLite3, Bootstrap 5, and WhiteNoise.

---

## Key Modules & Features

1. **Role-Based Access Control (RBAC)**
   - **Super Admin**: Full administrative and operational permissions (user creation, password resets, stock adjustments, dispatches, configuration).
   - **Accountant**: Customer outstanding balances, payment receipts, expense logging, credit tracking, financial statements (no destructive actions or user management).
   - **Owner (Read-Only)**: Real-time business KPI dashboards, inventory status, production and dispatch reports, client project progress, worker counts.
   - Enforced at both the view/backend level via custom decorators and dynamic template navigation.

2. **Factory Inventory & Product Purchases**
   - Live finished goods ledger calculated dynamically:
     $$\text{Current Stock} = \text{Opening} + \text{Production} + \text{Purchases/Additions} - \text{Dispatch} - \text{Deductions}$$
   - **Product Purchases Module**: Log incoming bought goods/raw stock with supplier invoices, automatically incrementing factory inventory and maintaining full audit trails.
   - Full movement transaction history, low-stock alerts, and atomic stock adjustments.

3. **Production Management**
   - Record daily manufacturing shifts (Morning, Afternoon, Night) with worker counts and output.
   - Atomic inventory updates and token-based duplicate submission prevention.
   - Edit production entries with automatic stock recalculation and negative stock prevention guards.

4. **Client & Account Management**
   - Customer registry with auto-generating client codes (`CLT-XXXX`).
   - Support for **Credit Accounts** (with credit limits and balance tracking) and **Cash Clients** (for direct-pay customers).
   - Complete 360° client profile: overview, dispatch history, client site stock, construction tracking, payments, and account ledger.

5. **Client Construction Site Tracking**
   - Track materials delivered to client sites and materials consumed on-site each day.
   - Formula:
     $$\text{Client Available Stock} = \text{Opening} + \text{Received (Dispatch)} - \text{Used}$$
   - Daily construction logs tracking progress %, worker attendance on-site, and material usage.

6. **Dispatch & Delivery Management**
   - Multi-item dispatch consignments with real-time price and stock checks.
   - Auto-deducts factory finished inventory and adds to client construction site stock (if linked).
   - Printable Delivery Challan / Tax Invoice vouchers.

7. **Finance, Billing & Expenses**
   - Record client payments with automatic or manual FIFO dispatch allocation.
   - Operating expense logging across customizable categories (Fuel, Wages, Electricity, Transport, Maintenance, etc.).
   - Client statements and outstanding balance management.

8. **Workers & Attendance**
   - Worker directory, roles (Mason, Operator, Helper, Driver, Supervisor), daily wage rates, and daily attendance records.

9. **Analytics & Reports**
   - Daily/monthly production reports, dispatch analytics, inventory audit ledger, sales summary, client outstanding balances, and expense breakdown.

---

## Tech Stack

- **Backend**: Python 3.10+ / Django 5+ / 6.0
- **Database**: SQLite3 (zero-configuration, single-file ACID storage)
- **Frontend**: HTML5, CSS3, Bootstrap 5, Bootstrap Icons, Vanilla JavaScript
- **Static Assets**: WhiteNoise for static file serving
- **Environment**: Compatible with standard Python virtual environments and PythonAnywhere Free

---

## Local Setup & Quickstart

```bash
# 1. Clone repository
git clone https://github.com/im-Abhiram/inventory.git
cd inventory

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Populate initial demonstration data (Users, Products, Inventory, Clients)
python manage.py seed_data

# 6. Start the development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

### Default Demonstration Logins

| Role | Username | Password |
|---|---|---|
| **Super Admin** | `admin` | `Admin@1234` |
| **Accountant** | `accountant` | `Accounts@1234` |
| **Owner** | `owner` | `Owner@1234` |

---

## PythonAnywhere Deployment

See the detailed step-by-step instructions in [PYTHONANYWHERE_DEPLOYMENT.md](file:///d:/thamarayyath%20inventory/PYTHONANYWHERE_DEPLOYMENT.md) for setting up the virtualenv, WSGI file configuration, static assets, and environment variables.

---

## Running Automated Tests

```bash
python manage.py test
```
All unit tests verify factory stock calculations, credit limits, cash clients, product purchases, and role-based permissions.
