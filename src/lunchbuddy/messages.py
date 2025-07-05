# General Commands
WELCOME_MESSAGE = """
🍽️ Welcome to LunchBuddy! 🍽️

I'm here to help you manage your lunch enrollments.

Available commands:
• /enroll - Enroll for lunch service (collects your preferences)
• /unenroll - Unenroll from lunch service
• /status - Check your current enrollment status
• /help - Show this help message

Let's get started! Use /enroll to begin your enrollment.
"""

HELP_MESSAGE_TEMPLATE = """
🍽️ LunchBuddy Help 🍽️

Commands:
• /enroll - Enroll for lunch service (collects your preferences)
• /unenroll - Unenroll from lunch service
• /status - Check your current enrollment status
• /help - Show this help message

Lunch is available on:
• {days}

You can choose multiple days and set dietary preferences (Veg/Non-Veg).

Daily registration requests are sent at {reminder_time} (UTC) on the day before each lunch day.
"""

STATUS_NOT_ENROLLED = (
    "❌ You are not enrolled for lunch service. Use /enroll to get started!"
)
STATUS_MESSAGE_TEMPLATE = """
✅ Enrollment Status

Name: {name}
Email: {email}
Dietary Preference: {diet}
Preferred Days: {days}
Enrolled: {enrolled}
Verified: {verified}
"""

# Enrollment
ENROLLMENT_WELCOME = (
    "🍽️ Welcome to LunchBuddy enrollment!\n\nPlease provide your full name:"
)
INVALID_NAME = "❌ Please provide a valid full name (at least 2 characters):"
NAME_ACCEPTED_TEMPLATE = "✅ Name: {name}\n\nPlease provide your work email address:"
INVALID_EMAIL = "❌ Please provide a valid email address:"
EMAIL_ACCEPTED_TEMPLATE = "✅ Email: {email}\n\nPlease select your dietary preference:"
DIET_ACCEPTED_TEMPLATE = "✅ Dietary Preference: {diet}\n\nPlease select your preferred lunch days (you can select multiple):"
NO_DAYS_SELECTED = "❌ Please select at least one day for lunch:"

ENROLL_SUCCESS_TEMPLATE = """
🎉 Enrollment details submitted!

Name: {name}
Email: {email}
Dietary Preference: {diet}
Preferred Days: {days}

Note: Your enrollment will be reviewed and confirmed internally before activation.
"""

ENROLL_FAILED = "❌ Failed to complete enrollment. Please try again later, or contact support if the issue continues."
SELECTED_DAYS_TEMPLATE = """
✅ Dietary Preference: {diet}

Selected Days: {selected}

Please select your preferred lunch days (you can select multiple):
"""

ENROLLMENT_CANCELLED = "❌ Enrollment cancelled."

# Unenroll
UNENROLL_SUCCESS = "✅ You have been successfully unenrolled from the lunch service.\n\nYou can re-enroll anytime using /enroll."
UNENROLL_FAILURE = "❌ You are not currently enrolled for lunch service."

# Lunch Confirmation
LUNCH_CONFIRMATION_TEMPLATE = """
🍽️ Do you want lunch for tomorrow??
"""

LUNCH_CONFIRMATION_YES = (
    "Thanks for confirming! Lunch will be arranged for you tomorrow. 🍽️"
)

LUNCH_CONFIRMATION_NO = "No worries! Lunch will not be arranged for you tomorrow."


LUNCH_TIMEOUT_OPT_IN = """
⏰ No response received within 30 minutes.
Your lunch will be automatically arranged for you tomorrow as per your preferences.
"""

LUNCH_TIMEOUT_OPT_OUT = """
⏰ No response received within 30 minutes.
Your lunch will not be arranged for you tomorrow as per your preferences.
"""

LUNCH_CONFIRMATION_EXPIRED = (
    "This confirmation is no longer active or already recorded."
)

ENROLL_VERIFICATION_REQUEST_TEMPLATE = """
🔍 New enrollment pending verification:

Telegram ID: {telegram_id}
Name: {name}
Email: {email}
Dietary Preference: {diet}
Preferred Days: {days}

Please review and verify this enrollment.
"""

ENROLL_APPROVED = "✅ Enrollment approved for Telegram ID {telegram_id}."
ENROLL_REJECTED = "❌ Enrollment rejected for Telegram ID {telegram_id}."

VERIFY_SUCCESS = "✅ You're all set! Your enrollment has been verified and activated."
VERIFY_FAIL = "❌ Your enrollment was not approved. Please contact support if you have questions."
