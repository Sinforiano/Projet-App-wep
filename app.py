import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import date, datetime
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(base_dir, 'stageboard.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'stageboard_secret_key_2026')

db = SQLAlchemy(app)

# --- CONTEXT PROCESSOR ALERTES ---
@app.context_processor
def inject_alertes():
    if 'user_id' in session:
        stage = Stage.query.filter_by(
            user_id=session['user_id'], actif=True
        ).first()
        if stage:
            today = date.today()
            count = 0
            for e in stage.echeances:
                if e.statut != 'termine':
                    jours = (date.fromisoformat(e.date_limite) - today).days
                    if 0 <= jours <= 7:
                        count += 1
            return dict(alertes_count=count)
    return dict(alertes_count=0)

# --- MODÈLES ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    filiere = db.Column(db.String(100))
    annee = db.Column(db.String(20))
    stages = db.relationship('Stage', backref='etudiant', lazy=True)

class Stage(db.Model):
    __tablename__ = 'stages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type_stage = db.Column(db.String(50))
    date_debut = db.Column(db.String(20))
    date_fin = db.Column(db.String(20))
    actif = db.Column(db.Boolean, default=True)
    echeances = db.relationship('Echeance', backref='stage', lazy=True)
    entrees = db.relationship('Journal', backref='stage', lazy=True)
    entreprise = db.relationship('Entreprise', backref='stage', uselist=False)

class Echeance(db.Model):
    __tablename__ = 'echeances'
    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=False)
    titre = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date_limite = db.Column(db.String(20), nullable=False)
    statut = db.Column(db.String(20), default='a_venir')

class Journal(db.Model):
    __tablename__ = 'journal'
    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=False)
    date_entree = db.Column(db.String(20), nullable=False)
    taches = db.Column(db.Text)
    competences = db.Column(db.Text)
    difficultes = db.Column(db.Text)

class Entreprise(db.Model):
    __tablename__ = 'entreprises'
    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=False)
    nom = db.Column(db.String(100))
    secteur = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    site_web = db.Column(db.String(100))
    tuteur_nom = db.Column(db.String(100))
    tuteur_poste = db.Column(db.String(100))
    tuteur_email = db.Column(db.String(120))
    tuteur_telephone = db.Column(db.String(20))
    notes = db.Column(db.Text)

with app.app_context():
    db.create_all()

# --- HELPERS ---
def get_stage_actif():
    return Stage.query.filter_by(
        user_id=session['user_id'], actif=True
    ).first()

def update_statuts(stage_id):
    today = date.today().isoformat()
    echeances = Echeance.query.filter_by(stage_id=stage_id).all()
    for e in echeances:
        if e.statut != 'termine' and e.date_limite < today:
            e.statut = 'retard'
    db.session.commit()

