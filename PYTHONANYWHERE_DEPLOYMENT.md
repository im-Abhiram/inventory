# PythonAnywhere Free Deployment Guide
## Brick Manufacturing Management System (Django + SQLite3)

This application is built specifically for low-overhead, reliable operation on **PythonAnywhere Free Tier** using Python, Django, SQLite3, and WhiteNoise.

---

### Prerequisites
- A free account on [PythonAnywhere](https://www.pythonanywhere.com/) (Username: `yourusername`).
- Your default web address will be: `https://yourusername.pythonanywhere.com`.

---

### Step-by-Step Deployment Instructions

#### 1. Open a Bash Console on PythonAnywhere
From the PythonAnywhere dashboard, click on **Consoles** &rarr; Start a new **Bash** console.

#### 2. Clone or Upload the Codebase
In the Bash console, clone your repository or upload your files into your home directory:
```bash
cd ~
git clone <your-git-repository-url> brick_management
# Or if uploaded as a zip:
# unzip brick_management.zip -d brick_management
cd ~/brick_management
```

Verify your project root contains:
```bash
ls -la
# You should see: manage.py, requirements.txt, brick_management/, static/, templates/, etc.
```

#### 3. Create and Activate a Virtual Environment
```bash
mkvirtualenv --python=/usr/bin/python3.10 brick-env
# Or with python 3.11:
# mkvirtualenv --python=/usr/bin/python3.11 brick-env
```
Once activated, your terminal prompt will show `(brick-env)`.

#### 4. Install Dependencies
```bash
pip install -r requirements.txt
```
*(All packages are lightweight and strictly compatible with PythonAnywhere free resource quotas).*

#### 5. Configure Django Environment & Database
Run migrations to create the local SQLite database in your project directory:
```bash
python manage.py migrate
```

Collect static files for production serving:
```bash
python manage.py collectstatic --noinput
```

#### 6. Create Super Admin User or Seed Demo Data
You can either create your own administrator account:
```bash
python manage.py createsuperuser
```
Or seed initial factory products, demo clients, and sample roles:
```bash
python manage.py seed_data
```
*(Note: If you run `seed_data`, remember to change passwords immediately from the user management screen).*

---

### Web App Configuration in PythonAnywhere Web Tab

#### 7. Create a Web App
1. Go to the **Web** tab in PythonAnywhere dashboard.
2. Click **Add a new web app**.
3. Choose **Manual configuration** (do NOT choose the default Django wizard, as you already have your project configured).
4. Select Python version matching your virtualenv (e.g. **Python 3.10** or **Python 3.11**).

#### 8. Configure Virtual Environment Path
Scroll to the **Virtualenv** section in the **Web** tab and set the path to:
```text
/home/yourusername/.virtualenvs/brick-env
```
*(Replace `yourusername` with your actual PythonAnywhere account name).*

#### 9. Configure Static Files
In the **Static files** section of the Web tab, enter:
- **URL**: `/static/`
- **Directory**: `/home/yourusername/brick_management/staticfiles/`

#### 10. Configure WSGI File
Click on the **WSGI configuration file** link (e.g. `/var/www/yourusername_pythonanywhere_com_wsgi.py`).

Delete all default boilerplate code and replace it with:
```python
import os
import sys

# Path to your project directory
path = '/home/yourusername/brick_management'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables for production
os.environ['DJANGO_SETTINGS_MODULE'] = 'brick_management.settings'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_SECRET_KEY'] = 'your-secure-production-secret-key-change-this'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
*(Replace `yourusername` with your PythonAnywhere username and save the file).*

#### 11. Reload and Test
1. Return to the **Web** tab.
2. Click the green **Reload yourusername.pythonanywhere.com** button.
3. Open `https://yourusername.pythonanywhere.com` in your browser.
4. Log in using your Super Admin credentials.

---

### SQLite3 Database Backup Procedure
Since SQLite stores everything in a single portable file (`db.sqlite3` located inside `~/brick_management/`), backups are simple and safe.

To create an instant timestamped backup in Bash:
```bash
mkdir -p ~/backups
cp ~/brick_management/db.sqlite3 ~/backups/db_backup_$(date +%F_%H%M%S).sqlite3
```
You can download backups directly from PythonAnywhere's **Files** tab at any time to keep an offline local copy.

---

### User Roles Overview
| Role | Access Level | Permissions |
|---|---|---|
| **Super Admin** | Full Admin | Create/edit user accounts, change passwords, manage products, stock adjustments, record production, record dispatch, manage construction tracking, payments, credit limits, expenses, and view all reports. |
| **Accountant** | Financials | View products, stock, dispatches, and construction progress; record customer payments; record operating expenses; manage outstanding client credit balances and view financial statements. *(Cannot create users or alter production)*. |
| **Owner** | Read-Only Audit | Executive dashboard with date filtering (Today, This Week, This Month, Custom Date Range), view stock holding, production logs, dispatches, customer sites, and financial summary. *(Strictly read-only; no modification rights)*. |

