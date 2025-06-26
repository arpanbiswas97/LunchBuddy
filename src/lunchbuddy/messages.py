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

Daily registration requests are sent at {reminder_time} on the day before each lunch day.
"""

STATUS_NOT_ENROLLED = "❌ You are not enrolled for lunch service. Use /enroll to get started!"
STATUS_MESSAGE_TEMPLATE = """
✅ Enrollment Status

Name: {name}
Email: {email}
Dietary Preference: {diet}
Preferred Days: {days}
Enrolled: {enrolled}
"""

# Enrollment
ALREADY_ENROLLED = "❌ You are already enrolled! Use /status to check your details or /unenroll to remove your enrollment."
ENROLLMENT_WELCOME = "🍽️ Welcome to LunchBuddy enrollment!\n\nPlease provide your full name:"
INVALID_NAME = "❌ Please provide a valid full name (at least 2 characters):"
NAME_ACCEPTED_TEMPLATE = "✅ Name: {name}\n\nPlease provide your work email address:"
INVALID_EMAIL = "❌ Please provide a valid email address:"
EMAIL_ACCEPTED_TEMPLATE = "✅ Email: {email}\n\nPlease select your dietary preference:"
DIET_ACCEPTED_TEMPLATE = "✅ Dietary Preference: {diet}\n\nPlease select your preferred lunch days (you can select multiple):"
NO_DAYS_SELECTED = "❌ Please select at least one day for lunch:"

ENROLL_SUCCESS_TEMPLATE = """
🎉 Enrollment successful!

Name: {name}
Email: {email}
Dietary Preference: {diet}
Preferred Days: {days}

You'll receive registration requests at {reminder_time} on the day before each lunch day ({days_list}).
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
🍽️ Do you want lunch for {date}?

Please respond within 30 minutes. If no response is received, you will be automatically registered for lunch.
"""

LUNCH_TIMEOUT_TEMPLATE = """
⏰ No response received within 30 minutes for lunch on {date}.

{status_icon} You have been {status_text} for lunch.
"""

LUNCH_RESPONSE_TEMPLATE = "{status_icon} Your lunch registration for {date} has been {status_text}."

LUNCH_CONFIRMATION_EXPIRED = "This confirmation is no longer active or already recorded."
