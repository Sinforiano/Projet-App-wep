import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Configuration des chemins
base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
bcrypt = Bcrypt(app)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'stageboard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cyber_208_secret_key'

db = SQLAlchemy(app)

# --- MODÈLE DE LA BASE DE DONNÉES ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# Création automatique de la base
with app.app_context():
    db.create_all()

# --- LES ROUTES ---

@app.route('/')
def index():
    return '<h1>Bienvenue sur StageBoard</h1><p><a href="/register">Inscription</a> | <a href="/login">Connexion</a></p>'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        password = request.form.get('password')

        # Hachage sécurisé du mot de passe
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(nom=nom, prenom=prenom, email=email, password_hash=hashed_pw)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return "<h2>Inscription réussie !</h2><a href='/login'>Connectez-vous ici</a>"
        except Exception as e:
            db.session.rollback()
            return f"<h2>Erreur :</h2><p>L'email est déjà utilisé.</p><a href='/register'>Réessayer</a>"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # Vérification sécurisée avec Bcrypt
        if user and bcrypt.check_password_hash(user.password_hash, password):
            return f"<h2>Bienvenue {user.prenom} !</h2><p>Connexion réussie.</p><a href='/'>Retour à l'accueil</a>"
        else:
            return "<h2>Erreur :</h2><p>Email ou mot de passe incorrect.</p><a href='/login'>Réessayer</a>"

    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)