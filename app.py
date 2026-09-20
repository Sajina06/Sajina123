import csv
import io
import os
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for, Response
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///disease_risk.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please login to continue."


DISEASES = [
    "Diabetes",
    "Heart Disease",
    "Kidney Disease",
    "Liver Disease",
    "Hypertension",
]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predictions = db.relationship(
        "Prediction",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def is_active(self):
        return self.is_active_user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    disease = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(30))
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    blood_pressure = db.Column(db.Float)
    blood_sugar = db.Column(db.Float)
    cholesterol = db.Column(db.Float)
    smoking = db.Column(db.String(20))
    family_history = db.Column(db.String(20))
    risk_level = db.Column(db.String(20))
    probability = db.Column(db.Float)
    result = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    disease = db.Column(db.String(80), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    records = db.Column(db.Integer, default=0)
    version = db.Column(db.String(50), default="v1")
    status = db.Column(db.String(30), default="Uploaded")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class MLModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disease = db.Column(db.String(80), unique=True, nullable=False)
    model_name = db.Column(db.String(150))
    filename = db.Column(db.String(255))
    version = db.Column(db.String(50), default="v1")
    accuracy = db.Column(db.Float)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)
    f1_score = db.Column(db.Float)
    status = db.Column(db.String(30), default="Not Loaded")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(180))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_app_data():
    return {
        "diseases": DISEASES,
        "logged_in": current_user.is_authenticated,
    }


def calculate_demo_prediction(data):
    score = 0

    age = float(data.get("age") or 0)
    bp = float(data.get("blood_pressure") or 0)
    sugar = float(data.get("blood_sugar") or 0)
    cholesterol = float(data.get("cholesterol") or 0)

    if age >= 50:
        score += 20
    if bp >= 140:
        score += 25
    if sugar >= 126:
        score += 30
    if cholesterol >= 240:
        score += 20
    if data.get("smoking") == "Yes":
        score += 10
    if data.get("family_history") == "Yes":
        score += 10

    if score >= 60:
        return "High", min(score, 95), "Higher risk indicators were detected."
    if score >= 30:
        return "Medium", min(score, 70), "Some risk indicators were detected."
    return "Low", max(score, 5), "Fewer risk indicators were detected."


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        message = ContactMessage(
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            subject=request.form.get("subject", "").strip(),
            message=request.form.get("message", "").strip(),
        )
        if not message.name or not message.email or not message.message:
            flash("Please fill all required fields.", "error")
        else:
            db.session.add(message)
            db.session.commit()
            flash("Your message has been sent.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Email is already registered.", "error")
            return render_template("auth/register.html")

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html")

        if not user.is_active_user:
            flash("Your account is inactive.", "error")
            return render_template("auth/login.html")

        login_user(user)
        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("admin_dashboard" if user.role == "admin" else "dashboard"))

    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))

    predictions = (
        Prediction.query.filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "user/dashboard.html",
        predictions=predictions,
        total_predictions=Prediction.query.filter_by(user_id=current_user.id).count(),
    )


@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        data = request.form
        disease = data.get("disease")

        if disease not in DISEASES:
            flash("Please select a valid disease.", "error")
            return render_template("user/predict.html")

        risk, probability, result = calculate_demo_prediction(data)

        prediction = Prediction(
            user_id=current_user.id,
            disease=disease,
            age=int(data.get("age") or 0),
            gender=data.get("gender"),
            height=float(data.get("height") or 0),
            weight=float(data.get("weight") or 0),
            blood_pressure=float(data.get("blood_pressure") or 0),
            blood_sugar=float(data.get("blood_sugar") or 0),
            cholesterol=float(data.get("cholesterol") or 0),
            smoking=data.get("smoking"),
            family_history=data.get("family_history"),
            risk_level=risk,
            probability=probability,
            result=result,
        )
        db.session.add(prediction)
        db.session.commit()

        return render_template(
            "user/predict.html",
            prediction=prediction,
            submitted=True,
        )

    return render_template("user/predict.html")


