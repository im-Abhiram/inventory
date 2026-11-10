# PythonAnywhere Free Deployment Guide
## Brick Manufacturing Management System (Django + SQLite3)

**Account Username**: `thamarayyathproduction`  
**Live Web Address**: `https://thamarayyathproduction.pythonanywhere.com`  
**GitHub Repository**: `https://github.com/im-Abhiram/inventory.git`

This application is built for lightweight, reliable operation on **PythonAnywhere Free Tier** using Python, Django, SQLite3, and WhiteNoise. Follow these exact steps to deploy.

---

### Step-by-Step Deployment Instructions

#### 1. Open a Bash Console on PythonAnywhere
1. Log in at [https://www.pythonanywhere.com/](https://www.pythonanywhere.com/) as `thamarayyathproduction`.
2. Go to the **Consoles** tab.
3. Click on **Bash** to open a new terminal session.

---

#### 2. Clone Your GitHub Repository
Run the following commands in the Bash console:
```bash
cd ~
git clone https://github.com/im-Abhiram/inventory.git brick_management
cd ~/brick_management
```

Verify your project root files:
```bash
ls -la
```
*(You will see `manage.py`, `requirements.txt`, `brick_management/`, `templates/`, etc.)*

---

#### 3. Create and Activate the Virtual Environment
Create a dedicated virtualenv with Python 3.10:
```bash
mkvirtualenv --python=/usr/bin/python3.10 brick-env
```
*(Whenever you open a new console in the future, activate it using `workon brick-env`)*.

---

#### 4. Install Dependencies
Make sure `(brick-env)` is visible in your command prompt, then install the lightweight requirements:
```bash
pip install -r requirements.txt
```
*(Installs Django, WhiteNoise, and python-dotenv — fully compliant with free tier resource quotas)*.

---

#### 5. Initialize the Database & Collect Static Files
Run migrations to set up your SQLite database:
```bash
python manage.py migrate
```

Collect static assets into the production staticfiles directory:
```bash
python manage.py collectstatic --noinput
```

---

#### 6. Seed Demonstration Data or Create Super Admin
You can seed initial factory products, demo clients, and the three pre-configured roles:
```bash
python manage.py seed_data
```

**Default Seed Credentials:**
- **Super Admin**: `admin` / `Admin@1234`
- **Accountant**: `accountant` / `Accounts@1234`
- **Owner**: `owner` / `Owner@1234`

*(Alternatively or in addition, you can create a custom superuser by running `python manage.py createsuperuser`)*.

---

### Web Tab Configuration

#### 7. Create the Web Application
1. Click on the **Web** tab at the top of the PythonAnywhere dashboard.
2. Click the **Add a new web app** button.
3. If prompted about domain name, proceed with `thamarayyathproduction.pythonanywhere.com`.
4. Choose **Manual configuration** *(Important: Do NOT select the "Django" wizard, as you have already created the project)*.
5. Select **Python 3.10**.

---

#### 8. Set the Virtual Environment Path
Scroll down to the **Virtualenv** section of the Web tab:
- Click the edit button next to **Path to a virtualenv**
- Enter:
  ```text
  /home/thamarayyathproduction/.virtualenvs/brick-env
  ```
- Click the checkmark to save.

---

#### 9. Configure Static Files Mappings
Scroll down to the **Static files** section of the Web tab and enter:

| URL | Directory |
|---|---|
| `/static/` | `/home/thamarayyathproduction/brick_management/staticfiles/` |

---

#### 10. Configure the WSGI Configuration File
In the **Code** section of the Web tab, click the link next to **WSGI configuration file**:  
`/var/www/thamarayyathproduction_pythonanywhere_com_wsgi.py`

Delete all existing lines and replace them with this exact code:

```python
import os
import sys

# Path to the project root directory
path = '/home/thamarayyathproduction/brick_management'
if path not in sys.path:
    sys.path.append(path)

# Django environment settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'brick_management.settings'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_SECRET_KEY'] = 'thamarayyath-secret-key-prod-2026-secure-factory-erp'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Click **Save** in the top right corner.

---

#### 11. Reload and Launch the Application
1. Return to the **Web** tab.
2. Click the large green button: **Reload thamarayyathproduction.pythonanywhere.com**.
3. Open your browser and navigate to:  
   👉 **[https://thamarayyathproduction.pythonanywhere.com](https://thamarayyathproduction.pythonanywhere.com)**
4. Log in using `admin` / `Admin@1234` (or your created superuser).

---

### Routine Maintenance & Database Backups

#### Updating Code in the Future
Whenever you push changes to GitHub, pull the updates on PythonAnywhere:
```bash
cd ~/brick_management
git pull origin main
python manage.py migrate
python manage.py collectstatic --noinput
```
Then click **Reload** in the **Web** tab.

#### Timestamped SQLite Database Backup
Since SQLite stores all data in a single portable file (`db.sqlite3`), you can take instant point-in-time backups in the Bash console:
```bash
mkdir -p ~/backups
cp ~/brick_management/db.sqlite3 ~/backups/db_backup_$(date +%F_%H%M%S).sqlite3
```
You can also download `db.sqlite3` directly to your local computer via PythonAnywhere's **Files** tab at any time.

---

### User Roles Overview
| Role | Access Level | Permissions |
|---|---|---|
| **Super Admin** | Full Admin | Create/edit user accounts, change passwords, manage products, stock adjustments, record production & production edits, record dispatch, manage construction tracking, payments, credit limits, expenses, and view all reports. |
| **Accountant** | Financials | View products, stock, dispatches, and construction progress; record customer payments; record operating expenses; manage outstanding client credit balances and view financial statements. *(Cannot create users or alter production logs)*. |
| **Owner** | Read-Only Audit | Executive dashboard with date filtering (Today, This Week, This Month, Custom Date Range), view stock holding, production logs, dispatches, customer sites, and financial summary. *(Strictly read-only; no modification rights)*. |
