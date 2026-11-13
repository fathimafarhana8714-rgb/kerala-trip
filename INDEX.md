# NEST KERALA – RENTAL HOME FINDER
## Project Index & Comprehensive Directory Map
**Project Type:** BCA Third Year Mini Project  
**Platform:** Python Flask / SQLite Relational Database / Bootstrap 5 / Leaflet OSM  
**Location:** `C:\HOME PROJECT\home pro`  
**Live URL:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)  

---

## 1. Quick Launch & Execution

To run the Nest Kerala website locally:

```powershell
# Option A: One-click launcher (Windows)
Double-click "run.bat" in C:\HOME PROJECT\home pro

# Option B: Terminal / VS Code
cd "C:\HOME PROJECT\home pro"
python app.py
```

Once started, open your web browser at:  
👉 **`http://127.0.0.1:5000/`**  
👉 Or open **`index.html`** in this folder for the Project Launch Portal.

---

## 2. Directory & File Index

| File / Folder | Role / Description |
| :--- | :--- |
| **`index.html`** | Standalone HTML Project Portal & launcher with live server health indicator. |
| **`INDEX.md`** | This file: Complete table of contents, architecture, and route index. |
| **`app.py`** | Main Flask application, routing, session auth, search engine, CRUD endpoints. |
| **`models.py`** | Relational SQLAlchemy database models (`users`, `admins`, `owners`, `districts`, `properties`, `property_photos`, `reviews`). |
| **`helpers.py`** | Smart Rental Home Matching weighted algorithm (100%), authentication decorators, image sanitization. |
| **`seed_data.py`** | Database seeder: populates 14 Kerala districts, 56 rental homes, 336 photographs, owners, and reviews. |
| **`districts_data.py`** | Kerala geographical metadata, district descriptions, Malayalam names, coordinates. |
| **`run.bat`** | Windows batch file to launch the server with one click. |
| **`requirements.txt`** | Python dependencies (`Flask`, `Flask-SQLAlchemy`, `Pillow`, `Werkzeug`). |
| **`test_app.py`** | Automated test suite (14 unit/integration tests). |
| **`README.md`** | Detailed BCA mini-project documentation, viva questions, and setup guide. |
| **`instance/nestkerala.db`** | SQLite relational database pre-loaded with all demo properties and districts. |
| **`templates/`** | Jinja2 HTML templates for all views (Home, Listings, Details, Auth, Admin). |
| **`templates/index.html`** | Homepage template (Hero, 5-field smart search form, 14 clickable district cards). |
| **`templates/properties.html`** | Listings view with search filters, BHK/Budget criteria, and prominent rent cards. |
| **`templates/property_detail.html`** | Complete property details (Sections A–I): Gallery, specs, map, landmarks, WhatsApp. |
| **`templates/admin/`** | Admin portal templates: Dashboard, Property Form (Add/Edit), Photo Manager, Review Moderation. |
| **`templates/auth/`** | Login & Registration templates with full validation and password hashing. |
| **`static/css/`** | Custom stylesheets implementing the Kerala Heritage Palette (`#103D32`, `#087F5B`, `#D5AD62`). |
| **`static/js/`** | Clientside scripts (Live smart search, photo lightbox, interactive Leaflet maps). |
| **`static/images/`** | District hero banners, property photos (336 high-resolution Kerala house images). |

---

## 3. Demo Accounts & Test Credentials

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@nestkerala.com` | `admin123` | Full Admin Dashboard, Manage Properties, Upload/Delete Photos, Moderate Reviews |
| **Registered Tenant 1** | `rahul.nair@techkerala.com` | `Tenant@123` | Search, Favorite Homes, Submit Reviews & Star Ratings, WhatsApp Enquiry |
| **Registered Tenant 2** | `anjali.menon@keralastudent.org` | `Tenant@123` | Filter Budget Rentals, Submit Enquiries, Schedule Property Visits |

---

## 4. Key Innovative Features

1. **Smart Rental Home Matching Engine (`helpers.py`):**
   - Transparent rule-based weighted recommendation algorithm:
     - **District Match:** 30%
     - **Budget Match:** 30%
     - **BHK Match:** 20%
     - **Square Feet Area:** 15%
     - **Town / Locality:** 5%
     - **Total:** 100%
   - Displays dynamic percentage badges (e.g. `95% Match`, `88% Match`).
   - Automatically provides intelligent alternative recommendations if exact criteria return 0 results.

2. **All 14 Kerala Districts Covered:**
   - Thiruvananthapuram, Kollam, Pathanamthitta, Alappuzha, Kottayam, Idukki, Ernakulam, Thrissur, Palakkad, Malappuram, Kozhikode, Wayanad, Kannur, Kasaragod.
   - At least 4 distinct, verified rental properties per district (56 total properties, 336 photos).

3. **Prominent Monthly Rent Display:**
   - Prominently styled price badges (`₹XX,XXX / month`) directly below photographs and in contrast overlays.

4. **Direct Owner Contact:**
   - WhatsApp Click-to-Chat integration (`wa.me`) with prefilled property enquiry messages.
   - One-click phone calling (`tel:`) with verified owner credentials.

5. **Location & Maps:**
   - Interactive Leaflet.js with OpenStreetMap pins.
   - Verified distance measurements to nearby bus stands, railway stations, hospitals, and schools.

6. **Full Admin Control Panel:**
   - Live analytics & statistical counters.
   - Add/Edit property listings with photo upload.
   - Dedicated photo gallery manager (set primary photo, delete, reorder).
   - Review and feedback moderation.
