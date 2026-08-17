from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import os
import shutil
from datetime import datetime


app = Flask(__name__)


# ================= DATABASE =================

DATABASE = "database.db"

BACKUP_FOLDER = "database/backups"

app.secret_key = "healthcare_secret_key_2026"


# ================= DATABASE CONNECTION =================

def get_db_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ================= CREATE DATABASE =================

def create_table():

    os.makedirs("database", exist_ok=True)

    os.makedirs(BACKUP_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DATABASE)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS patients (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            age INTEGER NOT NULL,

            phone TEXT NOT NULL,

            disease TEXT NOT NULL

        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS doctors (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            specialization TEXT NOT NULL,

            phone TEXT NOT NULL,

            department TEXT NOT NULL

        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_name TEXT NOT NULL,

            doctor_name TEXT NOT NULL,

            appointment_date TEXT NOT NULL,

            appointment_time TEXT NOT NULL,

            reason TEXT NOT NULL

        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)


    existing_user = conn.execute(
        """
        SELECT * FROM users
        WHERE username = ?
        """,
        ("admin",)
    ).fetchone()


    if existing_user is None:

        conn.execute(
            """
            INSERT INTO users
            (username, password)
            VALUES (?, ?)
            """,
            (
                "admin",
                "admin123"
            )
        )


    conn.commit()

    conn.close()


# ================= CREATE BACKUP =================

def create_backup():

    os.makedirs(BACKUP_FOLDER, exist_ok=True)


    if not os.path.exists(DATABASE):

        return None


    current_time = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    backup_filename = (
        "healthcare_backup_"
        + current_time
        + ".db"
    )


    backup_path = os.path.join(
        BACKUP_FOLDER,
        backup_filename
    )


    shutil.copy2(
        DATABASE,
        backup_path
    )


    return backup_path


# ================= LOGIN =================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]


        conn = get_db_connection()


        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            AND password = ?
            """,
            (
                username,
                password
            )
        ).fetchone()


        conn.close()


        if user:

            session["user"] = username

            return redirect("/")


        return render_template(
            "login.html",
            error="Invalid username or password"
        )


    return render_template("login.html")


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ================= HOME =================

@app.route("/")
def home():

    if "user" not in session:

        return redirect("/login")


    conn = get_db_connection()


    total_patients = conn.execute(
        """
        SELECT COUNT(*)
        FROM patients
        """
    ).fetchone()[0]


    total_doctors = conn.execute(
        """
        SELECT COUNT(*)
        FROM doctors
        """
    ).fetchone()[0]


    total_appointments = conn.execute(
        """
        SELECT COUNT(*)
        FROM appointments
        """
    ).fetchone()[0]


    recent_appointments = conn.execute(
        """
        SELECT * FROM appointments

        ORDER BY id DESC

        LIMIT 5
        """
    ).fetchall()


    upcoming_appointments = conn.execute(
        """
        SELECT * FROM appointments

        WHERE appointment_date >= date('now')

        ORDER BY appointment_date ASC,
                 appointment_time ASC

        LIMIT 5
        """
    ).fetchall()


    conn.close()


    return render_template(
        "index.html",

        total_patients=total_patients,

        total_doctors=total_doctors,

        total_appointments=total_appointments,

        recent_appointments=recent_appointments,

        upcoming_appointments=upcoming_appointments
    )


# ================= PATIENTS =================

@app.route("/patients")
def patients():

    if "user" not in session:

        return redirect("/login")


    search = request.args.get(
        "search",
        ""
    )


    conn = get_db_connection()


    if search:

        patients = conn.execute(
            """
            SELECT * FROM patients

            WHERE name LIKE ?

            ORDER BY id DESC
            """,
            (
                "%" + search + "%",
            )
        ).fetchall()


    else:

        patients = conn.execute(
            """
            SELECT * FROM patients

            ORDER BY id DESC
            """
        ).fetchall()


    conn.close()


    return render_template(
        "patients.html",

        patients=patients,

        search=search
    )


# ================= ADD PATIENT =================

@app.route(
    "/add_patient",
    methods=["POST"]
)
def add_patient():

    if "user" not in session:

        return redirect("/login")


    create_backup()


    name = request.form["name"]

    age = request.form["age"]

    phone = request.form["phone"]

    disease = request.form["disease"]


    conn = get_db_connection()


    conn.execute(
        """
        INSERT INTO patients
        (
            name,
            age,
            phone,
            disease
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            age,
            phone,
            disease
        )
    )


    conn.commit()

    conn.close()


    return redirect("/patients")


