# JollyTienda API - Python/FastAPI

Complete e-commerce API built with FastAPI, MongoDB, and Stripe.

## Features

- **Passwordless Authentication**: Magic link authentication with JWT tokens
- **Product Management**: Full CRUD for products and categories
- **Shopping Cart**: Cart management with automatic stock reservations
- **Order Processing**: Complete order lifecycle management
- **Stripe Payments**: Integrated payment processing with Stripe Checkout
- **Admin Panel**: User and customer management
- **Async/Await**: Fully asynchronous for high performance
- **OpenAPI Docs**: Auto-generated API documentation

## Tech Stack

- **FastAPI**: Modern async web framework
- **Motor**: Async MongoDB driver
- **Pydantic v2**: Data validation and serialization
- **Stripe**: Payment processing
- **JWT**: Token-based authentication
- **SMTP**: Email delivery for magic links

## Project Structure

```
app/
├── api/
│   ├── deps.py              # Authentication dependencies
│   └── v1/
│       ├── auth.py          # Authentication endpoints
│       ├── users.py         # Admin user management
│       ├── products.py      # Product CRUD
│       ├── orders.py        # Orders and carts
│       └── payments.py      # Stripe integration
├── core/
│   ├── security.py          # JWT and magic links
│   ├── email.py             # Email service
│   └── stripe_client.py     # Stripe integration
├── models/                  # Pydantic models
├── schemas/                 # Request/response schemas
├── utils/                   # Utilities
├── config.py                # Settings
├── database.py              # MongoDB connection
└── main.py                  # FastAPI application
```

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- Stripe account
- SMTP server (Gmail, SendGrid, etc.)

### Installation

1. **Clone the repository**:
   ```bash
   cd /root/universalstorepython
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Configure MongoDB**:
   - Install MongoDB locally or use MongoDB Atlas
   - Update `MONGODB_URL` in `.env`

6. **Configure Stripe**:
   - Get API keys from [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
   - Update `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in `.env`

7. **Configure Email**:
   - Set up SMTP credentials in `.env`
   - For Gmail: Enable 2FA and create an App Password

### Running the Application

**Development mode** (with auto-reload):
```bash
uvicorn app.main:app --reload
```

**Production mode**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/magic-link` - Request magic link
- `POST /api/auth/verify` - Verify magic link and get JWT
- `GET /api/auth/me` - Get current user profile
- `PUT /api/auth/profile` - Update profile
- `POST /api/auth/logout` - Logout

### Products
- `GET /api/products` - List products (public)
- `GET /api/products/search` - Search products
- `GET /api/products/{id}` - Get product
- `POST /api/products` - Create product (admin)
- `PUT /api/products/{id}` - Update product (admin)
- `DELETE /api/products/{id}` - Delete product (admin)

### Categories
- `GET /api/categories` - List categories
- `POST /api/categories` - Create category (admin)

### Orders & Carts
- `GET /api/carts` - Get or create cart
- `POST /api/carts` - Create cart with items
- `PUT /api/carts/{id}` - Update cart
- `DELETE /api/carts/{id}` - Clear cart
- `GET /api/orders` - List user orders
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Get order
- `POST /api/orders/{id}/cancel` - Cancel order

### Payments
- `POST /api/payments/checkout` - Create Stripe checkout
- `GET /api/payments/checkout/{id}` - Get checkout session
- `POST /api/payments/intent` - Create payment intent
- `POST /api/payments/verify` - Verify payment

### Admin - Users
- `GET /api/admin/users` - List admin users
- `POST /api/admin/users` - Create admin user
- `GET /api/admin/users/{id}` - Get admin user
- `PUT /api/admin/users/{id}` - Update admin user
- `DELETE /api/admin/users/{id}` - Delete admin user
- `GET /api/admin/customers` - List customers
- `GET /api/admin/customers/{id}` - Get customer

## Authentication Flow

1. **Request Magic Link**:
   ```bash
   curl -X POST http://localhost:8000/api/auth/magic-link \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com"}'
   ```

2. **Check Email**: User receives email with magic link

3. **Verify Magic Link**:
   ```bash
   curl -X POST http://localhost:8000/api/auth/verify \
     -H "Content-Type: application/json" \
     -d '{"token": "TOKEN_FROM_EMAIL"}'
   ```

4. **Use JWT Token**: Include in Authorization header for protected endpoints:
   ```bash
   curl http://localhost:8000/api/auth/me \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

## Stock Management

The API implements automatic stock reservation:

1. **Cart Creation**: Stock is reserved when items are added to cart
2. **Reservation Duration**: Reserved for 15 minutes (configurable)
3. **Order Creation**: Reserved stock is converted to actual stock reduction
4. **Order Cancellation**: Stock is restored when order is cancelled

## Development

### Testing the API

Use the interactive Swagger UI at http://localhost:8000/docs

### Database Indexes

Recommended MongoDB indexes for production:

```javascript
// Users
db.users.createIndex({ email: 1 }, { unique: true })
db.users.createIndex({ role: 1 })

// Products
db.products.createIndex({ active: 1, featured: 1 })
db.products.createIndex({ category: 1 })
db.products.createIndex({ name: "text", description: "text" })

// Orders
db.orders.createIndex({ user_id: 1, created_at: -1 })
db.orders.createIndex({ order_number: 1 }, { unique: true })
db.orders.createIndex({ status: 1 })

// Carts
db.carts.createIndex({ user_id: 1 })
db.carts.createIndex({ reserved_until: 1 })

// Magic Links
db.magic_links.createIndex({ token: 1 }, { unique: true })
db.magic_links.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 })
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `MONGODB_URL`: MongoDB connection string
- `JWT_SECRET`: Secret key for JWT tokens (generate with: `openssl rand -hex 32`)
- `STRIPE_SECRET_KEY`: Stripe API secret key
- `SMTP_*`: Email server configuration

## Security Notes

- Always use HTTPS in production
- Change `JWT_SECRET` to a strong random value
- Configure CORS `allow_origins` for your frontend domain
- Use environment variables for all secrets
- Enable MongoDB authentication in production
- Use Stripe webhook signing to verify webhook events

## License

MIT License

## Support

For issues and questions, please open a GitHub issue.
