# LunchBuddy 🍽️

A Telegram bot for managing lunch enrollments and daily registration requests. LunchBuddy allows users to enroll for lunch service, set their dietary preferences, choose preferred days, and receive daily registration requests about their lunch schedule.

## Features

- **User Enrollment**: Easy enrollment process with interactive conversations
- **Dietary Preferences**: Support for Vegetarian and Non-Vegetarian options
- **Flexible Scheduling**: Choose from configurable lunch days (multi-select)
- **Daily Registration**: Automatic registration requests at configurable time on the day before lunch
- **Timeout Handling**: 30-minute response window with automatic default registration
- **Database Storage**: PostgreSQL backend for persistent data storage
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Commands

- `/start` - Welcome message and introduction
- `/enroll` - Start enrollment process
- `/unenroll` - Remove enrollment
- `/status` - Check current enrollment status
- `/help` - Show help information

## Prerequisites

- Python 3.9+
- PostgreSQL database
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Installation

### Option 1: Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd LunchBuddy
```

2. Copy the environment file:
```bash
cp env.example .env
```

3. Edit `.env` file with your configuration:
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Database Configuration
DATABASE_URL=postgresql://lunchbuddy:lunchbuddy_password@db:5432/lunchbuddy
```

4. Run with Docker Compose:
```bash
docker-compose up -d
```

### Option 2: Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd LunchBuddy
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set up PostgreSQL database and update the `DATABASE_URL` in your environment.

5. Copy and configure the environment file:
```bash
cp env.example .env
# Edit .env with your settings
```

6. Run the application:
```bash
python -m lunchbuddy.main
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Required |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | Required |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://lunchbuddy:lunchbuddy_password@localhost:5432/lunchbuddy` |
| `LUNCH_REMINDER_TIME` | Time for daily registration requests | `12:30` |
| `LUNCH_DAYS` | Available lunch days | `Tuesday,Wednesday,Thursday` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `logs/lunchbuddy.log` |

## Database Schema

### Users Table
- `id`: Primary key
- `telegram_id`: Unique Telegram user ID
- `full_name`: User's full name
- `email`: Work email address
- `dietary_preference`: Veg/Non-Veg preference
- `preferred_days`: Array of preferred lunch days
- `is_enrolled`: Enrollment status
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Lunch Overrides Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `override_date`: Date for override
- `override_choice`: Boolean override choice
- `created_at`: Creation timestamp

## Usage

### Getting Started

1. Create a Telegram bot using [@BotFather](https://t.me/botfather)
2. Get your bot token and add it to the `.env` file
3. Start a conversation with your bot
4. Use `/start` to see available commands
5. Use `/enroll` to begin the enrollment process

### Enrollment Process

The enrollment process collects:
1. **Full Name**: User's complete name
2. **Email**: Work email address
3. **Dietary Preference**: Vegetarian or Non-Vegetarian
4. **Preferred Days**: Multiple selection from available lunch days (configurable)

### Daily Registration Process

- Registration requests are sent automatically at the configured time on the day before each lunch day
- For example: If lunch is on Monday, registration requests are sent on Sunday
- Users have 30 minutes to respond with Yes/No
- If no response is received, users are automatically registered based on their preferred days
- Each request shows:
  - The date for lunch registration
  - Clear timeout information
  - Yes/No buttons for quick response

### Configuration

The lunch days and timing are fully configurable through environment variables:
- `LUNCH_DAYS`: Comma-separated list of available days (e.g., "Monday,Tuesday,Wednesday")
- `LUNCH_REMINDER_TIME`: Time for registration requests (e.g., "12:30")

## Development

### Project Structure

```
LunchBuddy/
├── lunchbuddy/
│   ├── __init__.py
│   ├── main.py          # Application entry point
│   ├── bot.py           # Telegram bot implementation
│   ├── scheduler.py     # Reminder scheduling
│   ├── database.py      # Database operations
│   ├── models.py        # Data models
│   └── config.py        # Configuration management
├── pyproject.toml       # Project dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── env.example         # Environment variables template
└── README.md           # This file
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=lunchbuddy
```

### Code Formatting

```bash
# Format code
black lunchbuddy/

# Lint code
flake8 lunchbuddy/

# Type checking
mypy lunchbuddy/
```

## Deployment

### Docker Deployment

The application is containerized and can be deployed using Docker Compose:

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Production Considerations

1. **Environment Variables**: Use proper environment variable management
2. **Database**: Use a managed PostgreSQL service for production
3. **Logging**: Configure proper log rotation and monitoring
4. **Backup**: Set up regular database backups
5. **Monitoring**: Implement health checks and monitoring
6. **Security**: Use strong passwords and secure connections

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check if the bot token is correct
2. **Database connection errors**: Verify PostgreSQL is running and accessible
3. **Reminders not sent**: Check if the scheduler is running and timezone settings
4. **Permission errors**: Ensure proper file permissions for logs directory

### Logs

Check the application logs for detailed error information:

```bash
# Docker logs
docker-compose logs bot

# Local logs
tail -f logs/lunchbuddy.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please open an issue on the GitHub repository.