# ================= DELETE PATIENT =================

@app.route(
    "/delete_patient/<int:patient_id>"
)
def delete_patient(patient_id):

    if "user" not in session:

        return redirect("/login")


    create_backup()


    conn = get_db_connection()


    patient = conn.execute(
        """
        SELECT name FROM patients
        WHERE id = ?
        """,
        (patient_id,)
    ).fetchone()


    if patient:

        patient_name = patient["name"]


        conn.execute(
            """
            DELETE FROM appointments

            WHERE patient_name = ?
            """,
            (patient_name,)
        )


        conn.execute(
            """
            DELETE FROM patients

            WHERE id = ?
            """,
            (patient_id,)
        )


    conn.commit()

    conn.close()


    return redirect("/patients")


# ================= EDIT PATIENT =================

@app.route(
    "/edit_patient/<int:patient_id>",
    methods=["GET", "POST"]
)
def edit_patient(patient_id):

    if "user" not in session:

        return redirect("/login")


    conn = get_db_connection()


    if request.method == "POST":

        create_backup()


        name = request.form["name"]

        age = request.form["age"]

        phone = request.form["phone"]

        disease = request.form["disease"]


        old_patient = conn.execute(
            """
            SELECT name FROM patients
            WHERE id = ?
            """,
            (patient_id,)
        ).fetchone()


        if old_patient:

            old_name = old_patient["name"]


            conn.execute(
                """
                UPDATE patients

                SET name = ?,
                    age = ?,
                    phone = ?,
                    disease = ?

                WHERE id = ?
                """,
                (
                    name,
                    age,
                    phone,
                    disease,
                    patient_id
                )
            )


            conn.execute(
                """
                UPDATE appointments

                SET patient_name = ?

                WHERE patient_name = ?
                """,
                (
                    name,
                    old_name
                )
            )


        conn.commit()

        conn.close()


        return redirect("/patients")


    patient = conn.execute(
        """
        SELECT * FROM patients

        WHERE id = ?
        """,
        (patient_id,)
    ).fetchone()


    conn.close()


    return render_template(
        "edit_patient.html",

        patient=patient
    )


# ================= DOCTORS =================

@app.route("/doctors")
def doctors():

    if "user" not in session:

        return redirect("/login")


    search = request.args.get(
        "search",
        ""
    )


    conn = get_db_connection()


    if search:

        doctors = conn.execute(
            """
            SELECT * FROM doctors

            WHERE name LIKE ?

            ORDER BY id DESC
            """,
            (
                "%" + search + "%",
            )
        ).fetchall()


    else:

        doctors = conn.execute(
            """
            SELECT * FROM doctors

            ORDER BY id DESC
            """
        ).fetchall()


    conn.close()


    return render_template(
        "doctors.html",

        doctors=doctors,

        search=search
    )


# ================= ADD DOCTOR =================

