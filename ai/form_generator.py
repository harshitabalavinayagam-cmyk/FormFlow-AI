import os
import json
import base64

from dotenv import load_dotenv
from google import genai

from utils.schema import FormSchema


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY not found. "
        "Please check your .env file."
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=API_KEY
)


# ============================================================
# FORM GENERATION PROMPT
# ============================================================

FORM_PROMPT = """
You are FormFlow-AI, an intelligent form digitization assistant.

Your job is to analyze the provided requirement, document,
image, or audio and convert it into a structured digital form.

Understand the actual meaning of the requested form.

Identify:

1. Form title
2. Form description
3. Every relevant input field
4. Appropriate field type
5. Whether the field is required
6. Options for dropdown/radio/checkbox fields
7. Useful placeholder text
8. Helpful field descriptions

Allowed field types:

text
textarea
number
email
date
select
radio
checkbox

Important:

- Preserve the meaning of the original requirement.
- Do not invent unnecessary fields.
- Convert blank lines into appropriate input fields.
- Convert checkboxes into checkbox/select/radio fields as appropriate.
- Convert multiple-choice options into select or radio fields.
- Use clear machine-readable field names.
- For audio input, first understand what the speaker is requesting.
- Ignore unrelated background speech or noise.
- Return ONLY valid JSON.
- Do NOT use markdown.
- Do NOT use ```json.
- Do NOT include explanations.

Use exactly this structure:

{
    "title": "Form title",
    "description": "Short description",
    "fields": [
        {
            "name": "field_name",
            "label": "Field Label",
            "type": "text",
            "required": true,
            "options": null,
            "placeholder": "",
            "help_text": ""
        }
    ]
}
"""


# ============================================================
# CLEAN GEMINI RESPONSE
# ============================================================

def clean_json_response(response_text: str):

    response_text = response_text.strip()

    if response_text.startswith("```"):

        response_text = response_text.replace(
            "```json",
            ""
        )

        response_text = response_text.replace(
            "```",
            ""
        )

        response_text = response_text.strip()

    return response_text


# ============================================================
# VALIDATE FORM
# ============================================================

def validate_form(response_text: str):

    response_text = clean_json_response(
        response_text
    )

    data = json.loads(
        response_text
    )

    validated_form = FormSchema.model_validate(
        data
    )

    return validated_form


# ============================================================
# GENERATE FORM FROM TEXT
# ============================================================

def generate_form(requirement: str):

    prompt = f"""
{FORM_PROMPT}

USER REQUIREMENT:

{requirement}
"""

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[
            {
                "type": "text",
                "text": prompt
            }
        ]
    )

    return validate_form(
        interaction.output_text
    )


# ============================================================
# GENERATE FORM FROM PDF / IMAGE
# ============================================================

def generate_form_from_file(
    file_bytes,
    mime_type
):

    encoded_file = base64.b64encode(
        file_bytes
    ).decode("utf-8")

    if mime_type == "application/pdf":

        file_content = {
            "type": "document",
            "data": encoded_file,
            "mime_type": "application/pdf"
        }

    elif mime_type in [
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp"
    ]:

        file_content = {
            "type": "image",
            "data": encoded_file,
            "mime_type": mime_type
        }

    else:

        raise ValueError(
            "Unsupported file type. "
            "Please upload PDF, PNG, JPG or JPEG."
        )

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[
            {
                "type": "text",
                "text": FORM_PROMPT
            },
            file_content
        ]
    )

    return validate_form(
        interaction.output_text
    )


# ============================================================
# GENERATE FORM FROM VOICE
# ============================================================

def generate_form_from_audio(
    audio_bytes,
    mime_type
):

    encoded_audio = base64.b64encode(
        audio_bytes
    ).decode("utf-8")

    # Gemini supports several audio MIME types.
    # Streamlit may return formats such as audio/wav,
    # audio/webm, audio/mpeg, etc.

    supported_audio_types = [
        "audio/wav",
        "audio/mp3",
        "audio/mpeg",
        "audio/aac",
        "audio/ogg",
        "audio/flac",
        "audio/m4a",
        "audio/webm",
        "audio/aiff",
        "audio/opus"
    ]

    if mime_type not in supported_audio_types:

        # Some browsers may return an audio type
        # with additional parameters.
        mime_type = mime_type.split(";")[0]

    if mime_type not in supported_audio_types:

        raise ValueError(
            f"Unsupported audio format: {mime_type}"
        )

    audio_content = {
        "type": "audio",
        "data": encoded_audio,
        "mime_type": mime_type
    }

    voice_prompt = f"""
{FORM_PROMPT}

The following audio contains the administrator's
spoken requirement for a digital form.

Understand the speech and convert the spoken requirement
into the requested digital form.

Do not create fields for words that are unrelated to
the form requirement.
"""

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[
            {
                "type": "text",
                "text": voice_prompt
            },
            audio_content
        ]
    )

    return validate_form(
        interaction.output_text
    )
def modify_form(requirement: str, current_form: FormSchema):
    """
    Modify an existing form using a natural-language instruction.
    """

    current_form_json = current_form.model_dump_json(
        indent=2
    )

    modification_prompt = f"""
You are FormFlow-AI, an intelligent form modification assistant.

You are given an existing digital form and an administrator's
natural-language modification request.

Your task is to modify the existing form according to the
administrator's request.

IMPORTANT RULES:

1. Preserve all existing fields unless the administrator
   explicitly asks to remove or change them.

2. Add new fields when requested.

3. Remove fields only when explicitly requested.

4. Change field types when requested.

5. Change required status when requested.

6. Add or modify dropdown/radio options when requested.

7. Keep field names machine-readable using snake_case.

8. Do not invent unrelated fields.

9. Preserve the existing form title unless the administrator
   asks to change it.

10. Return ONLY valid JSON.

11. Do NOT use markdown.

12. Do NOT use ```json.

Allowed field types:

text
textarea
number
email
date
select
radio
checkbox

Use exactly this structure:

{{
    "title": "Form title",
    "description": "Short description",
    "fields": [
        {{
            "name": "field_name",
            "label": "Field Label",
            "type": "text",
            "required": true,
            "options": null,
            "placeholder": "",
            "help_text": ""
        }}
    ]
}}

EXISTING FORM:

{current_form_json}

ADMINISTRATOR'S MODIFICATION:

{requirement}
"""

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[
            {
                "type": "text",
                "text": modification_prompt
            }
        ]
    )

    return validate_form(
        interaction.output_text
    )