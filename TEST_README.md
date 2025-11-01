# Testing Guide for AI Astrologer API

This guide explains how to run tests for the user creation functionality in the AI Astrologer API.

## Quick Start

### Install Dependencies
```bash
# Install test dependencies
python run_tests.py install

# Or manually with pipenv
pipenv install --dev
```

### Run Tests
```bash
# Run all tests
python run_tests.py all

# Run only user creation tests
python run_tests.py user

# Run with coverage report
python run_tests.py coverage
```

## Test Structure

### Test Files
- `tests/test_user_creation.py` - Comprehensive user creation tests
- `tests/usertests.py` - Legacy user tests (backward compatibility)
- `tests/conftest.py` - Test configuration and fixtures

### Test Categories

#### 1. UserService Tests (`TestUserServiceCreation`)
- ✅ Successful user creation
- ✅ User creation with minimal data
- ✅ Duplicate user handling
- ✅ Database error handling
- ✅ Multiple user creation

#### 2. Schema Validation Tests (`TestUserSchemaValidation`)
- ✅ Valid UserCreate schema
- ✅ Minimal UserCreate schema
- ✅ Invalid email validation
- ✅ UserResponse schema creation

#### 3. API Endpoint Tests (`TestUserAPICreation`)
- ✅ `/users/sync` endpoint for new users
- ✅ `/users/sync` endpoint for existing users
- ✅ Unauthorized access handling
- ✅ Invalid Firebase data handling

#### 4. Edge Case Tests (`TestUserCreationEdgeCases`)
- ✅ Special characters in user data
- ✅ Very long strings
- ✅ Empty strings
- ✅ None values
- ✅ Case sensitivity

#### 5. Integration Tests (`TestUserCreationIntegration`)
- ✅ Full user creation flow
- ✅ User creation with subsequent updates
- ✅ Multiple users creation isolation

## Available Commands

| Command | Description |
|---------|-------------|
| `python run_tests.py all` | Run all tests |
| `python run_tests.py user` | Run user creation tests only |
| `python run_tests.py legacy` | Run legacy tests only |
| `python run_tests.py unit` | Run unit tests only |
| `python run_tests.py integration` | Run integration tests only |
| `python run_tests.py coverage` | Run tests with coverage report |
| `python run_tests.py install` | Install test dependencies |
| `python run_tests.py info` | Show test information |

## Manual Test Execution

### Using pytest directly
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_user_creation.py -v

# Run specific test class
pytest tests/test_user_creation.py::TestUserServiceCreation -v

# Run specific test method
pytest tests/test_user_creation.py::TestUserServiceCreation::test_create_user_success -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Using pipenv
```bash
# Run tests with pipenv
pipenv run pytest tests/ -v

# Install dependencies and run
pipenv install --dev
pipenv run pytest tests/test_user_creation.py -v
```

## Test Configuration

### Database
- Tests use in-memory SQLite database (`sqlite+aiosqlite:///:memory:`)
- Each test gets a fresh database session
- No external database required for testing

### Fixtures
- `test_db_session` - Async database session
- `client` - FastAPI test client
- `mock_firebase_user` - Mock Firebase user data
- `sample_user_data` - Sample UserCreate data
- `user_service` - UserService instance

### Mocking
- Firebase authentication is mocked
- Database operations use real async SQLModel
- External services are mocked as needed

## Test Coverage

The tests cover:
- ✅ User model creation and validation
- ✅ UserService business logic
- ✅ API endpoint functionality
- ✅ Schema validation
- ✅ Error handling and edge cases
- ✅ Integration flows
- ✅ Authentication and authorization

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure you're in the project root
   cd /path/to/Ai-Astrologer-Api
   
   # Install dependencies
   python run_tests.py install
   ```

2. **Database Connection Issues**
   - Tests use in-memory SQLite, no external DB needed
   - Check that all models are properly imported

3. **Async Test Issues**
   - Tests are configured with `pytest-asyncio`
   - Make sure `@pytest.mark.asyncio` decorators are present

4. **Firebase Mock Issues**
   - Firebase authentication is mocked in tests
   - Check mock configurations in test fixtures

### Debug Mode
```bash
# Run tests with detailed output
pytest tests/ -v -s --tb=long

# Run single test with debug
pytest tests/test_user_creation.py::test_create_user_success -v -s
```

## Contributing

When adding new tests:
1. Follow the existing test structure
2. Use appropriate fixtures from `conftest.py`
3. Add proper docstrings and assertions
4. Include both positive and negative test cases
5. Update this README if adding new test categories
