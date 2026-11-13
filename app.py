import os
from datetime import datetime, timezone
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort, send_from_directory
)
from werkzeug.security import check_password_hash, generate_password_hash
from models import (
    db, User, Admin, Owner, District, Property,
    PropertyPhoto, Review, Favorite, Enquiry, VisitRequest, PropertyReport
)
from seed_data import seed_database, KERALA_DISTRICTS
from districts_data import KERALA_DISTRICTS_INFO
from helpers import (
    get_current_user, get_current_admin, login_required,
    admin_required, role_required, save_uploaded_file,
    calculate_smart_match, get_smart_recommendations
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nestkerala-super-secure-production-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nestkerala.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'properties')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload

db.init_app(app)

# Inject current user, admin, language, districts, and counts into all Jinja templates
@app.context_processor
def inject_global_vars():
    curr_user = get_current_user()
    curr_admin = get_current_admin()
    lang = session.get('lang', 'en')
    
    # User's favorited property IDs
    fav_ids = set()
    if curr_user:
        fav_ids = {f.property_id for f in Favorite.query.filter_by(user_id=curr_user.user_id).all()}
    else:
        fav_ids = set(session.get('guest_favorites', []))
        
    compare_ids = session.get('compare_ids', [])

    # Calculate actual listing count for each district
    district_counts = {}
    for d in District.query.all():
        cnt = Property.query.filter_by(district_id=d.district_id, availability='Available').count()
        district_counts[d.district_name] = cnt

    return {
        'current_user': curr_user,
        'current_admin': curr_admin,
        'is_admin_logged_in': bool(curr_admin),
        'current_lang': lang,
        'districts_info': KERALA_DISTRICTS_INFO,
        'kerala_districts': KERALA_DISTRICTS,
        'district_counts': district_counts,
        'fav_ids': fav_ids,
        'compare_ids': compare_ids,
        'now': datetime.now(timezone.utc)
    }


# -------------------------------------------------------------
# Static & Utility Routes
# -------------------------------------------------------------

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'images'),
        'logo.svg',
        mimetype='image/svg+xml'
    )

@app.route('/saved')
def saved_redirect():
    return redirect(url_for('saved_homes'))

@app.route('/owner/dashboard')
def owner_dashboard_redirect():
    return redirect(url_for('owner_dashboard'))

@app.route('/admin/dashboard')
def admin_dashboard_redirect():
    return redirect(url_for('admin_dashboard'))


# -------------------------------------------------------------
# Public & Exploration Routes
# -------------------------------------------------------------

@app.route('/')
def index():
    # Featured properties
    featured_properties = Property.query.filter_by(
        availability='Available',
        is_featured=True
    ).order_by(Property.property_id.desc()).limit(6).all()

    if len(featured_properties) < 3:
        featured_properties = Property.query.filter_by(
            availability='Available'
        ).order_by(Property.property_id.desc()).limit(6).all()

    # Recent properties
    recent_properties = Property.query.filter_by(
        availability='Available'
    ).order_by(Property.property_id.desc()).limit(6).all()

    # Budget-friendly rental homes (<= Rs 20,000)
    budget_properties = Property.query.filter(
        Property.availability == 'Available',
        Property.rent <= 20000
    ).order_by(Property.rent.asc()).limit(6).all()

    return render_template(
        'index.html',
        featured_properties=featured_properties,
        recent_properties=recent_properties,
        budget_properties=budget_properties
    )


