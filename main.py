from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Float, desc
from sqlalchemy.orm import relationship
from flask_wtf import FlaskForm
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import pandas as pd
import numpy as np
from get_rec import get_recommendations

# Initializing Flask application
app = Flask(__name__)

# Setting up Flask app configurations
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///new-books-collection.db"
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.init_app(app)
db.init_app(app)

# Movie Database API URL setups
url = "https://api.themoviedb.org/3/search/movie?include_adult=false&language=en-US&page=1"
url_movie = "https://api.themoviedb.org/3/movie/1637?language=en-US"
MOVIE_DB_API_KEY = "3ebc96e98b766195e11b1d7e3ce199a2"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"

# Loading data from CSV files with the movie info and numpy array with similarity matrix
df2 = pd.read_csv('movies_final.csv')
df3 = pd.read_csv('links.csv')
cos_sim = np.load("cosine_sim.npy")

# Loading user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Defining User database model
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(100))

    # Relationship to Movie table
    movies = relationship('Movie', back_populates='user')


# Defining Movie database model
class Movie(db.Model):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    tmdb_id = Column(Integer, nullable=False)
    title = Column(String(250), unique=True, nullable=False)
    year = Column(Integer, nullable=False)
    description = Column(String(500), nullable=False)
    rating = Column(Float, nullable=True)
    ranking = Column(Integer, nullable=True)
    review = Column(String(250), nullable=True)
    img_url = Column(String(250), nullable=False)

    # Relationship to User table
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='movies')


# Creating database tables within Flask app context
with app.app_context():
    db.create_all()


# Defining form for finding a movie
class FindMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")


# Route for login page
@app.route("/", methods=['POST', 'GET'])
def login():
    # Checking email and password for authentication
    if request.method == "POST":
        email = request.form.get('email')
        curr_user = User.query.filter_by(email=email).first()
        password = request.form.get('password')

        # Email doesn't exist
        if not curr_user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(curr_user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # Email exists and password correct
        else:
            login_user(curr_user)
            return redirect(url_for('home'))
    return render_template("index.html", current_user=current_user)


# Route for user registration
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        email = request.form.get('email')

        # checking if user exist already
        if User.query.filter_by(email=email).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        # Creating a new user and storing in the database
        password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256', salt_length=8)
        name = request.form.get('name')

        new_user = User()
        new_user.password = password
        new_user.email = email

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("register.html", current_user=current_user)


# Route for home page
@app.route("/home",)
def home():
    print(current_user)
    result = Movie.query.filter_by(user_id=current_user.id).order_by(desc(Movie.rating)).all()

    # Calculating ranking for each movie
    for i in range(len(result)):
        result[i].ranking = i + 1
    db.session.commit()

    # Retrieving recommendations for the user
    rec_id = []
    rec_dict = [False]
    # checks if id is in similarity matrix
    for id in result[:5]:
        if id.tmdb_id in df3['tmdbId']:
            rec_id.append(id.tmdb_id)

    if len(rec_id) > 0:
        rec_dict[0] = True
        # gets recommendations based on user
        rec_list = get_recommendations(rec_id[:3], cos_sim, df2)
        rec_dict = []
        # gets all the data from movie api for the recommendations
        for id in rec_list:
            movie_api_url = f"{MOVIE_DB_INFO_URL}/{id}"
            response = requests.get(movie_api_url, params={
                "api_key": MOVIE_DB_API_KEY, "language": "en-US"})
            data = response.json()
            temp_dict ={}
            temp_dict['title'] = data["title"]
            temp_dict['year'] = data["release_date"].split("-")[0]
            temp_dict['img_url'] = f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}"
            temp_dict['description'] = data["overview"]
            temp_dict['tmdb_id'] = id
            rec_dict.append(temp_dict)
            print(rec_dict)
    len_mov = len(result)
    return render_template("home.html", movies=result[:5], current_user=current_user, rec_list=rec_dict, len_mov=len_mov)


# Route for displaying all movies
@app.route("/full")
def full():
    result = Movie.query.filter_by(user_id=current_user.id).order_by(desc(Movie.rating)).all()

    return render_template("full.html", movies=result, current_user=current_user)


# Route for editing movie details
@app.route("/edit", methods=["POST", "GET"])
def edit():
    if request.method == "POST":
        movie_id = request.form['id']
        movie_to_update = Movie.query.filter_by(id=movie_id, user_id=current_user.id).first()
        movie_to_update.rating = request.form["rating"]
        movie_to_update.review = request.form["review"]
        db.session.commit()
        return redirect(url_for('home'))
    movie_id = request.args.get('id')
    movie_to_update = Movie.query.filter_by(id=movie_id, user_id=current_user.id).first()
    return render_template("edit.html", movie=movie_to_update)


# Route for deleting a movie
@app.route("/delete")
def delete():
    movie_id = request.args.get('id')
    movie_to_delete = Movie.query.filter_by(id=movie_id, user_id=current_user.id).first()
    db.session.delete(movie_to_delete)
    db.session.commit()
    # Redirecting the user to the home page after deletion
    return redirect(url_for('home'))


# Route for adding a movie
@app.route("/add", methods=["POST", "GET"])
def add():
    form = FindMovieForm()
    if form.validate_on_submit():
        movie = form.title.data
        response = requests.get(url, params={"api_key": MOVIE_DB_API_KEY, "query": movie})
        print(response.text)
        data = response.json()["results"]
        return render_template("select.html", data=data)

    return render_template("add.html", form=form)


# Route for finding and adding a movie by its id
@app.route("/find")
def find():
    movie_id = request.args.get('id')
    print([movie_id])

    if movie_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_id}"
        response = requests.get(movie_api_url, params={
            "api_key": MOVIE_DB_API_KEY, "language": "en-US"})
        data = response.json()
        # Creating a new Movie object with retrieved movie details
        new_movie = Movie(
            tmdb_id = movie_id,
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            description=data["overview"]
        )
        # Associate the movie with the current user
        new_movie.user_id = current_user.id

        # Adding the movie to the database session and committing the changes
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit", id=new_movie.id))


# Route for user logout
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# Running the Flask app if the script is executed directly
if __name__ == '__main__':
    app.run(debug=True)
