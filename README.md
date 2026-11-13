# NEST KERALA – RENTAL HOME FINDER

**BCA Third Year Mini Project**

**Nest Kerala** is a modern, professional, fully functional, database-driven rental home finder web platform designed to help people discover suitable rental homes across all 14 districts of Kerala.

---

## 🌟 Key Project Highlights

1. **Innovative Smart Rental Home Matching Algorithm**
   - Transparent rule-based weighted recommendation engine:
     - **District Match:** 30%
     - **Budget Match:** 30%
     - **Bedrooms (BHK) Match:** 20%
     - **Preferred Square Feet Match:** 15%
     - **Town / Locality Match:** 5%
     - **Total:** 100%
   - Dynamically calculates and displays matching badges (e.g. `100% Match`, `95% Match`, `85% Match`).
   - Automatically recommends closest matching alternatives when exact criteria yield limited results.

2. **Coverage of All 14 Districts of Kerala (56+ Demo Properties)**
   - Includes **at least 4 distinct, fully specified rental properties per district**:
     - Thiruvananthapuram, Kollam, Pathanamthitta, Alappuzha, Kottayam, Idukki, Ernakulam, Thrissur, Palakkad, Malappuram, Kozhikode, Wayanad, Kannur, Kasaragod.
   - Varied realistic rents, security deposits, BHK options, property types, and facilities.
   - Realistic Kerala amenities: Open sweet well water, KWA connection, 3-Phase KSEB with inverter, rainwater harvesting, covered car porch.

3. **Prominent Monthly Rent Highlighting**
   - The monthly rent is visually prioritized on every property card with bold typography and strong contrast directly below the photograph and as a high-contrast overlay (`₹18,000 / month`).

4. **Interactive Location & Map Coordinates**
   - Embedded interactive **Leaflet.js / OpenStreetMap** map with custom Kerala green pin.
   - Direct **"Open in Google Maps"** navigation button with accurate GPS coordinates.
   - Categorized nearby landmarks with verified distances (Hospitals, Schools, Transit, Supermarkets).

5. **Direct Owner Contact & WhatsApp Click-to-Chat**
   - **Call Owner Button:** Direct `tel:` phone call integration.
   - **Chat on WhatsApp Button:** Opens WhatsApp Click-to-Chat with pre-filled enquiry message mentioning property title and ID.

6. **Tenant & Visitor Feedback System**
   - 1-to-5 star rating and review submission for authenticated users.
   - Dynamic calculation of average rating and total review counts.
   - Administrative review moderation and deletion.

7. **Secure Administrator Control Center**
   - Dedicated separate Admin Login (`/admin/login`).
   - 6 Live database statistical counters:
     1. Total Registered Users
     2. Total Rental Properties
     3. Available Properties
     4. Unavailable Properties
     5. Total Districts
     6. Total Feedback Reviews
   - **Feature A:** Add New Rental House with multi-photo upload.
   - **Feature B:** Edit Property Details.
   - **Feature C:** Manage Property Photographs (upload, delete, set primary cover).
   - **Feature D:** Manage Listings directory with search and district filtering.
   - **Feature E:** Manage User Feedback & Reviews.
   - **Feature F:** Delete Property with safe cascade cleanup.

---

## 🗄️ SQLite Database Schema (ER Diagram)

Implemented using strict relational integrity and foreign keys:

1. **`users`**: `user_id` (PK), `name`, `email` (UNIQUE), `password_hash`, `phone`, `role`, `created_at`
2. **`admins`**: `admin_id` (PK), `email` (UNIQUE), `password_hash`, `name`, `created_at`
3. **`owners`**: `owner_id` (PK), `name`, `phone`, `email`, `contact_type`, `created_at`
4. **`districts`**: `district_id` (PK), `district_name` (UNIQUE), `malayalam_name`, `image_path`, `description`
5. **`properties`**: `property_id` (PK), `owner_id` (FK), `district_id` (FK), `title`, `description`, `rent`, `deposit`, `bhk`, `area`, `address`, `landmarks`, `availability`, `town`, `pincode`, `bathrooms`, `furnishing`, `property_type`, `parking`, `water_supply`, `facilities`, `latitude`, `longitude`, `property_code`, `slug`, `created_at`
6. **`property_photos`**: `photo_id` (PK), `property_id` (FK), `photo_path`, `photo_type`, `is_primary`
7. **`reviews`**: `review_id` (PK), `user_id` (FK), `property_id` (FK), `rating`, `feedback`, `review_date`, `visit_type`, `water_rating`, `location_rating`, `landlord_rating`

---

## 🔑 Demonstration Login Credentials

| Role | Email | Password | Description |
|---|---|---|---|
| **Administrator** | `admin@nestkerala.com` | `admin123` | Full access to Admin Dashboard, Add/Edit/Delete Properties & Moderation |
| **Tenant User** | `rahul.nair@techkerala.com` | `Tenant@123` | Registered seeker account with review submission privileges |

---

## 🚀 How to Run in Visual Studio Code

### Method 1: Using the Batch Runner (One-Click)
Double-click `run.bat` in the project folder.

### Method 2: Manual Terminal Launch
1. Open the project folder in Visual Studio Code:
   ```bash
   cd "C:\HOME PROJECT\home pro"
   ```
2. Activate Python environment or install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```