@app.route("/history")
@login_required
def history():
    if current_user.role == "admin":
        return redirect(url_for("admin_predictions"))

    predictions = (
        Prediction.query.filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    return render_template("user/history.html", predictions=predictions)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.role == "admin":
        return redirect(url_for("admin_settings"))

    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name).strip()
        current_user.email = request.form.get("email", current_user.email).strip().lower()

        password = request.form.get("password", "")
        if password:
            current_user.set_password(password)

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("user/profile.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    recent = Prediction.query.order_by(Prediction.created_at.desc()).limit(8).all()
    return render_template(
        "admin/dashboard.html",
        total_users=User.query.filter_by(role="user").count(),
        total_predictions=Prediction.query.count(),
        total_datasets=Dataset.query.count(),
        total_models=MLModel.query.count(),
        unread_messages=ContactMessage.query.filter_by(is_read=False).count(),
        recent_predictions=recent,
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter(
            (User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
        )
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users, q=q)


@app.route("/admin/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin_users"))
    if user.role == "admin":
        flash("Admin accounts cannot be deactivated here.", "error")
        return redirect(url_for("admin_users"))
    user.is_active_user = not user.is_active_user
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete")
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin_users"))
    if user.id == current_user.id or user.role == "admin":
        flash("This account cannot be deleted here.", "error")
        return redirect(url_for("admin_users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/predictions")
@admin_required
def admin_predictions():
    disease = request.args.get("disease", "")
    risk = request.args.get("risk", "")

    query = Prediction.query
    if disease:
        query = query.filter_by(disease=disease)
    if risk:
        query = query.filter_by(risk_level=risk)

    predictions = query.order_by(Prediction.created_at.desc()).all()
    return render_template(
        "admin/predictions.html",
        predictions=predictions,
        selected_disease=disease,
        selected_risk=risk,
    )


@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    disease_counts = (
        db.session.query(Prediction.disease, func.count(Prediction.id))
        .group_by(Prediction.disease)
        .all()
    )
    risk_counts = (
        db.session.query(Prediction.risk_level, func.count(Prediction.id))
        .group_by(Prediction.risk_level)
        .all()
    )
    return render_template(
        "admin/analytics.html",
        disease_counts=disease_counts,
        risk_counts=risk_counts,
    )


@app.route("/admin/datasets", methods=["GET", "POST"])
@admin_required
def admin_datasets():
    if request.method == "POST":
        file = request.files.get("dataset")
        disease = request.form.get("disease")
        name = request.form.get("name", "").strip()

        if not file or not file.filename:
            flash("Please select a CSV file.", "error")
            return redirect(url_for("admin_datasets"))

        if not file.filename.lower().endswith(".csv"):
            flash("Only CSV files are supported.", "error")
            return redirect(url_for("admin_datasets"))

        try:
            content = file.read().decode("utf-8-sig")
            records = max(0, len(content.splitlines()) - 1)
        except UnicodeDecodeError:
            flash("Could not read the CSV file as UTF-8.", "error")
            return redirect(url_for("admin_datasets"))

        dataset = Dataset(
            name=name or file.filename,
            disease=disease if disease in DISEASES else "Other",
            filename=file.filename,
            records=records,
            version="v1",
            status="Uploaded",
        )
        db.session.add(dataset)
        db.session.commit()
        flash("Dataset uploaded and recorded.", "success")
        return redirect(url_for("admin_datasets"))

    datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).all()
    return render_template("admin/datasets.html", datasets=datasets)


@app.route("/admin/models")
@admin_required
def admin_models():
    for disease in DISEASES:
        if not MLModel.query.filter_by(disease=disease).first():
            db.session.add(
                MLModel(
                    disease=disease,
                    model_name=f"{disease} Model",
                    filename=f"{disease.lower().replace(' ', '_')}.joblib",
                    status="Not Loaded",
                )
            )
    db.session.commit()
    models = MLModel.query.order_by(MLModel.disease).all()
    return render_template("admin/models.html", models=models)


@app.route("/admin/reports")
@admin_required
def admin_reports():
    return render_template(
        "admin/reports.html",
        total_users=User.query.filter_by(role="user").count(),
        total_predictions=Prediction.query.count(),
        total_datasets=Dataset.query.count(),
    )


@app.route("/admin/reports/predictions.csv")
@admin_required
def prediction_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "User",
            "Email",
            "Disease",
            "Risk",
            "Probability",
            "Age",
            "Created At",
        ]
    )
    for p in Prediction.query.order_by(Prediction.created_at.desc()).all():
        writer.writerow(
            [
                p.id,
                p.user.name,
                p.user.email,
                p.disease,
                p.risk_level,
                p.probability,
                p.age,
                p.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=predictions.csv"},
    )


@app.route("/admin/messages")
@admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/messages/<int:message_id>/read")
@admin_required
def mark_message_read(message_id):
    message = db.session.get(ContactMessage, message_id)
    if message:
        message.is_read = True
        db.session.commit()
        flash("Message marked as read.", "success")
    return redirect(url_for("admin_messages"))


@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        if name:
            current_user.name = name
        if password:
            current_user.set_password(password)

        db.session.commit()
        flash("Admin settings updated.", "success")
        return redirect(url_for("admin_settings"))

    return render_template("admin/settings.html")


@app.cli.command("init-db")
def init_db():
    db.create_all()

    admin_email = "admin@diseaserisk.local"
    admin = User.query.filter_by(email=admin_email).first()

    if not admin:
        admin = User(
            name="System Administrator",
            email=admin_email,
            role="admin",
        )
        admin.set_password("Admin@123")
        db.session.add(admin)

    db.session.commit()
    print("Database initialized.")
    print("Admin: admin@diseaserisk.local / Admin@123")


if __name__ == "__main__":
    app.run(debug=True)
