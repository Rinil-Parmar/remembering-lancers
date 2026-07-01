from .extensions import db


class Obituary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tags = db.Column(db.String(50), default="new", server_default="new")
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
    funeral_home = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Obituary {self.name} - {self.city}, {self.province}>"


class DistinctObituary(db.Model):
    __tablename__ = "dist_obituary"

    id = db.Column(db.Integer, primary_key=True)
    tags = db.Column(db.String(50), default="new", server_default="new")
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
    funeral_home = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<DistinctObituary {self.name} - {self.city}, {self.province}>"


class ScrapeState(db.Model):
    __tablename__ = "scrape_state"

    id = db.Column(db.Integer, primary_key=True)
    subdomain = db.Column(db.String(255), nullable=False)
    search_keyword = db.Column(db.String(255), nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    last_processed_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default="running")
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "subdomain",
            "search_keyword",
            name="uq_scrape_state_subdomain_keyword",
        ),
    )

    def __repr__(self):
        return (
            f"<ScrapeState {self.subdomain} "
            f"{self.search_keyword} page={self.page_number}>"
        )


class ScrapeRun(db.Model):
    __tablename__ = "scrape_runs"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False, default="running")
    started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    search_keyword = db.Column(db.String(255), nullable=True)
    page_number = db.Column(db.Integer, nullable=True)
    saved_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    skipped_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    duplicate_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ScrapeRun {self.id} status={self.status}>"