@app.route('/properties')
def properties():
    query_text = request.args.get('q', '').strip()
    district_param = request.args.get('district', '').strip()
    property_type = request.args.get('property_type', '').strip()
    bhk = request.args.get('bhk', '').strip()
    min_rent = request.args.get('min_rent', '').strip()
    max_rent = request.args.get('max_rent', '').strip()
    area_pref = request.args.get('area', '').strip()
    furnishing = request.args.get('furnishing', '').strip()
    parking = request.args.get('parking', '').strip()
    pet_friendly = request.args.get('pet_friendly', '').strip()
    verified_only = request.args.get('verified_only', '').strip()
    sort_by = request.args.get('sort', 'smart').strip() # Default to smart matching when searched

    base_query = Property.query

    # Status: default to available or show all
    show_all_status = request.args.get('include_rented', '0')
    if show_all_status != '1':
        base_query = base_query.filter(Property.availability == 'Available')

    # Apply district filter
    if district_param:
        dist_record = District.query.filter(District.district_name.ilike(f"%{district_param}%")).first()
        if dist_record:
            base_query = base_query.filter(Property.district_id == dist_record.district_id)

    if property_type:
        base_query = base_query.filter(Property.property_type.ilike(f"%{property_type}%"))

    if bhk:
        try:
            bhk_val = int(bhk)
            if bhk_val >= 4:
                base_query = base_query.filter(Property.bhk >= 4)
            else:
                base_query = base_query.filter(Property.bhk == bhk_val)
        except ValueError:
            pass

    if min_rent:
        try:
            base_query = base_query.filter(Property.rent >= int(min_rent))
        except ValueError:
            pass

    if max_rent:
        try:
            base_query = base_query.filter(Property.rent <= int(max_rent))
        except ValueError:
            pass

    if furnishing:
        base_query = base_query.filter(Property.furnishing.ilike(f"%{furnishing}%"))

    if parking:
        base_query = base_query.filter(Property.parking.ilike(f"%{parking}%"))

    if verified_only == '1':
        base_query = base_query.filter(Property.is_verified == True)

    if query_text:
        term = f"%{query_text}%"
        base_query = base_query.filter(
            db.or_(
                Property.title.ilike(term),
                Property.town.ilike(term),
                Property.address.ilike(term),
                Property.property_code.ilike(term),
                Property.landmarks.ilike(term)
            )
        )

    # Execute query
    properties_list = base_query.all()
    exact_matches_count = len(properties_list)

    # Parse numeric targets for Smart Matching
    budget_val = None
    if max_rent:
        try:
            budget_val = int(max_rent)
        except ValueError:
            pass
    elif min_rent:
        try:
            budget_val = int(min_rent)
        except ValueError:
            pass

    bhk_val = None
    if bhk:
        try:
            bhk_val = int(bhk)
        except ValueError:
            pass

    area_val = None
    if area_pref:
        try:
            area_val = int(area_pref)
        except ValueError:
            pass

    # Check if user entered any preferences for Smart Matching
    has_preferences = bool(district_param or query_text or bhk_val or budget_val or area_val)

    # Calculate dynamic Smart Match percentage for every property
    for prop in properties_list:
        if has_preferences:
            score = calculate_smart_match(
                prop,
                pref_district=district_param,
                max_budget=budget_val,
                pref_bhk=bhk_val,
                pref_area=area_val,
                locality_query=query_text
            )
            prop.match_percentage = score
        else:
            prop.match_percentage = None

    # Sorting
    if sort_by == 'lowest_rent':
        properties_list.sort(key=lambda p: p.rent)
    elif sort_by == 'highest_rent':
        properties_list.sort(key=lambda p: p.rent, reverse=True)
    elif sort_by == 'area_desc':
        properties_list.sort(key=lambda p: p.area, reverse=True)
    elif sort_by == 'newest':
        properties_list.sort(key=lambda p: p.property_id, reverse=True)
    else: # 'smart'
        if has_preferences:
            properties_list.sort(key=lambda p: (getattr(p, 'match_percentage', 0) or 0), reverse=True)
        else:
            properties_list.sort(key=lambda p: p.property_id, reverse=True)

    # Smart Recommendation System:
    # If exact matches are zero or low (< 2), rank and recommend alternative homes!
    recommended_properties = []
    if exact_matches_count < 2 and has_preferences:
        criteria = {
            'district': district_param if district_param else None,
            'max_rent': budget_val,
            'bhk': bhk_val,
            'area': area_val,
            'q': query_text if query_text else None
        }
        exclude_ids = [p.property_id for p in properties_list]
        recommended_properties = get_smart_recommendations(criteria, exclude_ids=exclude_ids, limit=4)

    return render_template(
        'properties.html',
        properties=properties_list,
        exact_matches_count=exact_matches_count,
        recommended_properties=recommended_properties,
        selected_district=district_param,
        selected_bhk=bhk,
        selected_type=property_type,
        min_rent=min_rent,
        max_rent=max_rent,
        selected_area=area_pref,
        selected_furnishing=furnishing,
        selected_parking=parking,
        pet_friendly=pet_friendly,
        verified_only=verified_only,
        query_text=query_text,
        sort_by=sort_by
    )


@app.route('/district/<int:district_id>')
def district_detail(district_id):
    district = District.query.get_or_404(district_id)
    return redirect(url_for('properties', district=district.district_name))


@app.route('/property/<int:property_id>')
@app.route('/property/<int:property_id>/<slug>')
def property_detail(property_id, slug=None):
    prop = Property.query.get_or_404(property_id)

    # Track recently viewed in session
    recent = session.get('recently_viewed', [])
    if property_id in recent:
        recent.remove(property_id)
    recent.insert(0, property_id)
    session['recently_viewed'] = recent[:6]

    # Similar properties in the same district or neighboring
    similar_properties = Property.query.filter(
        Property.availability == 'Available',
        Property.property_id != prop.property_id,
        Property.district_id == prop.district_id
    ).limit(3).all()

    if len(similar_properties) < 3:
        more_props = Property.query.filter(
            Property.availability == 'Available',
            Property.property_id != prop.property_id,
            ~Property.property_id.in_([p.property_id for p in similar_properties])
        ).limit(3 - len(similar_properties)).all()
        similar_properties.extend(more_props)

    # All photos ordered (primary first)
    images = prop.photos.order_by(PropertyPhoto.is_primary.desc(), PropertyPhoto.photo_id.asc()).all()

    return render_template(
        'property_detail.html',
        property=prop,
        images=images,
        landmarks=prop.get_landmarks_parsed(),
        similar_properties=similar_properties
    )


