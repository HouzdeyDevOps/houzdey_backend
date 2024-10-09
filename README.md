# Houzdey Backend

## 🏠 About Houzdey

Houzdey is an innovative rental property platform that connects tenants with landlords and simplifies the property management process. This repository contains the backend code that powers the Houzdey application.

## 🚀 Features

- **RESTful API**: Robust endpoints for property management, user interactions, and more
- **Real-time Messaging**: Integration with Stream Chat API for instant communication
- **Payment Processing**: Secure transactions using Paystack
- **Authentication**: User authentication and authorization with Auth0
- **Database Management**: Efficient data storage and retrieval with MongoDB
- **Scalable Architecture**: Designed to handle growth and high concurrent users

## 🛠 Tech Stack

- **FastAPI**: High-performance Python web framework for building APIs
- **MongoDB**: NoSQL database for flexible and scalable data storage
- **Pydantic**: Data validation and settings management using Python type annotations
- **Auth0**: For secure user authentication and authorization
- **Stream Chat API**: For real-time messaging functionality
- **Paystack API**: For secure payment processing
- **Google Maps API**: For location-based services
- **Poetry**: For dependency management and packaging

## 🏗 Getting Started

### Prerequisites

- Python 3.8+
- Poetry
- MongoDB

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/houzdey/backend.git
   cd backend
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add the following:
   ```
   MONGODB_URI=<your_mongodb_uri>
   AUTH0_DOMAIN=<your_auth0_domain>
   AUTH0_API_AUDIENCE=<your_auth0_api_audience>
   STREAM_API_KEY=<your_stream_chat_api_key>
   STREAM_API_SECRET=<your_stream_chat_api_secret>
   PAYSTACK_SECRET_KEY=<your_paystack_secret_key>
   GOOGLE_MAPS_API_KEY=<your_google_maps_api_key>
   ```

4. Activate the virtual environment:
   ```
   poetry shell
   ```

5. Start the FastAPI server:
   ```
   uvicorn app.main:app --reload
   ```

6. The API will be available at `http://localhost:8000`. You can access the interactive API documentation at `http://localhost:8000/docs`.

## 🧪 Testing

Run the test suite with:

```
poetry run pytest
```

## 🚢 Deployment

1. Choose a cloud platform (e.g., AWS, Render, or DigitalOcean).
2. Set up a MongoDB instance (e.g., MongoDB Atlas).
3. Configure environment variables on your chosen platform.
4. Ensure Poetry is installed on your deployment environment.
5. Use Poetry to install dependencies:
   ```
   poetry install --no-dev
   ```
6. Deploy the FastAPI application using platform-specific instructions.

## 🌐 API Documentation

Once the server is running, you can access the interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🤝 Contributing

We welcome contributions to the Houzdey backend! Please read our [Contributing Guidelines](CONTRIBUTING.md) for more information on how to get started.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you encounter any issues or have questions, please file an issue on our [GitHub issue tracker](https://github.com/houzdey/backend/issues) or contact our support team at support@houzdey.com.

---

Built with ❤️ by the Houzdey Team