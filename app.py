import streamlit as st
import sqlite3
import json
import uuid
import io
from datetime import datetime

import pandas as pd
import qrcode

from ai.form_generator import (
    generate_form,
    generate_form_from_file,
    generate_form_from_audio,
    modify_form
)
from utils.pdf_generator import generate_response_pdf
from utils.schema import FormSchema


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FormFlow-AI",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

/* =========================================================
   GLOBAL
   ========================================================= */

.stApp {
    background: #f7f8fc;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* =========================================================
   SIDEBAR
   ========================================================= */

[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #1f2937;
}

[data-testid="stSidebar"] * {
    color: #f9fafb;
}

[data-testid="stSidebar"] .stButton button {
    background: transparent;
    border: 1px solid transparent;
    color: #e5e7eb;
    text-align: left;
    border-radius: 10px;
    padding: 10px 14px;
    transition: all 0.2s ease;
}

[data-testid="stSidebar"] .stButton button:hover {
    background: #1f2937;
    border-color: #374151;
}

/* =========================================================
   HEADINGS
   ========================================================= */

h1 {
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}

h2 {
    font-weight: 700 !important;
}

h3 {
    font-weight: 650 !important;
}

/* =========================================================
   BUTTONS
   ========================================================= */

.stButton > button {
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
    border: 1px solid #d1d5db;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
}

/* =========================================================
   PRIMARY BUTTON
   ========================================================= */

.stButton > button[kind="primary"] {
    border-radius: 10px;
    font-weight: 700;
}

/* =========================================================
   INPUTS
   ========================================================= */

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input,
.stSelectbox div[data-baseweb="select"],
.stMultiSelect div[data-baseweb="select"] {
    border-radius: 9px;
}

/* =========================================================
   FILE UPLOADER
   ========================================================= */

[data-testid="stFileUploader"] {
    border-radius: 12px;
}

/* =========================================================
   METRIC CARDS
   ========================================================= */

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

[data-testid="stMetricLabel"] {
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    font-weight: 800;
}

/* =========================================================
   DATAFRAMES
   ========================================================= */

[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* =========================================================
   EXPANDERS
   ========================================================= */

[data-testid="stExpander"] {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: white;
}

/* =========================================================
   ALERTS
   ========================================================= */

[data-testid="stAlert"] {
    border-radius: 10px;
}

/* =========================================================
   CARDS
   ========================================================= */

.formflow-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
}

.formflow-card-title {
    font-size: 20px;
    font-weight: 750;
    margin-bottom: 6px;
}

.formflow-card-description {
    color: #6b7280;
    font-size: 14px;
    line-height: 1.6;
}

/* =========================================================
   HERO SECTION
   ========================================================= */

.formflow-hero {
    background: linear-gradient(
        135deg,
        #111827,
        #1f2937
    );
    border-radius: 20px;
    padding: 34px;
    margin-bottom: 28px;
    color: white;
}

.formflow-hero h1 {
    color: white;
    margin-bottom: 8px;
}

.formflow-hero p {
    color: #d1d5db;
    font-size: 16px;
}

/* =========================================================
   STATUS BADGES
   ========================================================= */

.status-published {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #dcfce7;
    color: #166534;
    font-size: 12px;
    font-weight: 700;
}

.status-draft {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #fef3c7;
    color: #92400e;
    font-size: 12px;
    font-weight: 700;
}

/* =========================================================
   DIVIDERS
   ========================================================= */

hr {
    margin-top: 24px;
    margin-bottom: 24px;
    border-color: #e5e7eb;
}

/* =========================================================
   MOBILE
   ========================================================= */

@media (max-width: 768px) {

    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .formflow-hero {
        padding: 24px;
    }

}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================

DB_NAME = "formflow.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forms (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            schema_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id TEXT PRIMARY KEY,
            form_id TEXT NOT NULL,
            response_json TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY(form_id) REFERENCES forms(id)
        )
    """)

    conn.commit()
    conn.close()


init_database()


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def save_form(form, status="Published"):

    form_id = "FF-" + uuid.uuid4().hex[:8].upper()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO forms
        (id, title, description, schema_json, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            form_id,
            form.title,
            form.description,
            form.model_dump_json(),
            status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()

    return form_id


def get_form(form_id):

    conn = get_connection()

    row = conn.execute(
        "SELECT * FROM forms WHERE id = ?",
        (form_id,)
    ).fetchone()

    conn.close()

    return row


def get_all_forms():

    conn = get_connection()

    rows = conn.execute(
        "SELECT * FROM forms ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return rows


def update_form(form_id, form):

    conn = get_connection()

    conn.execute(
        """
        UPDATE forms
        SET title = ?,
            description = ?,
            schema_json = ?
        WHERE id = ?
        """,
        (
            form.title,
            form.description,
            form.model_dump_json(),
            form_id
        )
    )

    conn.commit()
    conn.close()


def save_response(form_id, response_data):

    response_id = "RESP-" + uuid.uuid4().hex[:8].upper()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO responses
        (id, form_id, response_json, submitted_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            response_id,
            form_id,
            json.dumps(response_data),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()

    return response_id


def get_response_count():

    conn = get_connection()

    row = conn.execute(
        "SELECT COUNT(*) AS count FROM responses"
    ).fetchone()

    conn.close()

    return row["count"]


def get_form_response_count(form_id):

    conn = get_connection()

    row = conn.execute(
        "SELECT COUNT(*) AS count FROM responses WHERE form_id = ?",
        (form_id,)
    ).fetchone()

    conn.close()

    return row["count"]


def get_responses_for_form(form_id):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM responses
        WHERE form_id = ?
        ORDER BY submitted_at DESC
        """,
        (form_id,)
    ).fetchall()

    conn.close()

    return rows


