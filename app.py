from remembering_lancers import create_app
from remembering_lancers.extensions import db


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.extensions["scraper_service"].start_scheduler()
    app.run(debug=True)
