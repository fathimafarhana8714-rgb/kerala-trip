from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

# =====================================================================
# Table 1: USERS
# Fields: user_id (PK), name, email (Unique), password_hash, phone, created_at
# =====================================================================
class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    role = db.Column(db.String(20), default='tenant') # tenant / owner / agent / admin
    agency_name = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Alias id to user_id for Flask / SQLAlchemy compatibility
    @property
    def id(self):
        return self.user_id

    @property
    def full_name(self):
        return self.name

    @full_name.setter
    def full_name(self, value):
        self.name = value

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_owner_or_agent(self):
        return self.role in ['owner', 'agent', 'admin']

    # Relationships
    reviews = db.relationship('Review', backref='user_rel', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user_rel', lazy='dynamic', cascade='all, delete-orphan')
    enquiries_sent = db.relationship('Enquiry', backref='sender_rel', lazy='dynamic')
    visit_requests_sent = db.relationship('VisitRequest', backref='visitor_rel', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email} ({self.name})>'


# =====================================================================
# Table 2: ADMINS
# Fields: admin_id (PK), email (Unique), password_hash, created_at
# =====================================================================
class Admin(db.Model):
    __tablename__ = 'admins'

    admin_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(120), default='Administrator')
    created_at = db.Column(db.DateTime, default=utc_now)

    @property
    def id(self):
        return self.admin_id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.email}>'