# -------------------------------------------------------------
# Interactions: Feedback, Enquiry, Visit Scheduling, Reporting
# -------------------------------------------------------------

@app.route('/property/<int:property_id>/feedback', methods=['GET', 'POST'])
def property_feedback(property_id):
    prop = Property.query.get_or_404(property_id)
    curr_user = get_current_user()

    if request.method == 'POST':
        reviewer_name = request.form.get('reviewer_name', '').strip()
        reviewer_email = request.form.get('reviewer_email', '').strip()
        rating = request.form.get('rating', 5, type=int)
        visit_type = request.form.get('visit_type', 'Visited in Person').strip()
        headline = request.form.get('headline', '').strip()
        comment = request.form.get('comment', '').strip()
        
        water_rating = request.form.get('water_rating', 5, type=int)
        location_rating = request.form.get('location_rating', 5, type=int)
        landlord_rating = request.form.get('landlord_rating', 5, type=int)

        if not reviewer_name or not comment:
            flash("Please provide your name and your feedback comments.", "danger")
            return redirect(url_for('property_feedback', property_id=prop.property_id))

        # Check or create user if guest
        user_for_review = curr_user
        if not user_for_review:
            # Check if user with that email exists
            if reviewer_email:
                user_for_review = User.query.filter_by(email=reviewer_email.lower()).first()
            if not user_for_review:
                # Create visitor user entry for foreign key integrity
                user_for_review = User(
                    name=reviewer_name,
                    email=reviewer_email.lower() if reviewer_email else f"visitor_{int(datetime.now().timestamp())}@nestkerala.com",
                    phone="+91 94470 00000",
                    role="tenant"
                )
                user_for_review.set_password("Guest@123")
                db.session.add(user_for_review)
                db.session.flush()

        fb = Review(
            property_id=prop.property_id,
            user_id=user_for_review.user_id,
            rating=max(1, min(5, rating)),
            headline=headline,
            feedback=comment,
            visit_type=visit_type,
            water_rating=max(1, min(5, water_rating)),
            location_rating=max(1, min(5, location_rating)),
            landlord_rating=max(1, min(5, landlord_rating)),
            is_approved=True
        )
        db.session.add(fb)
        db.session.commit()

        flash(f"Thank you for sharing your feedback on {prop.title}! Your review has been saved.", "success")
        return redirect(url_for('property_feedback', property_id=prop.property_id))

    # GET: fetch all approved feedbacks
    feedbacks = prop.reviews.filter_by(is_approved=True).order_by(Review.review_date.desc()).all()

    water_avg = round(sum(f.water_rating for f in feedbacks) / len(feedbacks), 1) if feedbacks else 0.0
    location_avg = round(sum(f.location_rating for f in feedbacks) / len(feedbacks), 1) if feedbacks else 0.0
    landlord_avg = round(sum(f.landlord_rating for f in feedbacks) / len(feedbacks), 1) if feedbacks else 0.0

    return render_template(
        'feedback.html',
        property=prop,
        feedbacks=feedbacks,
        water_avg=water_avg,
        location_avg=location_avg,
        landlord_avg=landlord_avg
    )


@app.route('/property/<int:property_id>/enquiry', methods=['POST'])
def submit_enquiry(property_id):
    prop = Property.query.get_or_404(property_id)
    curr_user = get_current_user()

    sender_name = request.form.get('sender_name', '').strip()
    sender_phone = request.form.get('sender_phone', '').strip()
    sender_email = request.form.get('sender_email', '').strip()
    message = request.form.get('message', '').strip()
    move_in_date = request.form.get('move_in_date', 'Immediate').strip()
    tenant_type = request.form.get('tenant_type', 'Family').strip()

    if not sender_name or not sender_phone or not message:
        flash("Please provide your name, contact phone number, and enquiry message.", "danger")
        return redirect(url_for('property_detail', property_id=prop.property_id))

    enquiry = Enquiry(
        property_id=prop.property_id,
        user_id=curr_user.user_id if curr_user else None,
        sender_name=sender_name,
        sender_phone=sender_phone,
        sender_email=sender_email if sender_email else (curr_user.email if curr_user else "N/A"),
        message=message,
        move_in_date=move_in_date,
        tenant_type=tenant_type,
        status='pending'
    )
    db.session.add(enquiry)
    db.session.commit()

    flash(f"Your enquiry has been delivered directly to {prop.owner_name}. The owner will contact you shortly on {sender_phone}.", "success")
    return redirect(url_for('property_detail', property_id=prop.property_id))