@app.route(
    "/add_doctor",
    methods=["POST"]
)
def add_doctor():

    if "user" not in session:

        return redirect("/login")


    create_backup()


    name = request.form["name"]

    specialization = request.form["specialization"]

    phone = request.form["phone"]

    department = request.form["department"]


    conn = get_db_connection()


    conn.execute(
        """
        INSERT INTO doctors
        (
            name,
            specialization,
            phone,
            department
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            specialization,
            phone,
            department
        )
    )


    conn.commit()

    conn.close()


    return redirect("/doctors")


# ================= DELETE DOCTOR =================

@app.route(
    "/delete_doctor/<int:doctor_id>"
)
def delete_doctor(doctor_id):

    if "user" not in session:

        return redirect("/login")


    create_backup()


    conn = get_db_connection()


    doctor = conn.execute(
        """
        SELECT name FROM doctors

        WHERE id = ?
        """,
        (doctor_id,)
    ).fetchone()


    if doctor:

        doctor_name = doctor["name"]


        conn.execute(
            """
            DELETE FROM appointments

            WHERE doctor_name = ?
            """,
            (doctor_name,)
        )


        conn.execute(
            """
            DELETE FROM doctors

            WHERE id = ?
            """,
            (doctor_id,)
        )


    conn.commit()

    conn.close()


    return redirect("/doctors")


# ================= EDIT DOCTOR =================

@app.route(
    "/edit_doctor/<int:doctor_id>",
    methods=["GET", "POST"]
)
def edit_doctor(doctor_id):

    if "user" not in session:

        return redirect("/login")


    conn = get_db_connection()


    if request.method == "POST":

        create_backup()


        name = request.form["name"]

        specialization = request.form["specialization"]

        phone = request.form["phone"]

        department = request.form["department"]


        old_doctor = conn.execute(
            """
            SELECT name FROM doctors

            WHERE id = ?
            """,
            (doctor_id,)
        ).fetchone()


        if old_doctor:

            old_name = old_doctor["name"]


            conn.execute(
                """
                UPDATE doctors

                SET name = ?,
                    specialization = ?,
                    phone = ?,
                    department = ?

                WHERE id = ?
                """,
                (
                    name,
                    specialization,
                    phone,
                    department,
                    doctor_id
                )
            )


            conn.execute(
                """
                UPDATE appointments

                SET doctor_name = ?

                WHERE doctor_name = ?
                """,
                (
                    name,
                    old_name
                )
            )


        conn.commit()

        conn.close()


        return redirect("/doctors")


    doctor = conn.execute(
        """
        SELECT * FROM doctors

        WHERE id = ?
        """,
        (doctor_id,)
    ).fetchone()


    conn.close()


    return render_template(
        "edit_doctor.html",

        doctor=doctor
    )


# ================= APPOINTMENTS =================

@app.route("/appointments")
def appointments():

    if "user" not in session:

        return redirect("/login")


    search = request.args.get(
        "search",
        ""
    )


    conn = get_db_connection()


    patients = conn.execute(
        """
        SELECT * FROM patients

        ORDER BY name
        """
    ).fetchall()


    doctors = conn.execute(
        """
        SELECT * FROM doctors

        ORDER BY name
        """
    ).fetchall()


    if search:

        appointments = conn.execute(
            """
            SELECT * FROM appointments

            WHERE patient_name LIKE ?

            OR doctor_name LIKE ?

            ORDER BY id DESC
            """,
            (
                "%" + search + "%",

                "%" + search + "%"
            )
        ).fetchall()


    else:

        appointments = conn.execute(
            """
            SELECT * FROM appointments

            ORDER BY id DESC
            """
        ).fetchall()


    conn.close()


    return render_template(
        "appointments.html",

        appointments=appointments,

        patients=patients,

        doctors=doctors,

        search=search
    )


# ================= ADD APPOINTMENT =================

@app.route(
    "/add_appointment",
    methods=["POST"]
)
def add_appointment():

    if "user" not in session:

        return redirect("/login")


    patient_name = request.form[
        "patient_name"
    ]

    doctor_name = request.form[
        "doctor_name"
    ]

    appointment_date = request.form[
        "appointment_date"
    ]

    appointment_time = request.form[
        "appointment_time"
    ]

    reason = request.form[
        "reason"
    ]


    conn = get_db_connection()


    existing_appointment = conn.execute(
        """
        SELECT * FROM appointments

        WHERE doctor_name = ?

        AND appointment_date = ?

        AND appointment_time = ?
        """,
        (
            doctor_name,

            appointment_date,

            appointment_time
        )
    ).fetchone()


    if existing_appointment:

        conn.close()


        return """
        <script>

            alert(
                "❌ This doctor already has an appointment at this date and time."
            );

            window.location.href =
                "/appointments";

        </script>
        """


    create_backup()


    conn.execute(
        """
        INSERT INTO appointments

        (
            patient_name,
            doctor_name,
            appointment_date,
            appointment_time,
            reason
        )

        VALUES (?, ?, ?, ?, ?)
        """,
        (
            patient_name,

            doctor_name,

            appointment_date,

            appointment_time,

            reason
        )
    )


    conn.commit()

    conn.close()


    return redirect("/appointments")


# ================= DELETE APPOINTMENT =================

@app.route(
    "/delete_appointment/<int:appointment_id>"
)
def delete_appointment(appointment_id):

    if "user" not in session:

        return redirect("/login")


    create_backup()


    conn = get_db_connection()


    conn.execute(
        """
        DELETE FROM appointments

        WHERE id = ?
        """,
        (appointment_id,)
    )


    conn.commit()

    conn.close()


    return redirect("/appointments")


# ================= EDIT APPOINTMENT =================

@app.route(
    "/edit_appointment/<int:appointment_id>",
    methods=["GET", "POST"]
)
def edit_appointment(appointment_id):

    if "user" not in session:

        return redirect("/login")


    conn = get_db_connection()


    if request.method == "POST":

        patient_name = request.form[
            "patient_name"
        ]

        doctor_name = request.form[
            "doctor_name"
        ]

        appointment_date = request.form[
            "appointment_date"
        ]

        appointment_time = request.form[
            "appointment_time"
        ]

        reason = request.form[
            "reason"
        ]


        existing_appointment = conn.execute(
            """
            SELECT * FROM appointments

            WHERE doctor_name = ?

            AND appointment_date = ?

            AND appointment_time = ?

            AND id != ?
            """,
            (
                doctor_name,

                appointment_date,

                appointment_time,

                appointment_id
            )
        ).fetchone()


        if existing_appointment:

            conn.close()


            return """
            <script>

                alert(
                    "❌ This doctor already has another appointment at this date and time."
                );

                window.history.back();

            </script>
            """


        create_backup()


        conn.execute(
            """
            UPDATE appointments

            SET patient_name = ?,

                doctor_name = ?,

                appointment_date = ?,

                appointment_time = ?,

                reason = ?

            WHERE id = ?
            """,
            (
                patient_name,

                doctor_name,

                appointment_date,

                appointment_time,

                reason,

                appointment_id
            )
        )


        conn.commit()

        conn.close()


        return redirect("/appointments")


    appointment = conn.execute(
        """
        SELECT * FROM appointments

        WHERE id = ?
        """,
        (appointment_id,)
    ).fetchone()


    patients = conn.execute(
        """
        SELECT * FROM patients

        ORDER BY name
        """
    ).fetchall()


    doctors = conn.execute(
        """
        SELECT * FROM doctors

        ORDER BY name
        """
    ).fetchall()


    conn.close()


    return render_template(
        "edit_appointment.html",

        appointment=appointment,

        patients=patients,

        doctors=doctors
    )


# ================= BACKUP DATABASE =================

@app.route("/backup")
def backup_database():

    if "user" not in session:

        return redirect("/login")


    backup_path = create_backup()


    if backup_path is None:

        return "Database file not found."


    return send_file(
        backup_path,
        as_attachment=True
    )


# ================= RUN APPLICATION =================

if __name__ == "__main__":

    create_table()

    app.run(
        debug=True
    )