# =====================================================================
# Table 3: OWNERS
# Fields: owner_id (PK), name, phone, email (Unique where applicable), created_at
# =====================================================================
class Owner(db.Model):
    __tablename__ = 'owners'

    owner_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    contact_type = db.Column(db.String(50), default='Individual Owner') # Individual Owner / Authorized Agent
    created_at = db.Column(db.DateTime, default=utc_now)

    @property
    def id(self):
        return self.owner_id

    # Relationships
    properties = db.relationship('Property', backref='owner_rel', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Owner {self.name} ({self.phone})>'


# =====================================================================
# Table 4: DISTRICTS
# Fields: district_id (PK), district_name, image_path, description
# =====================================================================
class District(db.Model):
    __tablename__ = 'districts'

    district_id = db.Column(db.Integer, primary_key=True)
    district_name = db.Column(db.String(60), unique=True, nullable=False, index=True)
    image_path = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    malayalam_name = db.Column(db.String(100), nullable=True)

    @property
    def id(self):
        return self.district_id

    @property
    def name(self):
        return self.district_name

    # Relationships
    properties = db.relationship('Property', backref='district_rel', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<District {self.district_name}>'


# =====================================================================
# Table 5: PROPERTIES
# Fields: property_id (PK), owner_id (FK), district_id (FK), title,
# description, rent, deposit, bhk, area, address, landmarks, availability,
# created_at, town, pincode, bathrooms, furnishing, property_type,
# parking, water_supply, facilities, latitude, longitude
# =====================================================================
class Property(db.Model):
    __tablename__ = 'properties'

    property_id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.owner_id', ondelete='CASCADE'), nullable=False)
    district_id = db.Column(db.Integer, db.ForeignKey('districts.district_id', ondelete='CASCADE'), nullable=False)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    rent = db.Column(db.Integer, nullable=False, index=True) # Monthly Rent
    deposit = db.Column(db.Integer, nullable=False) # Security Deposit
    bhk = db.Column(db.Integer, nullable=False) # 1, 2, 3, 4, 5
    area = db.Column(db.Integer, nullable=False) # Sq Ft
    address = db.Column(db.Text, nullable=False)
    landmarks = db.Column(db.Text, nullable=True)
    availability = db.Column(db.String(30), default='Available', index=True) # Available / Rented / Under Offer
    created_at = db.Column(db.DateTime, default=utc_now)

    # Necessary property attributes
    town = db.Column(db.String(100), nullable=False, index=True)
    pincode = db.Column(db.String(15), nullable=False)
    bathrooms = db.Column(db.Integer, default=2)
    balconies = db.Column(db.Integer, default=1)
    furnishing = db.Column(db.String(50), default='Semi-Furnished') # Fully Furnished, Semi-Furnished, Unfurnished
    property_type = db.Column(db.String(60), default='Independent Villa') # Independent Villa, Nalukettu, Apartment, etc.
    parking = db.Column(db.String(60), default='Covered Car Parking')
    water_supply = db.Column(db.String(120), default='KWA + Open Well')
    electricity = db.Column(db.String(120), default='3-Phase KSEB with Inverter')
    facilities = db.Column(db.Text, default='Covered Parking, 24x7 Water, Modular Kitchen, Balcony, Gated Access')
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Identifiers & Badges
    property_code = db.Column(db.String(30), unique=True, nullable=True, index=True)
    slug = db.Column(db.String(255), nullable=True)
    maintenance_charges = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_sample_demo = db.Column(db.Boolean, default=True)
    approval_status = db.Column(db.String(30), default='approved', index=True)

    # Relationships
    photos = db.relationship('PropertyPhoto', backref='property_rel', lazy='dynamic', cascade='all, delete-orphan', order_by='PropertyPhoto.is_primary.desc(), PropertyPhoto.photo_id.asc()')
    reviews = db.relationship('Review', backref='property_rel', lazy='dynamic', cascade='all, delete-orphan', order_by='Review.review_date.desc()')
    enquiries = db.relationship('Enquiry', backref='property_rel', lazy='dynamic', cascade='all, delete-orphan')
    visit_requests = db.relationship('VisitRequest', backref='property_rel', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='property_rel', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('PropertyReport', backref='property_rel', lazy='dynamic', cascade='all, delete-orphan')

    # Compatibility Aliases for existing views
    @property
    def id(self):
        return self.property_id

    @property
    def district(self):
        return self.district_rel.district_name if self.district_rel else ""

    @property
    def city_town(self):
        return self.town

    @property
    def locality(self):
        return self.town

    @property
    def full_address(self):
        return self.address

    @property
    def pin_code(self):
        return self.pincode

    @property
    def monthly_rent(self):
        return self.rent

    @property
    def security_deposit(self):
        return self.deposit

    @property
    def sqft_area(self):
        return self.area

    @property
    def status(self):
        return self.availability

    @property
    def availability_date(self):
        return 'Immediate' if self.availability == 'Available' else self.availability

    @property
    def owner_name(self):
        return self.owner_rel.name if self.owner_rel else "NestKerala Verified Host"

    @property
    def owner_contact_type(self):
        return self.owner_rel.contact_type if self.owner_rel else "Individual Owner"

    @property
    def contact_phone(self):
        return self.owner_rel.phone if self.owner_rel else ""

    @property
    def whatsapp_number(self):
        return self.owner_rel.phone if self.owner_rel else ""

    @property
    def contact_email(self):
        return self.owner_rel.email if self.owner_rel else ""

    @property
    def primary_image_url(self):
        primary = self.photos.filter_by(is_primary=True).first()
        if primary:
            return primary.photo_path
        first = self.photos.first()
        if first:
            return first.photo_path
        return '/static/images/hero-kerala.jpg'

    @property
    def images(self):
        return self.photos.all()

    @property
    def formatted_rent(self):
        return f"₹{self.rent:,}"

    @property
    def formatted_deposit(self):
        return f"₹{self.deposit:,}"

    @property
    def formatted_maintenance(self):
        if self.maintenance_charges > 0:
            return f"₹{self.maintenance_charges:,}/mo"
        return "Included in Rent"

    @property
    def average_rating(self):
        approved = self.reviews.filter_by(is_approved=True).all()
        if not approved:
            return 0.0
        return round(sum(r.rating for r in approved) / len(approved), 1)

    @property
    def feedback_count(self):
        return self.reviews.filter_by(is_approved=True).count()

    @property
    def feedbacks(self):
        return self.reviews

    def get_landmarks_parsed(self):
        """Returns list of dicts with name, distance, and category icon."""
        if not self.landmarks:
            return []
        items = []
        for line in self.landmarks.split('|'):
            line = line.strip()
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 2:
                name = parts[0].strip()
                dist = ':'.join(parts[1:]).strip()
            else:
                name = line
                dist = "Nearby"
            
            name_lower = name.lower()
            if any(k in name_lower for k in ['school', 'college', 'vidyalaya', 'campus', 'university']):
                icon = 'school'
            elif any(k in name_lower for k in ['hospital', 'clinic', 'medical', 'health']):
                icon = 'hospital'
            elif any(k in name_lower for k in ['metro', 'railway', 'station', 'bus', 'airport']):
                icon = 'transit'
            elif any(k in name_lower for k in ['supermarket', 'mall', 'market', 'hypermarket']):
                icon = 'shopping'
            elif any(k in name_lower for k in ['park', 'infopark', 'technopark', 'cyberpark']):
                icon = 'tech'
            else:
                icon = 'pin'
            
            items.append({
                'name': name,
                'distance': dist,
                'icon': icon
            })
        return items

    def get_facilities_list(self):
        if not self.facilities:
            return []
        return [f.strip() for f in self.facilities.split(',') if f.strip()]

    def __repr__(self):
        return f'<Property {self.property_id}: {self.title}>'


# =====================================================================
# Table 6: PROPERTY_PHOTOS
# Fields: photo_id (PK), property_id (FK), photo_path, photo_type, is_primary
# =====================================================================
class PropertyPhoto(db.Model):
    __tablename__ = 'property_photos'

    photo_id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    photo_path = db.Column(db.String(255), nullable=False)
    photo_type = db.Column(db.String(50), default='Exterior') # Exterior, Living Room, Bedroom, Kitchen, Bathroom, Balcony/Courtyard
    is_primary = db.Column(db.Boolean, default=False)

    @property
    def id(self):
        return self.photo_id

    @property
    def image_url(self):
        return self.photo_path

    @property
    def caption(self):
        return self.photo_type

    def __repr__(self):
        return f'<PropertyPhoto {self.photo_id} ({self.photo_type})>'


# Alias PropertyImage to PropertyPhoto for existing references
PropertyImage = PropertyPhoto


# =====================================================================
# Table 7: REVIEWS
# Fields: review_id (PK), user_id (FK), property_id (FK), rating, feedback, review_date
# =====================================================================
class Review(db.Model):
    __tablename__ = 'reviews'

    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5) # 1 to 5 stars
    feedback = db.Column(db.Text, nullable=False)
    review_date = db.Column(db.DateTime, default=utc_now)

    # Context fields
    visit_type = db.Column(db.String(60), default='Visited Property') # Visited in Person, Previous Tenant, Seeker
    headline = db.Column(db.String(200), nullable=True)
    water_rating = db.Column(db.Integer, default=5)
    location_rating = db.Column(db.Integer, default=5)
    landlord_rating = db.Column(db.Integer, default=5)
    is_approved = db.Column(db.Boolean, default=True)

    @property
    def id(self):
        return self.review_id

    @property
    def reviewer_name(self):
        return self.user_rel.name if self.user_rel else "Verified Visitor"

    @property
    def reviewer_email(self):
        return self.user_rel.email if self.user_rel else ""

    @property
    def comment(self):
        return self.feedback

    @property
    def created_at(self):
        return self.review_date

    def __repr__(self):
        return f'<Review {self.review_id} for Prop {self.property_id} ({self.rating} stars)>'


# Alias PropertyFeedback to Review for backward compatibility
PropertyFeedback = Review


# =====================================================================
# Additional Auxiliary Tables for interactive features
# =====================================================================
class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (db.UniqueConstraint('user_id', 'property_id', name='uq_user_property_favorite'),)


class Enquiry(db.Model):
    __tablename__ = 'enquiries'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    
    sender_name = db.Column(db.String(120), nullable=False)
    sender_email = db.Column(db.String(120), nullable=False)
    sender_phone = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    move_in_date = db.Column(db.String(50), nullable=True)
    tenant_type = db.Column(db.String(50), default='Family')
    status = db.Column(db.String(30), default='pending')
    created_at = db.Column(db.DateTime, default=utc_now)


class VisitRequest(db.Model):
    __tablename__ = 'visit_requests'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    
    visitor_name = db.Column(db.String(120), nullable=False)
    visitor_phone = db.Column(db.String(30), nullable=False)
    visitor_email = db.Column(db.String(120), nullable=False)
    preferred_date = db.Column(db.String(50), nullable=False)
    preferred_time_slot = db.Column(db.String(60), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='pending')
    owner_reply = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)


class PropertyReport(db.Model):
    __tablename__ = 'property_reports'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    
    reporter_name = db.Column(db.String(120), nullable=False)
    reporter_email = db.Column(db.String(120), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='pending')
    created_at = db.Column(db.DateTime, default=utc_now)