@app.route('/property/<int:property_id>/schedule-visit', methods=['POST'])
def schedule_visit(property_id):
    prop = Property.query.get_or_404(property_id)
    curr_user = get_current_user()

    visitor_name = request.form.get('visitor_name', '').strip()
    visitor_phone = request.form.get('visitor_phone', '').strip()
    visitor_email = request.form.get('visitor_email', '').strip()
    preferred_date = request.form.get('preferred_date', '').strip()
    preferred_time_slot = request.form.get('preferred_time_slot', 'Morning (9:00 AM - 12:00 PM)').strip()
    notes = request.form.get('notes', '').strip()

    if not visitor_name or not visitor_phone or not preferred_date:
        flash("Please provide your name, phone number, and preferred visit date.", "danger")
        return redirect(url_for('property_detail', property_id=prop.property_id))

    visit = VisitRequest(
        property_id=prop.property_id,
        user_id=curr_user.user_id if curr_user else None,
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
        visitor_email=visitor_email if visitor_email else (curr_user.email if curr_user else "N/A"),
        preferred_date=preferred_date,
        preferred_time_slot=preferred_time_slot,
        notes=notes,
        status='pending'
    )
    db.session.add(visit)
    db.session.commit()

    flash(f"Property visit appointment requested for {preferred_date} ({preferred_time_slot}). The owner has been notified.", "success")
    return redirect(url_for('property_detail', property_id=prop.property_id))


@app.route('/property/<int:property_id>/report', methods=['POST'])
def report_property(property_id):
    prop = Property.query.get_or_404(property_id)
    curr_user = get_current_user()

    reporter_name = request.form.get('reporter_name', '').strip()
    reporter_email = request.form.get('reporter_email', '').strip()
    reason = request.form.get('reason', 'Inaccurate Details').strip()
    details = request.form.get('details', '').strip()

    if not reporter_name or not details:
        flash("Please provide your name and details of the report.", "danger")
        return redirect(url_for('property_detail', property_id=prop.property_id))

    report = PropertyReport(
        property_id=prop.property_id,
        user_id=curr_user.user_id if curr_user else None,
        reporter_name=reporter_name,
        reporter_email=reporter_email if reporter_email else "N/A",
        reason=reason,
        details=details,
        status='pending'
    )
    db.session.add(report)
    db.session.commit()

    flash("Thank you for your vigilance. Our moderation team will inspect this listing promptly.", "info")
    return redirect(url_for('property_detail', property_id=prop.property_id))


# -------------------------------------------------------------
# Favourites & Side-by-Side Comparison
# -------------------------------------------------------------

@app.route('/favorite/toggle/<int:property_id>', methods=['POST'])
def toggle_favorite(property_id):
    prop = Property.query.get_or_404(property_id)
    curr_user = get_current_user()

    if curr_user:
        fav = Favorite.query.filter_by(user_id=curr_user.user_id, property_id=prop.property_id).first()
        if fav:
            db.session.delete(fav)
            db.session.commit()
            status = 'removed'
        else:
            new_fav = Favorite(user_id=curr_user.user_id, property_id=prop.property_id)
            db.session.add(new_fav)
            db.session.commit()
            status = 'added'
    else:
        guest_favs = session.get('guest_favorites', [])
        if property_id in guest_favs:
            guest_favs.remove(property_id)
            status = 'removed'
        else:
            guest_favs.append(property_id)
            status = 'added'
        session['guest_favorites'] = guest_favs

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': status, 'property_id': property_id})
    
    flash("Favourites updated.", "success")
    return redirect(request.referrer or url_for('properties'))


@app.route('/saved-homes')
def saved_homes():
    curr_user = get_current_user()
    if curr_user:
        favs = Favorite.query.filter_by(user_id=curr_user.user_id).order_by(Favorite.id.desc()).all()
        saved_props = [f.property_rel for f in favs if f.property_rel]
    else:
        guest_ids = session.get('guest_favorites', [])
        saved_props = Property.query.filter(Property.property_id.in_(guest_ids)).all() if guest_ids else []

    recent_ids = session.get('recently_viewed', [])
    recently_viewed = Property.query.filter(Property.property_id.in_(recent_ids)).all() if recent_ids else []

    return render_template(
        'saved_homes.html',
        saved_properties=saved_props,
        recently_viewed=recently_viewed
    )


@app.route('/compare')
def compare():
    compare_ids = session.get('compare_ids', [])
    query_ids = request.args.get('ids')
    if query_ids:
        try:
            compare_ids = [int(i.strip()) for i in query_ids.split(',') if i.strip()]
        except ValueError:
            pass

    properties = Property.query.filter(Property.property_id.in_(compare_ids)).limit(3).all() if compare_ids else []
    return render_template('compare.html', properties=properties)


@app.route('/compare/toggle/<int:property_id>', methods=['POST'])
def toggle_compare(property_id):
    compare_ids = session.get('compare_ids', [])
    if property_id in compare_ids:
        compare_ids.remove(property_id)
        status = 'removed'
        msg = "Removed from comparison."
    else:
        if len(compare_ids) >= 3:
            return jsonify({'status': 'full', 'message': 'You can compare up to 3 homes at once. Please remove one first.'}), 400
        compare_ids.append(property_id)
        status = 'added'
        msg = "Added to comparison."
    
    session['compare_ids'] = compare_ids
    return jsonify({'status': status, 'message': msg, 'count': len(compare_ids), 'compare_ids': compare_ids})