# --- ROUTES AUTH ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        password = request.form.get('password')
        filiere = request.form.get('filiere')
        annee = request.form.get('annee')
        type_stage = request.form.get('type_stage')
        date_debut = request.form.get('date_debut')
        date_fin = request.form.get('date_fin')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            nom=nom, prenom=prenom, email=email,
            password_hash=hashed_pw, filiere=filiere,
            annee=annee
        )
        try:
            db.session.add(new_user)
            db.session.flush()
            premier_stage = Stage(
                user_id=new_user.id,
                type_stage=type_stage,
                date_debut=date_debut,
                date_fin=date_fin,
                actif=True
            )
            db.session.add(premier_stage)
            db.session.commit()
            flash('Compte créé avec succès ! Connectez-vous.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Email déjà utilisé.', 'danger')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_prenom'] = user.prenom
            flash(f'Bienvenue {user.prenom} !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Déconnexion réussie.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARD ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if user is None:
        session.clear()
        return redirect(url_for('login'))

    stage = get_stage_actif()
    jours_restants = 0
    progression = 0
    alertes = []

    if stage:
        update_statuts(stage.id)
        if stage.date_debut and stage.date_fin:
            debut = date.fromisoformat(stage.date_debut)
            fin = date.fromisoformat(stage.date_fin)
            today = date.today()
            total_jours = (fin - debut).days
            jours_passes = (today - debut).days
            jours_restants = max((fin - today).days, 0)
            progression = min(round((jours_passes / total_jours) * 100), 100) if total_jours > 0 else 0

        for e in stage.echeances:
            if e.statut != 'termine':
                jours = (date.fromisoformat(e.date_limite) - date.today()).days
                if 0 <= jours <= 7:
                    alertes.append(e)

        total_echeances = len(stage.echeances)
        echeances_retard = sum(1 for e in stage.echeances if e.statut == 'retard')
        prochaine_echeance = Echeance.query.filter_by(
            stage_id=stage.id
        ).filter(Echeance.statut != 'termine').order_by(Echeance.date_limite).first()
        derniere_entree = Journal.query.filter_by(
            stage_id=stage.id
        ).order_by(Journal.date_entree.desc()).first()
    else:
        total_echeances = 0
        echeances_retard = 0
        prochaine_echeance = None
        derniere_entree = None

    return render_template('dashboard.html',
        stage=stage,
        jours_restants=jours_restants,
        progression=progression,
        total_echeances=total_echeances,
        echeances_retard=echeances_retard,
        prochaine_echeance=prochaine_echeance,
        derniere_entree=derniere_entree,
        alertes=alertes
    )

# --- STAGES ---

@app.route('/stages/nouveau', methods=['GET', 'POST'])
def nouveau_stage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        ancien = get_stage_actif()
        if ancien:
            ancien.actif = False
        nouveau = Stage(
            user_id=session['user_id'],
            type_stage=request.form.get('type_stage'),
            date_debut=request.form.get('date_debut'),
            date_fin=request.form.get('date_fin'),
            actif=True
        )
        db.session.add(nouveau)
        db.session.commit()
        flash('Nouveau stage créé !', 'success')
        return redirect(url_for('dashboard'))
    return render_template('nouveau_stage.html')

@app.route('/stages/historique')
def historique_stages():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stages = Stage.query.filter_by(
        user_id=session['user_id']
    ).order_by(Stage.date_debut.desc()).all()
    return render_template('historique_stages.html', stages=stages)

# --- ÉCHÉANCES ---

@app.route('/echeances')
def echeances():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stage = get_stage_actif()
    if not stage:
        flash("Créez d'abord un stage.", 'warning')
        return redirect(url_for('nouveau_stage'))
    update_statuts(stage.id)
    filtre = request.args.get('filtre', 'tous')
    if filtre == 'tous':
        liste = Echeance.query.filter_by(stage_id=stage.id).order_by(Echeance.date_limite).all()
    else:
        liste = Echeance.query.filter_by(stage_id=stage.id, statut=filtre).order_by(Echeance.date_limite).all()
    return render_template('echeances.html', echeances=liste, filtre=filtre)

@app.route('/echeances/ajouter', methods=['POST'])
def ajouter_echeance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stage = get_stage_actif()
    if not stage:
        return redirect(url_for('nouveau_stage'))
    nouvelle = Echeance(
        stage_id=stage.id,
        titre=request.form.get('titre'),
        description=request.form.get('description'),
        date_limite=request.form.get('date_limite'),
        statut=request.form.get('statut')
    )
    db.session.add(nouvelle)
    db.session.commit()
    flash('Échéance ajoutée !', 'success')
    return redirect(url_for('echeances'))

@app.route('/echeances/terminer/<int:id>')
def terminer_echeance(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    e = db.session.get(Echeance, id)
    stage = get_stage_actif()
    if e and stage and e.stage_id == stage.id:
        e.statut = 'termine'
        db.session.commit()
        flash('Échéance terminée !', 'success')
    return redirect(url_for('echeances'))

@app.route('/echeances/supprimer/<int:id>')
def supprimer_echeance(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    e = db.session.get(Echeance, id)
    stage = get_stage_actif()
    if e and stage and e.stage_id == stage.id:
        db.session.delete(e)
        db.session.commit()
        flash('Échéance supprimée.', 'info')
    return redirect(url_for('echeances'))

# --- JOURNAL ---

@app.route('/journal')
def journal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stage = get_stage_actif()
    if not stage:
        flash("Créez d'abord un stage.", 'warning')
        return redirect(url_for('nouveau_stage'))
    date_debut = request.args.get('date_debut', '')
    date_fin = request.args.get('date_fin', '')
    query = Journal.query.filter_by(stage_id=stage.id)
    if date_debut:
        query = query.filter(Journal.date_entree >= date_debut)
    if date_fin:
        query = query.filter(Journal.date_entree <= date_fin)
    entrees = query.order_by(Journal.date_entree.desc()).all()
    return render_template('journal.html', entrees=entrees,
                           date_debut=date_debut, date_fin=date_fin)

@app.route('/journal/ajouter', methods=['POST'])
def ajouter_journal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stage = get_stage_actif()
    if not stage:
        return redirect(url_for('nouveau_stage'))
    nouvelle = Journal(
        stage_id=stage.id,
        date_entree=request.form.get('date_entree'),
        taches=request.form.get('taches'),
        competences=request.form.get('competences'),
        difficultes=request.form.get('difficultes')
    )
    db.session.add(nouvelle)
    db.session.commit()
    flash('Entrée ajoutée !', 'success')
    return redirect(url_for('journal'))

@app.route('/journal/supprimer/<int:id>')
def supprimer_journal(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    entree = db.session.get(Journal, id)
    stage = get_stage_actif()
    if entree and stage and entree.stage_id == stage.id:
        db.session.delete(entree)
        db.session.commit()
        flash('Entrée supprimée.', 'info')
    return redirect(url_for('journal'))

# --- ENTREPRISE ---

@app.route('/entreprise')
def entreprise():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stage = get_stage_actif()
    if not stage:
        flash("Créez d'abord un stage.", 'warning')
        return redirect(url_for('nouveau_stage'))
    ent = Entreprise.query.filter_by(stage_id=stage.id).first()
    return render_template('entreprise.html', entreprise=ent)

@app.route('/entreprise/sauvegarder', methods=['POST'])
def sauvegarder_entreprise():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stage = get_stage_actif()
    if not stage:
        return redirect(url_for('nouveau_stage'))
    ent = Entreprise.query.filter_by(stage_id=stage.id).first()
    if not ent:
        ent = Entreprise(stage_id=stage.id)
        db.session.add(ent)
    ent.nom = request.form.get('nom')
    ent.secteur = request.form.get('secteur')
    ent.adresse = request.form.get('adresse')
    ent.telephone = request.form.get('telephone')
    ent.site_web = request.form.get('site_web')
    ent.tuteur_nom = request.form.get('tuteur_nom')
    ent.tuteur_poste = request.form.get('tuteur_poste')
    ent.tuteur_email = request.form.get('tuteur_email')
    ent.tuteur_telephone = request.form.get('tuteur_telephone')
    ent.notes = request.form.get('notes')
    db.session.commit()
    flash('Entreprise sauvegardée !', 'success')
    return redirect(url_for('entreprise'))

# --- PROFIL ---

@app.route('/profil')
def profil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    stages = Stage.query.filter_by(
        user_id=session['user_id']
    ).order_by(Stage.date_debut.desc()).all()
    return render_template('profil.html', user=user, stages=stages)

@app.route('/profil/modifier', methods=['POST'])
def modifier_profil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    user.nom = request.form.get('nom')
    user.prenom = request.form.get('prenom')
    user.email = request.form.get('email')
    user.filiere = request.form.get('filiere')
    user.annee = request.form.get('annee')
    db.session.commit()
    session['user_prenom'] = user.prenom
    flash('Profil mis à jour !', 'success')
    return redirect(url_for('profil'))

@app.route('/profil/password', methods=['POST'])
def changer_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    ancien = request.form.get('ancien_password')
    nouveau = request.form.get('nouveau_password')
    confirm = request.form.get('confirm_password')
    if not bcrypt.check_password_hash(user.password_hash, ancien):
        flash('Mot de passe actuel incorrect.', 'danger')
    elif nouveau != confirm:
        flash('Les mots de passe ne correspondent pas.', 'danger')
    else:
        user.password_hash = bcrypt.generate_password_hash(nouveau).decode('utf-8')
        db.session.commit()
        flash('Mot de passe changé !', 'success')
    return redirect(url_for('profil'))

# --- 404 ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)