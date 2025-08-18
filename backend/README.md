# Conversational Memory Backend

A modular conversational memory system that provides persistent conversation context and user preference learning for AI assistants.

## Features

- **Conversation Context Management**: Maintains context across multiple interactions
- **User Preference Learning**: Adapts to user communication styles and preferences
- **Privacy Controls**: Comprehensive data deletion and export capabilities
- **Search Functionality**: Full-text and semantic search through conversation history
- **Scalable Architecture**: Modular design with clear separation of concerns
- **Data Security**: Encryption at rest and comprehensive audit logging

## Architecture

The system follows a microservice architecture with these core components:

- **Memory Service**: Central orchestrator for all memory operations
- **Context Manager**: Handles conversation context and summarization
- **Preference Engine**: Learns and applies user preferences
- **Search Service**: Provides search capabilities across conversations
- **Privacy Controller**: Enforces data retention and privacy policies
- **Storage Layer**: Abstraction over multiple storage backends

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (for structured data)
- MongoDB (for conversation content)
- Redis (for caching)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

4. Update the `.env` file with your database connections

5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## Configuration

The system is configured through environment variables. See `.env.example` for all available options.

Key configuration options:
- `POSTGRES_URL`: PostgreSQL connection string
- `MONGODB_URL`: MongoDB connection string  
- `REDIS_URL`: Redis connection string
- `ENCRYPTION_KEY`: Key for encrypting sensitive data
- `MAX_CONTEXT_MESSAGES`: Maximum messages to keep in context
- `CONTEXT_RETENTION_DAYS`: How long to retain conversation data

## API Usage

The memory system integrates with your existing chat API. Key endpoints:

- `POST /memory/store` - Store a conversation
- `GET /memory/context/{user_id}` - Retrieve conversation context
- `POST /memory/search` - Search conversation history
- `DELETE /memory/user/{user_id}` - Delete user data

## Development

### Running Tests

```bash
make test
```

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

## Privacy & Security

- All sensitive data is encrypted at rest
- Comprehensive audit logging for data access
- GDPR/CCPA compliant data deletion and export
- Configurable data retention policies
- User-controlled privacy settings

## License

MIT License