# ============================================================
# QR CODE FUNCTION
# ============================================================

def generate_qr_code(url):

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image()

    return img


# ============================================================
# SESSION STATE
# ============================================================

if "generated_form" not in st.session_state:
    st.session_state.generated_form = None

if "editing_form_id" not in st.session_state:
    st.session_state.editing_form_id = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 📝 FormFlow-AI")

    st.caption("AI-Powered Form Digitization")

    st.divider()

    pages = [
        "Dashboard",
        "Create Form",
        "Form Editor",
        "My Forms",
        "Responses",
        "Analytics",
        "Settings"
    ]

    for page in pages:

        if st.button(
            page,
            use_container_width=True,
            key=f"nav_{page}"
        ):
            st.session_state.page = page
            st.rerun()

    st.divider()

    st.caption("FormFlow-AI")
    st.caption("Intelligent Form Digitization")


# ============================================================
# PUBLIC FORM
# ============================================================

form_id_from_url = st.query_params.get("form_id")

if form_id_from_url:

    row = get_form(form_id_from_url)

    if row is None:

        st.error("Form not found.")

    elif row["status"] != "Published":

        st.warning("This form has not been published.")

    else:

        form_data = json.loads(row["schema_json"])
        form = FormSchema.model_validate(form_data)

        st.markdown(
            f'<div class="dashboard-title">{form.title}</div>',
            unsafe_allow_html=True
        )

        st.write(form.description)

        st.divider()

        with st.form("public_form"):

            answers = {}

            for field in form.fields:

                if field.type == "text":

                    answers[field.name] = st.text_input(
                        field.label,
                        placeholder=field.placeholder or "",
                        help=field.help_text or ""
                    )

                elif field.type == "textarea":

                    answers[field.name] = st.text_area(
                        field.label,
                        placeholder=field.placeholder or "",
                        help=field.help_text or ""
                    )

                elif field.type == "number":

                    answers[field.name] = st.number_input(
                        field.label,
                        help=field.help_text or ""
                    )

                elif field.type == "email":

                    answers[field.name] = st.text_input(
                        field.label,
                        placeholder=field.placeholder or "",
                        help=field.help_text or ""
                    )

                elif field.type == "date":

                    answers[field.name] = st.date_input(
                        field.label,
                        help=field.help_text or ""
                    )

                elif field.type == "select":

                    options = field.options or ["Select"]

                    answers[field.name] = st.selectbox(
                        field.label,
                        options
                    )

                elif field.type == "radio":

                    options = field.options or ["Yes", "No"]

                    answers[field.name] = st.radio(
                        field.label,
                        options
                    )

                elif field.type == "checkbox":

                    answers[field.name] = st.checkbox(
                        field.label,
                        help=field.help_text or ""
                    )

            submitted = st.form_submit_button(
                "🚀 Submit Form",
                use_container_width=True
            )

        if submitted:

            missing_fields = []

            for field in form.fields:

                if field.required:

                    value = answers.get(field.name)

                    if value is None or str(value).strip() == "":
                        missing_fields.append(field.label)

            if missing_fields:

                st.error(
                    "Please fill the required fields: "
                    + ", ".join(missing_fields)
                )

            else:

                for key, value in answers.items():

                    if hasattr(value, "isoformat"):
                        answers[key] = value.isoformat()

                response_id = save_response(
                    form_id_from_url,
                    answers
                )

                st.success(
                    f"Form submitted successfully! "
                    f"Response ID: {response_id}"
                )

    st.stop()


# ============================================================
# DASHBOARD
# ============================================================

