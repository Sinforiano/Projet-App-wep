#  StageBoard

> Application web de gestion de stage avec suivi des échéances, journal d’activité et API sécurisée par JWT.

---

## 🧠 Overview

StageBoard est une application web développée avec Flask permettant aux étudiants de suivre leur stage :

- Gestion des échéances
- Suivi de progression
- Journal d’activités
- Informations entreprise
- API REST sécurisée

---

## 🏗️ Architecture

Client (Browser)
│
├── Templates (HTML / CSS / JS)
│
└── API REST (JSON)
        │
     Flask App
        │
 ├── Routes
 ├── Models (SQLAlchemy)
 └── SQLite DB

---

## 🗃️ Data Model

### User
- id (PK)
- nom
- prenom
- email (unique)
- password_hash
- filiere
- annee

### Stage
- id
- user_id (FK)
- type_stage
- date_debut
- date_fin
- actif

### Echeance
- id
- stage_id (FK)
- titre
- description
- date_limite
- statut (a_venir, termine, retard)

### Journal
- id
- stage_id (FK)
- date_entree
- taches
- competences
- difficultes

### Entreprise
- id
- stage_id (FK)
- nom
- secteur
- adresse
- tuteur_nom
- tuteur_email

---

## 🔐 Sécurité

- Hash des mots de passe avec Bcrypt
- Authentification via session (web)
- Authentification JWT (API)
- Token expirant après 1 heure

---

## ⚙️ Installation

```bash
git clone https://github.com/ton-username/projet-app-web.git
cd projet-app-web

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install flask flask_sqlalchemy flask_bcrypt flask_jwt_extended python-dotenv

python app.py
