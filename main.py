import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired
import requests

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
Bootstrap5(app)


# CREATE DB

class Base(DeclarativeBase):
	pass


db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('SQLALCHEMY_DATABASE_URI')
db.init_app(app)


# CREATE TABLE

class Movie(db.Model):
	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	title: Mapped[str] = mapped_column(String, unique=True, nullable=False)
	year: Mapped[int] = mapped_column(Integer, nullable=False)
	description: Mapped[str] = mapped_column(String(500), nullable=False)
	rating: Mapped[float] = mapped_column(Float, nullable=True)
	ranking: Mapped[int] = mapped_column(Integer, nullable=True)
	review: Mapped[str] = mapped_column(String(500), nullable=True)
	img_url: Mapped[str] = mapped_column(String(500), nullable=False)

	def __repr__(self):
		return f'<Movie {self.title}>'


with app.app_context():
	db.create_all()


class UpdateForm(FlaskForm):
	new_rating = StringField('New rating: ', validators=[DataRequired()])
	new_review = StringField('New review: ', validators=[DataRequired()])
	submit = SubmitField('Update')


class AddForm(FlaskForm):
	name = StringField('Add a movie you watched', validators=[DataRequired()])
	submit = SubmitField('Add')


def search_movie(title):
	TMDB_API = os.getenv('TMDB_API_KEY')
	TMDB_URL = f'https://api.themoviedb.org/3/search/movie?query={title}&api_key={TMDB_API}'
	response = requests.get(url=TMDB_URL)
	response.raise_for_status()
	movies = response.json()['results']

	return movies


def get_movie_by_id(movie_id):
	url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"

	headers = {
		"accept": "application/json",
		"Authorization": os.getenv('TMDB_AUTH_TOKEN')
	}

	response = requests.get(url, headers=headers).json()
	return response


@app.route("/")
def home():
	movie_list = db.session.execute(db.select(Movie).order_by(Movie.rating)).scalars().all()

	for index, movie in enumerate(movie_list):
		movie.ranking = 10 - index

	db.session.commit()

	return render_template("index.html", movies=movie_list)


@app.route("/update/<int:movie_id>", methods=["GET", "POST"])
def update_movie(movie_id):
	movie_to_update = Movie.query.get_or_404(movie_id)
	form = UpdateForm(movie_id=movie_id)
	if form.validate_on_submit():
		movie_to_update.rating = form.new_rating.data
		movie_to_update.review = form.new_review.data
		db.session.commit()
		return redirect(url_for('home'))

	form.new_rating.data = movie_to_update.rating
	form.new_review.data = movie_to_update.review
	return render_template('edit.html', form=form, movie=movie_to_update)


@app.route("/delete/<int:movie_id>")
def delete_movie(movie_id):
	movie_to_delete = Movie.query.get_or_404(movie_id)
	db.session.delete(movie_to_delete)
	db.session.commit()
	return redirect(url_for('home'))


@app.route("/add", methods=["GET", "POST"])
def add_movie():
	form = AddForm()
	movie_to_search = form.name.data
	if form.validate_on_submit():
		movie_info = search_movie(movie_to_search)
		return render_template("select.html", movies=movie_info)
	return render_template("add.html", form=form)


@app.route("/find")
def find_movie():
	movie_tmdb_id = request.args.get("id")
	if movie_tmdb_id:
		movie = get_movie_by_id(movie_tmdb_id)
		title = movie["title"]
		img_path = movie['poster_path']
		base_url = "https://image.tmdb.org/t/p/w500"
		img_url = f"{base_url}{img_path}"
		description = movie['overview']
		year = int(movie['release_date'][:4])

		with app.app_context():
			new_movie = Movie(title=title, year=year, description=description, img_url=img_url)
			db.session.add(new_movie)
			db.session.commit()

		db_movie = db.session.execute(db.select(Movie).where(Movie.title == title)).scalar()
		db_id = db_movie.id

		return redirect(url_for("update_movie", movie_id=db_id))


if __name__ == '__main__':
	app.run(debug=True)