if st.session_state.page == "Dashboard":

    st.markdown("""
    <div class="formflow-hero">
        <h1>🤖 FormFlow-AI</h1>
        <p>
            Intelligent form digitization powered by Generative AI.
            Create, publish, collect and analyze forms in one place.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 👋 Welcome to your FormFlow workspace")

    st.caption(
        "Turn paper forms, PDFs, images, text or voice requirements "
        "into interactive digital forms."
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Create, manage and analyze AI-generated digital forms.'
        '</div>',
        unsafe_allow_html=True
    )

    forms = get_all_forms()

    total_forms = len(forms)
    total_responses = get_response_count()

    published_forms = len(
        [f for f in forms if f["status"] == "Published"]
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{total_forms}</div>
                <div class="stat-label">Total Forms</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{published_forms}</div>
                <div class="stat-label">Published Forms</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{total_responses}</div>
                <div class="stat-label">Total Responses</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    st.subheader("🚀 Quick Actions")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "➕ Create New Form",
            use_container_width=True
        ):

            st.session_state.page = "Create Form"
            st.rerun()

    with col2:

        if st.button(
            "📋 View My Forms",
            use_container_width=True
        ):

            st.session_state.page = "My Forms"
            st.rerun()

    st.subheader("📋 Recent Forms")

    if not forms:

        st.info(
            "No forms created yet. "
            "Create your first AI-powered form."
        )

    else:

        for form in forms[:5]:

            count = get_form_response_count(form["id"])

            st.markdown(
                f"""
                <div class="card">
                    <h4>{form["title"]}</h4>
                    <p>{form["description"] or ""}</p>
                    <small>
                    Status: {form["status"]} |
                    Responses: {count} |
                    Created: {form["created_at"]}
                    </small>
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# CREATE FORM
# ============================================================

elif st.session_state.page == "Create Form":

    st.markdown(
        '<div class="dashboard-title">Create New Form</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Generate a digital form using AI from text, PDF, image or voice.'
        '</div>',
        unsafe_allow_html=True
    )

    input_method = st.radio(
        "Choose input method",
        [
            "Text Requirement",
            "Upload PDF / Image",
            "Voice Requirement"
        ],
        horizontal=True
    )


    # ========================================================
    # TEXT REQUIREMENT
    # ========================================================

    if input_method == "Text Requirement":

        requirement = st.text_area(
            "Describe the form you want",
            placeholder=(
                "Example: Create a vehicle service request form "
                "with customer name, email, vehicle number, "
                "vehicle model, service type, preferred date "
                "and additional comments."
            ),
            height=180
        )

        if st.button(
            "✨ Generate Form with AI",
            type="primary",
            use_container_width=True
        ):

            if not requirement.strip():

                st.warning(
                    "Please enter a form requirement."
                )

            else:

                with st.spinner(
                    "AI is understanding your requirement..."
                ):

                    try:

                        form = generate_form(
                            requirement
                        )

                        st.session_state.generated_form = form

                        st.session_state.editing_form_id = None

                        st.session_state.page = "Form Editor"

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Form generation failed: {e}"
                        )


    # ========================================================
    # PDF / IMAGE
    # ========================================================

    elif input_method == "Upload PDF / Image":

        uploaded_file = st.file_uploader(
            "Upload your existing form",
            type=[
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "webp"
            ]
        )

        if uploaded_file:

            st.info(
                f"Uploaded: {uploaded_file.name}"
            )

            if st.button(
                "✨ Convert to Digital Form",
                type="primary",
                use_container_width=True
            ):

                with st.spinner(
                    "AI is analyzing your form..."
                ):

                    try:

                        form = generate_form_from_file(
                            uploaded_file.getvalue(),
                            uploaded_file.type
                        )

                        st.session_state.generated_form = form

                        st.session_state.editing_form_id = None

                        st.session_state.page = "Form Editor"

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Form generation failed: {e}"
                        )


    # ========================================================
    # VOICE REQUIREMENT
    # ========================================================

    elif input_method == "Voice Requirement":

        st.subheader(
            "🎤 Describe Your Form Using Your Voice"
        )

        st.write(
            "Click the microphone button and describe "
            "the form you want to create."
        )

        st.info(
            "Example: "
            "\"Create a vehicle service request form "
            "with customer name, email, vehicle number, "
            "vehicle model, service type, preferred date "
            "and comments.\""
        )

        audio = st.audio_input(
            "🎙️ Record your form requirement"
        )

        if audio:

            st.success(
                "Voice recording captured successfully!"
            )

            st.audio(
                audio
            )

            if st.button(
                "✨ Generate Form from Voice",
                type="primary",
                use_container_width=True
            ):

                with st.spinner(
                    "Gemini is listening and creating your form..."
                ):

                    try:

                        form = generate_form_from_audio(
                            audio.getvalue(),
                            audio.type
                        )

                        st.session_state.generated_form = form

                        st.session_state.editing_form_id = None

                        st.success(
                            "🎉 Form generated from your voice!"
                        )

                        st.session_state.page = "Form Editor"

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Voice form generation failed: {e}"
                        )

