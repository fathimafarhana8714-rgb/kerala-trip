import os
import uuid
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.utils import secure_filename
from models import db, User, Admin, Property, District

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder):
    if not file or file.filename == '':
        return None
    if allowed_file(file.filename):
        unique_name = f"{uuid.uuid4().hex[:12]}_{secure_filename(file.filename)}"
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_name)
        file.save(file_path)
        return f"/static/uploads/properties/{unique_name}"
    return None

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def get_current_admin():
    admin_id = session.get('admin_id')
    if admin_id:
        return db.session.get(Admin, admin_id)
    # Fallback: check if logged in as user with role 'admin'
    user_id = session.get('user_id')
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.is_admin():
            return user
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'admin_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' in session:
            return f(*args, **kwargs)
        if 'user_id' in session:
            user = db.session.get(User, session['user_id'])
            if user and user.is_admin():
                return f(*args, **kwargs)
        flash("Admin authorization required to access the Admin Control Center.", "danger")
        return redirect(url_for('admin_login', next=request.url))
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' in session:
                return f(*args, **kwargs)
            if 'user_id' not in session:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for('login', next=request.url))
            user = db.session.get(User, session['user_id'])
            if not user or (user.role not in roles and user.role != 'admin'):
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Neighboring/Regional district affinity for smart location similarity
DISTRICT_NEIGHBORS = {
    "Ernakulam": ["Thrissur", "Kottayam", "Alappuzha", "Idukki"],
    "Thiruvananthapuram": ["Kollam"],
    "Kollam": ["Thiruvananthapuram", "Pathanamthitta", "Alappuzha"],
    "Pathanamthitta": ["Kollam", "Alappuzha", "Kottayam", "Idukki"],
    "Alappuzha": ["Ernakulam", "Kottayam", "Pathanamthitta", "Kollam"],
    "Kottayam": ["Ernakulam", "Idukki", "Alappuzha", "Pathanamthitta"],
    "Idukki": ["Ernakulam", "Kottayam", "Thrissur", "Pathanamthitta"],
    "Thrissur": ["Ernakulam", "Palakkad", "Malappuram", "Idukki"],
    "Palakkad": ["Thrissur", "Malappuram"],
    "Malappuram": ["Kozhikode", "Palakkad", "Thrissur", "Wayanad"],
    "Kozhikode": ["Kannur", "Malappuram", "Wayanad"],
    "Wayanad": ["Kozhikode", "Kannur", "Malappuram"],
    "Kannur": ["Kasaragod", "Kozhikode", "Wayanad"],
    "Kasaragod": ["Kannur"]
}

def calculate_smart_match(property_obj, pref_district=None, max_budget=None, pref_bhk=None, pref_area=None, locality_query=None):
    """
    Transparent rule-based weighted matching algorithm (Total 100%):
    - District Match: 30%
    - Budget Match: 30%
    - BHK Match: 20%
    - Square Feet Match: 15%
    - Locality Match: 5%
    Returns integer percentage (5 to 100).
    """
    district_score = 0.0
    budget_score = 0.0
    bhk_score = 0.0
    area_score = 0.0
    locality_score = 0.0

    # 1. District Match (30%)
    if pref_district and pref_district.strip():
        prop_dist = property_obj.district.strip().lower()
        target_dist = pref_district.strip().lower()
        if prop_dist == target_dist:
            district_score = 30.0
        elif property_obj.district in DISTRICT_NEIGHBORS.get(pref_district, []):
            district_score = 15.0 # Neighboring district gets partial score
        else:
            district_score = 0.0
    else:
        district_score = 30.0

    # 2. Budget Match (30%)
    if max_budget and max_budget > 0:
        if property_obj.rent <= max_budget:
            budget_score = 30.0
        else:
            diff = property_obj.rent - max_budget
            tolerance = max_budget * 0.40 # Within 40% over budget
            if diff < tolerance:
                budget_score = max(0.0, 30.0 * (1.0 - (diff / tolerance)))
            else:
                budget_score = 0.0
    else:
        budget_score = 30.0

    # 3. BHK Match (20%)
    if pref_bhk and pref_bhk > 0:
        if property_obj.bhk == pref_bhk:
            bhk_score = 20.0
        elif abs(property_obj.bhk - pref_bhk) == 1:
            bhk_score = 10.0
        else:
            bhk_score = 0.0
    else:
        bhk_score = 20.0

    # 4. Square Feet Match (15%)
    if pref_area and pref_area > 0:
        diff = abs(property_obj.area - pref_area)
        tolerance = pref_area * 0.50
        if diff <= pref_area * 0.10: # Within 10%
            area_score = 15.0
        elif diff < tolerance:
            area_score = max(0.0, 15.0 * (1.0 - (diff / tolerance)))
        else:
            area_score = 0.0
    else:
        area_score = 15.0

    # 5. Locality Match (5%)
    if locality_query and locality_query.strip():
        q = locality_query.strip().lower()
        text = f"{property_obj.town} {property_obj.address} {property_obj.landmarks or ''}".lower()
        if q in text:
            locality_score = 5.0
        else:
            locality_score = 0.0
    else:
        locality_score = 5.0

    total_pct = round(district_score + budget_score + bhk_score + area_score + locality_score)
    return max(10, min(100, total_pct))

def get_smart_recommendations(criteria, exclude_ids=None, limit=4):
    """
    Ranks alternative properties based on criteria when exact matches are few or zero.
    """
    if exclude_ids is None:
        exclude_ids = []

    target_district = criteria.get('district')
    target_rent = criteria.get('rent') or criteria.get('max_rent')
    target_bhk = criteria.get('bhk')
    target_area = criteria.get('area')
    locality_query = criteria.get('q')

    try:
        trent = float(target_rent) if target_rent else None
    except (ValueError, TypeError):
        trent = None

    try:
        tbhk = int(target_bhk) if target_bhk else None
    except (ValueError, TypeError):
        tbhk = None

    try:
        tarea = int(target_area) if target_area else None
    except (ValueError, TypeError):
        tarea = None

    query = Property.query.filter(Property.availability == 'Available')
    if exclude_ids:
        query = query.filter(~Property.property_id.in_(exclude_ids))

    all_candidates = query.all()
    if not all_candidates:
        return []

    scored_candidates = []
    for prop in all_candidates:
        match_score = calculate_smart_match(
            prop,
            pref_district=target_district,
            max_budget=trent,
            pref_bhk=tbhk,
            pref_area=tarea,
            locality_query=locality_query
        )
        prop.match_percentage = match_score
        scored_candidates.append(prop)

    scored_candidates.sort(key=lambda p: getattr(p, 'match_percentage', 0), reverse=True)
    return scored_candidates[:limit]
