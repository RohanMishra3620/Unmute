import re

SESSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")


class ValidationError(ValueError):
    pass


def validate_session_id(value):
    if not isinstance(value, str) or not SESSION_ID_RE.match(value):
        raise ValidationError("Invalid session_id.")
    return value


def validate_message(value, max_chars=1000):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Message cannot be empty.")
    value = value.strip()
    if len(value) > max_chars:
        raise ValidationError(f"Message must be at most {max_chars} characters.")
    return value