# ============================================================
# FORM EDITOR
# ============================================================

elif st.session_state.page == "Form Editor":

    st.markdown(
        '<div class="dashboard-title">Form Editor</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Review and customize the AI-generated form before publishing.'
        '</div>',
        unsafe_allow_html=True
    )

    form = st.session_state.generated_form

    if form is None:

        st.info(
            "No form is currently available for editing."
        )

        if st.button("➕ Create a Form"):

            st.session_state.page = "Create Form"
            st.rerun()

    else:

        # ====================================================
        # BASIC FORM DETAILS
        # ====================================================

        st.subheader("📝 Form Details")

        title = st.text_input(
            "Form Title",
            value=form.title
        )

        description = st.text_area(
            "Form Description",
            value=form.description
        )

        st.divider()

        # ====================================================
        # AI FORM MODIFICATION
        # ====================================================

        st.subheader("🤖 Modify Form with AI")

        st.caption(
            "Describe what you want to change using normal language. "
            "Gemini will understand your instruction and update the existing form."
        )

        ai_modification = st.text_area(
            "What would you like to change?",
            placeholder=(
                "Example: Add an emergency contact number "
                "and make email mandatory."
            ),
            height=120,
            key="ai_form_modification"
        )

        example_col1, example_col2, example_col3 = st.columns(3)

        with example_col1:
            st.info("💡 Add a phone number field")

        with example_col2:
            st.info("💡 Make email required")

        with example_col3:
            st.info("💡 Remove the comments field")

        if st.button(
            "✨ Apply AI Modification",
            type="primary",
            use_container_width=True
        ):

            if not ai_modification.strip():
                st.warning(
                    "Please describe the modification you want to make."
                )
            else:
                with st.spinner(
                    "🤖 Gemini is modifying your form..."
                ):
                    try:
                        modified_form = modify_form(
                            ai_modification,
                            st.session_state.generated_form
                        )

                        st.session_state.generated_form = modified_form

                        st.success(
                            "🎉 Form successfully modified by AI!"
                        )

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"AI modification failed: {e}"
                        )

        st.divider()

        # ====================================================
        # FIELD EDITOR
        # ====================================================

        st.subheader("🧩 Form Fields")

        updated_fields = []

        for index, field in enumerate(form.fields):

            with st.expander(
                f"Field {index + 1}: {field.label}",
                expanded=True
            ):

                col1, col2 = st.columns([3, 1])

                with col1:

                    field_label = st.text_input(
                        "Field Label",
                        value=field.label,
                        key=f"label_{index}"
                    )

                with col2:

                    required = st.checkbox(
                        "Required",
                        value=field.required,
                        key=f"required_{index}"
                    )

                field_name = st.text_input(
                    "Field Name",
                    value=field.name,
                    key=f"name_{index}"
                )

                field_types = [
                    "text",
                    "textarea",
                    "number",
                    "email",
                    "date",
                    "select",
                    "radio",
                    "checkbox"
                ]

                current_type_index = (
                    field_types.index(field.type)
                    if field.type in field_types
                    else 0
                )

                field_type = st.selectbox(
                    "Field Type",
                    field_types,
                    index=current_type_index,
                    key=f"type_{index}"
                )

                placeholder = st.text_input(
                    "Placeholder",
                    value=field.placeholder or "",
                    key=f"placeholder_{index}"
                )

                help_text = st.text_input(
                    "Help Text",
                    value=field.help_text or "",
                    key=f"help_{index}"
                )

                options = None

                if field_type in [
                    "select",
                    "radio"
                ]:

                    current_options = field.options or []

                    options_text = st.text_area(
                        "Options",
                        value="\n".join(current_options),
                        placeholder=(
                            "Enter one option per line"
                        ),
                        key=f"options_{index}"
                    )

                    options = [
                        option.strip()
                        for option in options_text.split("\n")
                        if option.strip()
                    ]

                updated_fields.append(
                    {
                        "name": field_name.strip(),
                        "label": field_label.strip(),
                        "type": field_type,
                        "required": required,
                        "options": options,
                        "placeholder": placeholder,
                        "help_text": help_text
                    }
                )

        st.divider()

        # ====================================================
        # ADD NEW FIELD
        # ====================================================

        st.subheader("➕ Add New Field")

        with st.form("add_field_form"):

            new_label = st.text_input(
                "New Field Label",
                placeholder="Example: Customer Address"
            )

            new_name = st.text_input(
                "Field Name",
                placeholder="customer_address"
            )

            new_type = st.selectbox(
                "Field Type",
                [
                    "text",
                    "textarea",
                    "number",
                    "email",
                    "date",
                    "select",
                    "radio",
                    "checkbox"
                ]
            )

            new_required = st.checkbox(
                "Required"
            )

            new_options_text = ""

            if new_type in [
                "select",
                "radio"
            ]:

                new_options_text = st.text_area(
                    "Options",
                    placeholder=(
                        "Enter one option per line"
                    )
                )

            add_field = st.form_submit_button(
                "➕ Add Field"
            )

        if add_field:

            if not new_label.strip():

                st.warning(
                    "Please enter a field label."
                )

            else:

                if not new_name.strip():

                    generated_name = (
                        new_label
                        .lower()
                        .replace(" ", "_")
                        .replace("-", "_")
                    )

                else:

                    generated_name = (
                        new_name.strip()
                    )

                new_options = None

                if new_type in [
                    "select",
                    "radio"
                ]:

                    new_options = [
                        option.strip()
                        for option in new_options_text.split("\n")
                        if option.strip()
                    ]

                updated_fields.append(
                    {
                        "name": generated_name,
                        "label": new_label.strip(),
                        "type": new_type,
                        "required": new_required,
                        "options": new_options,
                        "placeholder": "",
                        "help_text": ""
                    }
                )

                try:

                    new_form = FormSchema.model_validate(
                        {
                            "title": title,
                            "description": description,
                            "fields": updated_fields
                        }
                    )

                    st.session_state.generated_form = (
                        new_form
                    )

                    st.success(
                        "New field added successfully!"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not add field: {e}"
                    )

        st.divider()

        # ====================================================
        # SAVE / PUBLISH
        # ====================================================

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "💾 Save Changes",
                use_container_width=True
            ):

                try:

                    names = [
                        field["name"]
                        for field in updated_fields
                    ]

                    if len(names) != len(set(names)):

                        st.error(
                            "Field names must be unique."
                        )

                    else:

                        updated_form = (
                            FormSchema.model_validate(
                                {
                                    "title": title.strip(),
                                    "description": (
                                        description.strip()
                                    ),
                                    "fields": updated_fields
                                }
                            )
                        )

                        st.session_state.generated_form = (
                            updated_form
                        )

                        st.success(
                            "Changes saved successfully!"
                        )

                        st.rerun()

                except Exception as e:

                    st.error(
                        f"Unable to save changes: {e}"
                    )

        with col2:

            if st.button(
                "🚀 Publish Form",
                type="primary",
                use_container_width=True
            ):

                try:

                    names = [
                        field["name"]
                        for field in updated_fields
                    ]

                    if len(names) != len(set(names)):

                        st.error(
                            "Field names must be unique."
                        )

                    elif not title.strip():

                        st.error(
                            "Form title cannot be empty."
                        )

                    else:

                        final_form = (
                            FormSchema.model_validate(
                                {
                                    "title": title.strip(),
                                    "description": (
                                        description.strip()
                                    ),
                                    "fields": updated_fields
                                }
                            )
                        )

                        if st.session_state.editing_form_id:

                            update_form(
                                st.session_state.editing_form_id,
                                final_form
                            )

                            published_id = (
                                st.session_state.editing_form_id
                            )

                        else:

                            published_id = save_form(
                                final_form,
                                status="Published"
                            )

                        st.session_state.generated_form = (
                            final_form
                        )

                        st.session_state.editing_form_id = (
                            published_id
                        )

                        st.success(
                            "🎉 Form published successfully!"
                        )

                        # ====================================================
                        # SHAREABLE LINK
                        # ====================================================

                        # Use the current app URL so QR/share links
                        # work both locally and after deployment.
                        base_url = st.context.url
                        form_url = (
                            f"{base_url}?form_id={published_id}"
                        )

                        st.markdown(
                            "### 🔗 Share Your Form"
                        )

                        st.markdown(
                            f"""
                            <div class="form-link">
                            <b>Form ID:</b> {published_id}<br><br>
                            <b>Shareable URL:</b><br>
                            {form_url}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        st.code(
                            form_url,
                            language="text"
                        )

                        # ====================================================
                        # QR CODE
                        # ====================================================

                        st.markdown(
                            "### 📱 QR Code"
                        )

                        qr_image = generate_qr_code(
                            form_url
                        )

                        qr_buffer = io.BytesIO()

                        qr_image.save(
                            qr_buffer,
                            format="PNG"
                        )

                        qr_bytes = (
                            qr_buffer.getvalue()
                        )

                        col_qr1, col_qr2 = st.columns(
                            [1, 2]
                        )

                        with col_qr1:

                            st.image(
                                qr_bytes,
                                caption=(
                                    "Scan to open the form"
                                ),
                                width=250
                            )

                        with col_qr2:

                            st.write(
                                "### 📲 Share with Users"
                            )

                            st.write(
                                "Users can scan this QR code "
                                "with their mobile phone to "
                                "open the published form."
                            )

                            st.download_button(
                                "⬇️ Download QR Code",
                                data=qr_bytes,
                                file_name=(
                                    f"{published_id}_QR.png"
                                ),
                                mime="image/png",
                                use_container_width=True
                            )

                except Exception as e:

                    st.error(
                        f"Unable to publish form: {e}"
                    )

        # ====================================================
        # LIVE PREVIEW
        # ====================================================

        st.divider()

        st.subheader("👀 Form Preview")

        st.markdown(
            '<div class="preview-box">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"### {title}"
        )

        st.write(
            description
        )

        for preview_index, field in enumerate(
            updated_fields
        ):

            label = field["label"]

            if field["required"]:
                label += " *"

            unique_key = (
                f"preview_{preview_index}_{field['name']}"
            )

            if field["type"] == "text":

                st.text_input(
                    label,
                    placeholder=(
                        field["placeholder"]
                        or ""
                    ),
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "textarea":

                st.text_area(
                    label,
                    placeholder=(
                        field["placeholder"]
                        or ""
                    ),
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "number":

                st.number_input(
                    label,
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "email":

                st.text_input(
                    label,
                    placeholder=(
                        field["placeholder"]
                        or ""
                    ),
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "date":

                st.date_input(
                    label,
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "select":

                st.selectbox(
                    label,
                    field["options"]
                    or ["Option 1"],
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "radio":

                st.radio(
                    label,
                    field["options"]
                    or ["Option 1"],
                    disabled=True,
                    key=unique_key
                )

            elif field["type"] == "checkbox":

                st.checkbox(
                    label,
                    disabled=True,
                    key=unique_key
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )


# ============================================================
# MY FORMS
# ============================================================

elif st.session_state.page == "My Forms":

    st.title("📋 My Forms")

    st.caption(
        "Manage, edit, publish and monitor all your forms."
    )

    all_forms = get_all_forms()

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    search_text = st.text_input(
        "🔎 Search forms",
        placeholder="Search by form name..."
    )

    # Filter forms
    if search_text:
        filtered_forms = [
            form for form in all_forms
            if search_text.lower()
            in form["title"].lower()
        ]
    else:
        filtered_forms = all_forms

    # ---------------------------------------------------------
    # FORM COUNT
    # ---------------------------------------------------------

    st.markdown(
        f"### 📁 {len(filtered_forms)} form(s)"
    )

    if not filtered_forms:

        if search_text:
            st.info(
                f"No forms found for '{search_text}'."
            )
        else:
            st.info(
                "No forms have been created yet."
            )

    # ---------------------------------------------------------
    # FORM CARDS
    # ---------------------------------------------------------

    for form in filtered_forms:

        form_id = form["id"]
        title = form["title"]
        description = form["description"]
        status = form["status"]
        created_at = form["created_at"]

        response_count = get_form_response_count(
            form_id
        )

        st.markdown(
            '<div class="formflow-card">',
            unsafe_allow_html=True
        )

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------

        col_info, col_status = st.columns(
            [5, 1]
        )

        with col_info:

            st.markdown(
                f'<div class="formflow-card-title">'
                f'📄 {title}'
                f'</div>',
                unsafe_allow_html=True
            )

            if description:
                st.markdown(
                    f'<div class="formflow-card-description">'
                    f'{description}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        with col_status:

            if status == "Published":

                st.markdown(
                    '<span class="status-published">'
                    '● Published'
                    '</span>',
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    '<span class="status-draft">'
                    '● Draft'
                    '</span>',
                    unsafe_allow_html=True
                )

        st.write("")

        # -----------------------------------------------------
        # FORM INFORMATION
        # -----------------------------------------------------

        info1, info2, info3 = st.columns(3)

        with info1:
            st.caption("🆔 Form ID")
            st.write(form_id)

        with info2:
            st.caption("📝 Responses")
            st.write(response_count)

        with info3:
            st.caption("📅 Created")
            st.write(created_at)

        st.write("")

        # -----------------------------------------------------
        # ACTION BUTTONS
        # -----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        # EDIT
        with col1:

            if st.button(
                "✏️ Edit",
                key=f"edit_{form_id}",
                use_container_width=True
            ):

                form_schema = FormSchema.model_validate(
                    json.loads(form["schema_json"])
                )

                st.session_state.generated_form = form_schema
                st.session_state.editing_form_id = form_id
                st.session_state.page = "Form Editor"

                st.rerun()

        # OPEN
        with col2:

            if st.button(
                "👁️ Open",
                key=f"open_{form_id}",
                use_container_width=True
            ):

                st.query_params["form_id"] = form_id
                st.rerun()

        # DUPLICATE
        with col3:

            if st.button(
                "📋 Duplicate",
                key=f"duplicate_{form_id}",
                use_container_width=True
            ):

                try:

                    original_schema = json.loads(
                        form["schema_json"]
                    )

                    duplicated_schema = FormSchema.model_validate(
                        original_schema
                    )

                    duplicated_schema.title = (
                        f"{duplicated_schema.title} - Copy"
                    )

                    new_id = save_form(
                        duplicated_schema,
                        status="Draft"
                    )

                    st.success(
                        "✅ Form duplicated successfully!"
                    )

                    st.session_state.generated_form = (
                        duplicated_schema
                    )

                    st.session_state.editing_form_id = new_id

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not duplicate form: {e}"
                    )

        # DELETE
        with col4:

            if st.button(
                "🗑️ Delete",
                key=f"delete_{form_id}",
                use_container_width=True
            ):

                st.session_state[
                    f"confirm_delete_{form_id}"
                ] = True

        # -----------------------------------------------------
        # DELETE CONFIRMATION
        # -----------------------------------------------------

        if st.session_state.get(
            f"confirm_delete_{form_id}",
            False
        ):

            st.warning(
                "⚠️ Are you sure you want to delete "
                f"'{title}'?"
            )

            st.caption(
                "This action will remove the form and "
                "its collected responses."
            )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:

                if st.button(
                    "Yes, Delete",
                    key=f"confirm_yes_{form_id}",
                    type="primary",
                    use_container_width=True
                ):

                    try:

                        connection = get_connection()
                        cursor = connection.cursor()

                        # Delete responses first
                        cursor.execute(
                            """
                            DELETE FROM responses
                            WHERE form_id = ?
                            """,
                            (form_id,)
                        )

                        # Delete form
                        cursor.execute(
                            """
                            DELETE FROM forms
                            WHERE id = ?
                            """,
                            (form_id,)
                        )

                        connection.commit()
                        connection.close()

                        st.session_state[
                            f"confirm_delete_{form_id}"
                        ] = False

                        st.success(
                            "🗑️ Form deleted successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Delete failed: {e}"
                        )

            with cancel_col:

                if st.button(
                    "Cancel",
                    key=f"confirm_no_{form_id}",
                    use_container_width=True
                ):

                    st.session_state[
                        f"confirm_delete_{form_id}"
                    ] = False

                    st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


# ============================================================
# RESPONSES
# ============================================================

elif st.session_state.page == "Responses":

    st.markdown(
        '<div class="dashboard-title">Responses</div>',
        unsafe_allow_html=True
    )

    forms = get_all_forms()

    if not forms:

        st.info(
            "No forms available."
        )

    else:

        form_options = {
            f"{form['title']} ({form['id']})":
            form["id"]
            for form in forms
        }

        selected_label = st.selectbox(
            "Select Form",
            list(form_options.keys())
        )

        selected_form_id = (
            form_options[selected_label]
        )

        responses = get_responses_for_form(
            selected_form_id
        )

        if not responses:

            st.info(
                "No responses submitted yet."
            )

        else:

            records = []

            for response in responses:

                data = json.loads(
                    response["response_json"]
                )

                data["Submitted At"] = (
                    response["submitted_at"]
                )

                records.append(data)

            df = pd.DataFrame(
                records
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            csv_data = df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download CSV",
                csv_data,
                file_name="form_responses.csv",
                mime="text/csv"
            )

            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl"
            ) as writer:

                df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Responses"
                )

            st.download_button(
                "⬇️ Download Excel",
                excel_buffer.getvalue(),
                file_name="form_responses.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )

            st.subheader("📄 Individual Response PDF")

            responses = get_responses_for_form(selected_form_id)

            if responses:
                response_options = []

                for index, response in enumerate(responses):
                    response_id = response["id"]
                    submitted_at = response["submitted_at"]

                    response_options.append(
                        f"{index + 1}. {response_id} — {submitted_at}"
                    )

                selected_response_label = st.selectbox(
                    "Select a response",
                    response_options
                )

                selected_index = response_options.index(
                    selected_response_label
                )

                selected_response = responses[selected_index]

                response_data = json.loads(
                    selected_response["response_json"]
                )

                selected_form = get_form(selected_form_id)

                if selected_form:

                    form_schema = FormSchema.model_validate(
                        json.loads(selected_form["schema_json"])
                    )

                    pdf_buffer = generate_response_pdf(
                        form_title=selected_form["title"],
                        form_description=selected_form["description"],
                        response_data=response_data,
                        submitted_at=selected_response["submitted_at"]
                    )

                    st.download_button(
                        label="📄 Download Response as PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=(
                            f"FormFlow_Response_"
                            f"{selected_response['id']}.pdf"
                        ),
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
            else:
                st.info("No responses available for this form yet.")


# ============================================================
# ANALYTICS
# ============================================================

elif st.session_state.page == "Analytics":

    st.title("📊 Analytics Dashboard")
    st.caption(
        "Monitor your forms, responses and submission activity"
    )

    # ---------------------------------------------------------
    # REFRESH BUTTON
    # ---------------------------------------------------------

    col_refresh, col_space = st.columns([1, 5])

    with col_refresh:
        if st.button(
            "🔄 Refresh",
            use_container_width=True
        ):
            st.rerun()

    # ---------------------------------------------------------
    # GET FORM DATA
    # ---------------------------------------------------------

    all_forms = get_all_forms()

    total_forms = len(all_forms)

    published_forms = len([
        form for form in all_forms
        if form["status"] == "Published"
    ])

    total_responses = get_response_count()

    if total_forms > 0:
        average_responses = round(
            total_responses / total_forms,
            1
        )
    else:
        average_responses = 0

    # ---------------------------------------------------------
    # TOP STATISTICS
    # ---------------------------------------------------------

    st.markdown("### 📌 Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "📋 Total Forms",
            total_forms
        )

    with col2:
        st.metric(
            "🟢 Published Forms",
            published_forms
        )

    with col3:
        st.metric(
            "📝 Total Responses",
            total_responses
        )

    with col4:
        st.metric(
            "📊 Avg. Responses / Form",
            average_responses
        )

    st.divider()

    # ---------------------------------------------------------
    # RESPONSES BY FORM
    # ---------------------------------------------------------

    st.markdown("### 📈 Responses by Form")

    if all_forms:

        analytics_data = []

        for form in all_forms:

            response_count = get_form_response_count(
                form["id"]
            )

            analytics_data.append({
                "Form": form["title"],
                "Responses": response_count
            })

        analytics_df = pd.DataFrame(
            analytics_data
        )

        if analytics_df["Responses"].sum() > 0:

            st.bar_chart(
                analytics_df.set_index("Form")
            )

        else:

            st.info(
                "No responses have been submitted yet."
            )

    else:

        st.info(
            "Create your first form to see analytics."
        )

    st.divider()

    # ---------------------------------------------------------
    # FORM-WISE STATISTICS
    # ---------------------------------------------------------

    st.markdown("### 📑 Form-wise Statistics")

    if all_forms:

        statistics_data = []

        for form in all_forms:

            response_count = get_form_response_count(
                form["id"]
            )

            statistics_data.append({
                "Form Name": form["title"],
                "Status": form["status"],
                "Responses": response_count,
                "Created": form["created_at"]
            })

        statistics_df = pd.DataFrame(
            statistics_data
        )

        st.dataframe(
            statistics_df,
            use_container_width=True,
            hide_index=True
        )

    # ---------------------------------------------------------
    # RECENT SUBMISSIONS
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 🕐 Recent Submissions")

    recent_submissions = []

    for form in all_forms:

        responses = get_responses_for_form(
            form["id"]
        )

        for response in responses:

            recent_submissions.append({
                "Form": form["title"],
                "Response ID": response["id"],
                "Submitted At": response["submitted_at"]
            })

    if recent_submissions:

        recent_submissions.sort(
            key=lambda x: x["Submitted At"],
            reverse=True
        )

        recent_submissions = recent_submissions[:10]

        recent_df = pd.DataFrame(
            recent_submissions
        )

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No submissions available yet."
        )

    # ---------------------------------------------------------
    # ANALYTICS SUMMARY
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 💡 Quick Summary")

    if total_forms == 0:

        st.info(
            "No forms have been created yet. "
            "Create a form to start collecting responses."
        )

    elif total_responses == 0:

        st.info(
            f"You currently have {total_forms} form(s), "
            f"but no responses have been submitted yet."
        )

    else:

        st.success(
            f"🎉 Your system has collected "
            f"{total_responses} response(s) "
            f"across {total_forms} form(s)."
        )


# ============================================================
# SETTINGS
# ============================================================

elif st.session_state.page == "Settings":

    st.markdown(
        '<div class="dashboard-title">Settings</div>',
        unsafe_allow_html=True
    )

    st.subheader(
        "⚙️ FormFlow-AI"
    )

    st.write(
        "AI-powered intelligent form digitization "
        "and dynamic form generation."
    )

    st.divider()

    st.subheader(
        "Supported AI Input"
    )

    st.write(
        "• Text requirements"
    )

    st.write(
        "• PDF forms"
    )

    st.write(
        "• PNG/JPG images"
    )

    st.divider()

    st.subheader(
        "Supported Field Types"
    )

    st.write(
        "Text • Textarea • Number • Email • Date • "
        "Select • Radio • Checkbox"
    )