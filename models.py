# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Obituary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tags = db.Column(db.String(50), default='updated')# New field: Tags (comma-separated string for now)
    name = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    birth_date = db.Column(db.String(50), nullable=True)
    death_date = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    province = db.Column(db.String(255), nullable=True)
    publication_date = db.Column(db.DateTime(timezone=True)) 
    obituary_url = db.Column(db.String(255), unique=True, nullable=False)
    family_information = db.Column(db.Text, nullable=True)
    donation_information = db.Column(db.Text, nullable=True)
    is_alumni = db.Column(db.Boolean, default=False)
    funeral_home = db.Column(db.String(255), nullable=True) # New field: Funeral Home
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Obituary {self.name} - {self.city}, {self.province}>"

class DistinctObituary(db.Model): # New model for dist_obituary
    __tablename__ = 'dist_obituary' # Specify the table name if it's different from class name

    id = db.Column(db.Integer, primary_key=True)
    tags = db.Column(db.String(50), default='updated') # New field: Tags (comma-separated string for now)
    name = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    birth_date = db.Column(db.String(50), nullable=True)
    death_date = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    province = db.Column(db.String(255), nullable=True)
    publication_date = db.Column(db.DateTime(timezone=True)) 
    obituary_url = db.Column(db.String(255), unique=True, nullable=False)
    family_information = db.Column(db.Text, nullable=True)
    donation_information = db.Column(db.Text, nullable=True)
    is_alumni = db.Column(db.Boolean, default=False)
    funeral_home = db.Column(db.String(255), nullable=True) # New field: Funeral Home
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<DistinctObituary {self.name} - {self.city}, {self.province}>"