@app.route('/compare/clear', methods=['POST'])
def clear_compare():
    session['compare_ids'] = []
    flash("Comparison list cleared.", "info")
    return redirect(url_for('compare'))


# -------------------------------------------------------------
# User Authentication Routes (Section 4)
# -------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not full_name or not email or not password or not phone:
            flash("Please fill in all mandatory fields.", "danger")
            return render_template('auth/register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please enter matching passwords.", "danger")
            return render_template('auth/register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/register.html')

        # Check duplicate email
        if User.query.filter_by(email=email).first():
            flash("An account with that email address already exists. Please log in.", "warning")
            return redirect(url_for('login'))

        user = User(
            name=full_name,
            email=email,
            phone=phone,
            role='tenant'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Log user in securely
        session['user_id'] = user.user_id
        session['user_role'] = user.role
        session['user_name'] = user.name
        flash(f"Welcome to Nest Kerala, {user.name}! Your account has been created successfully.", "success")
        return redirect(url_for('index'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.args.get('next')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.user_id
            session['user_role'] = user.role
            session['user_name'] = user.name
            flash(f"Welcome back, {user.name}!", "success")

            if next_url:
                return redirect(next_url)
            if user.is_admin():
                session['admin_id'] = 1
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))

        flash("Invalid email or password. Please try again.", "danger")

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    session.pop('user_name', None)
    flash("You have successfully signed out.", "info")
    return redirect(url_for('index'))


# -------------------------------------------------------------
# Admin Authentication & Dashboard (Section 4 & 15)
# -------------------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.args.get('next')

        # Check ADMINS table
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.admin_id
            session['admin_email'] = admin.email
            session['admin_name'] = admin.name
            flash(f"Welcome to Nest Kerala Control Center, {admin.name}!", "success")
            return redirect(next_url or url_for('admin_dashboard'))

        # Fallback to User with admin role
        admin_user = User.query.filter_by(email=email, role='admin').first()
        if admin_user and admin_user.check_password(password):
            session['admin_id'] = admin_user.user_id
            session['user_id'] = admin_user.user_id
            session['user_name'] = admin_user.name
            session['user_role'] = 'admin'
            flash(f"Welcome Administrator, {admin_user.name}!", "success")
            return redirect(next_url or url_for('admin_dashboard'))

        flash("Invalid administrator credentials. Access denied.", "danger")

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    session.pop('admin_name', None)
    flash("Administrator signed out successfully.", "info")
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    # Overview statistics calculated directly from SQLite records
    total_users = User.query.count()
    total_properties = Property.query.count()
    available_properties = Property.query.filter_by(availability='Available').count()
    unavailable_properties = Property.query.filter(Property.availability != 'Available').count()
    total_districts = District.query.count()
    total_reviews = Review.query.count()

    # Search & District Filtering for listings management table
    district_filter = request.args.get('district_filter', '').strip()
    query_q = request.args.get('q', '').strip()

    prop_query = Property.query
    if district_filter:
        dist_obj = District.query.filter_by(district_name=district_filter).first()
        if dist_obj:
            prop_query = prop_query.filter(Property.district_id == dist_obj.district_id)

    if query_q:
        q_term = f"%{query_q}%"
        prop_query = prop_query.filter(
            db.or_(
                Property.title.ilike(q_term),
                Property.town.ilike(q_term),
                Property.property_code.ilike(q_term)
            )
        )

    all_properties = prop_query.order_by(Property.property_id.desc()).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_properties=total_properties,
        available_properties=available_properties,
        unavailable_properties=unavailable_properties,
        total_districts=total_districts,
        total_reviews=total_reviews,
        properties=all_properties,
        selected_district=district_filter,
        query_q=query_q
    )


# Admin Feature A: Add New Rental House
@app.route('/admin/property/add', methods=['GET', 'POST'])
@admin_required
def admin_add_property():
    districts = District.query.order_by(District.district_name.asc()).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        district_id = request.form.get('district_id', type=int)
        town = request.form.get('town', '').strip()
        address = request.form.get('address', '').strip()
        pincode = request.form.get('pincode', '').strip()
        rent = request.form.get('rent', type=int)
        deposit = request.form.get('deposit', type=int)
        bhk = request.form.get('bhk', type=int)
        bathrooms = request.form.get('bathrooms', default=2, type=int)
        area = request.form.get('area', type=int)
        furnishing = request.form.get('furnishing', 'Semi-Furnished').strip()
        property_type = request.form.get('property_type', 'Independent Villa').strip()
        parking = request.form.get('parking', 'Covered Car Parking').strip()
        water_supply = request.form.get('water_supply', 'KWA + Open Well').strip()
        facilities = request.form.get('facilities', '').strip()
        availability = request.form.get('availability', 'Available').strip()
        
        owner_name = request.form.get('owner_name', '').strip()
        owner_phone = request.form.get('owner_phone', '').strip()
        owner_email = request.form.get('owner_email', '').strip()
        
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        landmarks = request.form.get('landmarks', '').strip()

        # Validation
        if not title or not district_id or not rent or not deposit or not bhk or not area or not owner_name or not owner_phone:
            flash("Please fill in all required property, pricing, and owner details.", "danger")
            return render_template('admin/property_form.html', is_edit=False, districts=districts)

        # Find or create Owner
        owner = Owner.query.filter_by(phone=owner_phone).first()
        if not owner:
            owner = Owner(
                name=owner_name,
                phone=owner_phone,
                email=owner_email if owner_email else None,
                contact_type="Individual Owner"
            )
            db.session.add(owner)
            db.session.flush()

        # Generate property code
        dist_obj = db.session.get(District, district_id)
        dist_code = dist_obj.district_name[:3].upper() if dist_obj else "KRL"
        now_ts = int(datetime.now().timestamp()) % 10000
        prop_code = f"NK-{dist_code}-{now_ts}"

        slug = f"{title.lower().replace(' ', '-')[:50]}"

        new_prop = Property(
            title=title,
            description=description,
            rent=rent,
            deposit=deposit,
            bhk=bhk,
            bathrooms=bathrooms,
            area=area,
            town=town,
            address=address,
            pincode=pincode,
            furnishing=furnishing,
            property_type=property_type,
            parking=parking,
            water_supply=water_supply,
            facilities=facilities,
            availability=availability,
            latitude=latitude,
            longitude=longitude,
            landmarks=landmarks,
            district_id=district_id,
            owner_id=owner.owner_id,
            property_code=prop_code,
            slug=slug,
            is_verified=True,
            is_sample_demo=False
        )
        db.session.add(new_prop)
        db.session.flush()

        # Save uploaded photographs
        uploaded_files = request.files.getlist('property_photos')
        saved_photos = 0
        for idx, file in enumerate(uploaded_files):
            file_url = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
            if file_url:
                caption = "Exterior View" if idx == 0 else f"Interior View {idx}"
                photo = PropertyPhoto(
                    property_id=new_prop.property_id,
                    photo_path=file_url,
                    photo_type=caption,
                    is_primary=(idx == 0)
                )
                db.session.add(photo)
                saved_photos += 1

        # Fallback photo if none uploaded
        if saved_photos == 0:
            fallback = PropertyPhoto(
                property_id=new_prop.property_id,
                photo_path="/static/images/hero-kerala.jpg",
                photo_type="Exterior View",
                is_primary=True
            )
            db.session.add(fallback)

        db.session.commit()
        flash(f"New rental property '{title}' created successfully in {dist_obj.district_name if dist_obj else ''}!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/property_form.html', is_edit=False, districts=districts)


# Admin Feature B: Edit Property Details
@app.route('/admin/property/<int:property_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_property(property_id):
    prop = Property.query.get_or_404(property_id)
    districts = District.query.order_by(District.district_name.asc()).all()

    if request.method == 'POST':
        prop.title = request.form.get('title', prop.title).strip()
        prop.description = request.form.get('description', prop.description).strip()
        prop.district_id = request.form.get('district_id', prop.district_id, type=int)
        prop.town = request.form.get('town', prop.town).strip()
        prop.address = request.form.get('address', prop.address).strip()
        prop.pincode = request.form.get('pincode', prop.pincode).strip()
        prop.rent = request.form.get('rent', prop.rent, type=int)
        prop.deposit = request.form.get('deposit', prop.deposit, type=int)
        prop.bhk = request.form.get('bhk', prop.bhk, type=int)
        prop.bathrooms = request.form.get('bathrooms', prop.bathrooms, type=int)
        prop.area = request.form.get('area', prop.area, type=int)
        prop.furnishing = request.form.get('furnishing', prop.furnishing).strip()
        prop.property_type = request.form.get('property_type', prop.property_type).strip()
        prop.parking = request.form.get('parking', prop.parking).strip()
        prop.water_supply = request.form.get('water_supply', prop.water_supply).strip()
        prop.facilities = request.form.get('facilities', prop.facilities).strip()
        prop.availability = request.form.get('availability', prop.availability).strip()
        prop.landmarks = request.form.get('landmarks', prop.landmarks).strip()

        lat = request.form.get('latitude', type=float)
        lng = request.form.get('longitude', type=float)
        if lat is not None:
            prop.latitude = lat
        if lng is not None:
            prop.longitude = lng

        # Update Owner details
        if prop.owner_rel:
            prop.owner_rel.name = request.form.get('owner_name', prop.owner_rel.name).strip()
            prop.owner_rel.phone = request.form.get('owner_phone', prop.owner_rel.phone).strip()
            prop.owner_rel.email = request.form.get('owner_email', prop.owner_rel.email).strip()

        # Handle any new photos uploaded in edit form
        uploaded_files = request.files.getlist('property_photos')
        for file in uploaded_files:
            file_url = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
            if file_url:
                photo = PropertyPhoto(
                    property_id=prop.property_id,
                    photo_path=file_url,
                    photo_type="Additional View",
                    is_primary=False
                )
                db.session.add(photo)

        db.session.commit()
        flash(f"Property '{prop.title}' details updated successfully.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/property_form.html', is_edit=True, property=prop, districts=districts)


# Admin Feature C: Manage Property Photos
@app.route('/admin/property/<int:property_id>/photos')
@admin_required
def admin_manage_photos(property_id):
    prop = Property.query.get_or_404(property_id)
    photos = prop.photos.order_by(PropertyPhoto.is_primary.desc(), PropertyPhoto.photo_id.asc()).all()
    return render_template('admin/manage_photos.html', property=prop, photos=photos)


@app.route('/admin/property/<int:property_id>/photos/upload', methods=['POST'])
@admin_required
def admin_upload_photo(property_id):
    prop = Property.query.get_or_404(property_id)
    file = request.files.get('photo_file')
    photo_type = request.form.get('photo_type', 'Exterior').strip()

    if file:
        file_url = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
        if file_url:
            # If no photos exist, make this primary
            is_prim = (prop.photos.count() == 0)
            photo = PropertyPhoto(
                property_id=prop.property_id,
                photo_path=file_url,
                photo_type=photo_type,
                is_primary=is_prim
            )
            db.session.add(photo)
            db.session.commit()
            flash("New photograph uploaded successfully.", "success")
        else:
            flash("Invalid image file format.", "danger")
    else:
        flash("Please select an image file to upload.", "warning")

    return redirect(url_for('admin_manage_photos', property_id=prop.property_id))


@app.route('/admin/photos/<int:photo_id>/set-primary', methods=['POST'])
@admin_required
def admin_set_primary_photo(photo_id):
    photo = PropertyPhoto.query.get_or_404(photo_id)
    # Remove primary flag from other photos of this property
    PropertyPhoto.query.filter_by(property_id=photo.property_id).update({'is_primary': False})
    photo.is_primary = True
    db.session.commit()
    flash("Primary cover photo updated successfully.", "success")
    return redirect(url_for('admin_manage_photos', property_id=photo.property_id))


@app.route('/admin/photos/<int:photo_id>/delete', methods=['POST'])
@admin_required
def admin_delete_photo(photo_id):
    photo = PropertyPhoto.query.get_or_404(photo_id)
    prop_id = photo.property_id
    db.session.delete(photo)
    db.session.commit()
    flash("Photograph removed successfully.", "info")
    return redirect(url_for('admin_manage_photos', property_id=prop_id))


# Admin Feature E: Manage Feedback
@app.route('/admin/reviews')
@admin_required
def admin_manage_reviews():
    reviews = Review.query.order_by(Review.review_date.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews)


@app.route('/admin/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review has been permanently removed.", "info")
    return redirect(url_for('admin_manage_reviews'))


# Admin Feature F: Delete Property
@app.route('/admin/property/<int:property_id>/delete', methods=['POST'])
@admin_required
def admin_delete_property(property_id):
    prop = Property.query.get_or_404(property_id)
    title = prop.title
    db.session.delete(prop)
    db.session.commit()
    flash(f"Property '{title}' and its associated photographs and reviews have been permanently deleted.", "info")
    return redirect(url_for('admin_dashboard'))


# Backward compatibility route for standard delete
@app.route('/property/<int:property_id>/delete', methods=['POST'])
@login_required
def delete_property(property_id):
    curr_user = get_current_user()
    curr_admin = get_current_admin()
    prop = Property.query.get_or_404(property_id)

    if not curr_admin and (not curr_user or prop.owner_rel.phone != curr_user.phone):
        flash("You are not authorized to delete this property.", "danger")
        return redirect(url_for('index'))

    title = prop.title
    db.session.delete(prop)
    db.session.commit()
    flash(f"Property '{title}' deleted.", "info")
    return redirect(request.referrer or url_for('admin_dashboard'))


# -------------------------------------------------------------
# Additional Routes: List Property, Owner Dashboard, Profile
# -------------------------------------------------------------

@app.route('/list-property', methods=['GET', 'POST'])
def list_property():
    districts = District.query.order_by(District.district_name.asc()).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        district_name = request.form.get('district', '').strip()
        town = request.form.get('city_town', '').strip()
        address = request.form.get('full_address', '').strip()
        pincode = request.form.get('pin_code', '').strip()
        rent = request.form.get('monthly_rent', type=int)
        deposit = request.form.get('security_deposit', type=int)
        bhk = request.form.get('bhk', type=int)
        bathrooms = request.form.get('bathrooms', default=2, type=int)
        area = request.form.get('sqft_area', type=int)
        property_type = request.form.get('property_type', 'Independent Villa').strip()
        furnishing = request.form.get('furnishing', 'Semi-Furnished').strip()
        parking = request.form.get('parking', 'Covered Car Parking').strip()
        water_supply = request.form.get('water_supply', 'KWA + Open Well').strip()
        facilities = request.form.get('facilities', 'Covered Parking, 24x7 Water, Balcony').strip()
        description = request.form.get('description', '').strip()
        landmarks = request.form.get('nearby_landmarks', '').strip()
        owner_name = request.form.get('owner_name', '').strip()
        owner_phone = request.form.get('contact_phone', '').strip()
        owner_email = request.form.get('contact_email', '').strip()

        if not title or not district_name or not rent or not deposit or not bhk or not area or not owner_name or not owner_phone:
            flash("Please fill in all mandatory fields.", "danger")
            return render_template('list_property.html')

        dist_obj = District.query.filter_by(district_name=district_name).first()
        if not dist_obj:
            dist_obj = District.query.first()

        owner = Owner.query.filter_by(phone=owner_phone).first()
        if not owner:
            owner = Owner(name=owner_name, phone=owner_phone, email=owner_email if owner_email else None)
            db.session.add(owner)
            db.session.flush()

        dist_code = dist_obj.district_name[:3].upper()
        now_ts = int(datetime.now().timestamp()) % 10000
        prop_code = f"NK-{dist_code}-{now_ts}"

        new_prop = Property(
            title=title,
            description=description,
            rent=rent,
            deposit=deposit,
            bhk=bhk,
            bathrooms=bathrooms,
            area=area,
            town=town or dist_obj.district_name,
            address=address,
            pincode=pincode or "682001",
            furnishing=furnishing,
            property_type=property_type,
            parking=parking,
            water_supply=water_supply,
            facilities=facilities,
            landmarks=landmarks,
            district_id=dist_obj.district_id,
            owner_id=owner.owner_id,
            property_code=prop_code,
            slug=title.lower().replace(' ', '-')[:50],
            availability='Available'
        )
        db.session.add(new_prop)
        db.session.flush()

        uploaded_files = request.files.getlist('property_photos')
        saved_photos = 0
        for idx, file in enumerate(uploaded_files):
            file_url = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
            if file_url:
                photo = PropertyPhoto(
                    property_id=new_prop.property_id,
                    photo_path=file_url,
                    photo_type="Exterior View" if idx == 0 else f"Interior View {idx}",
                    is_primary=(idx == 0)
                )
                db.session.add(photo)
                saved_photos += 1

        if saved_photos == 0:
            fallback = PropertyPhoto(
                property_id=new_prop.property_id,
                photo_path="/static/images/hero-kerala.jpg",
                photo_type="Exterior View",
                is_primary=True
            )
            db.session.add(fallback)

        db.session.commit()
        flash(f"Property '{title}' has been successfully listed on Nest Kerala!", "success")
        return redirect(url_for('property_detail', property_id=new_prop.property_id))

    return render_template('list_property.html')


@app.route('/dashboard/owner')
@login_required
def owner_dashboard():
    curr_user = get_current_user()
    curr_admin = get_current_admin()

    if curr_admin or (curr_user and curr_user.is_admin()):
        properties = Property.query.order_by(Property.property_id.desc()).all()
    else:
        owner = Owner.query.filter_by(phone=curr_user.phone).first() if curr_user else None
        if owner:
            properties = Property.query.filter_by(owner_id=owner.owner_id).all()
        else:
            properties = []

    prop_ids = [p.property_id for p in properties]
    enquiries = Enquiry.query.filter(Enquiry.property_id.in_(prop_ids)).order_by(Enquiry.id.desc()).all() if prop_ids else []
    visit_requests = VisitRequest.query.filter(VisitRequest.property_id.in_(prop_ids)).order_by(VisitRequest.id.desc()).all() if prop_ids else []

    return render_template(
        'dashboard/owner.html',
        user=curr_user or curr_admin,
        properties=properties,
        enquiries=enquiries,
        visit_requests=visit_requests,
        total_properties=len(properties),
        available_count=sum(1 for p in properties if p.availability == 'Available'),
        rented_count=sum(1 for p in properties if p.availability != 'Available'),
        pending_visits=sum(1 for v in visit_requests if v.status == 'pending')
    )


@app.route('/profile')
@login_required
def profile():
    curr_user = get_current_user()
    if not curr_user:
        return redirect(url_for('login'))

    sent_enquiries = Enquiry.query.filter_by(user_id=curr_user.user_id).order_by(Enquiry.id.desc()).all()
    sent_visits = VisitRequest.query.filter_by(user_id=curr_user.user_id).order_by(VisitRequest.id.desc()).all()

    return render_template(
        'auth/profile.html',
        user=curr_user,
        sent_enquiries=sent_enquiries,
        sent_visits=sent_visits
    )


@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['en', 'ml']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        'error.html',
        error_code='404',
        error_title='Property or Page Not Found',
        error_message='The property listing or URL you are trying to visit is not available or has been unlisted.'
    ), 404


@app.errorhandler(500)
def server_error(e):
    return render_template(
        'error.html',
        error_code='500',
        error_title='Internal Server Notice',
        error_message='An unexpected error occurred while processing your request. Please try again shortly.'
    ), 500


# -------------------------------------------------------------
# Database Setup & Seeding on Application Startup
# -------------------------------------------------------------

with app.app_context():
    db.create_all()
    seed_database(app)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
