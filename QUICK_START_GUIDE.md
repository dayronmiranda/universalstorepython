# Quick Start Guide: New Admin Endpoints

## Prerequisites
- Admin JWT token (obtain through `/api/auth/magic-link` with admin user)
- MongoDB running and connected
- FastAPI server running

## Getting Started

### 1. Start the Server
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### 2. View API Documentation
Open in browser: http://localhost:8000/docs

## Common Workflows

### Workflow 1: Initial Store Setup

#### Step 1: Configure Basic Store Information
```bash
curl -X PUT http://localhost:8000/api/admin/store/config \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Awesome Store",
    "tagline": "Quality products delivered fast",
    "description": "Your one-stop shop for everything",
    "domain": "mystore.com",
    "frontendUrl": "https://mystore.com"
  }'
```

#### Step 2: Configure Branding
```bash
curl -X PUT http://localhost:8000/api/admin/store/config/branding \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "logo": "https://mystore.com/logo.png",
    "primaryColor": "#FF6B35",
    "secondaryColor": "#004E89"
  }'
```

#### Step 3: Configure Contact Information
```bash
curl -X PUT http://localhost:8000/api/admin/store/config/contact \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "contact@mystore.com",
    "phone": "+1-555-0123",
    "address": "123 Main Street",
    "city": "New York",
    "country": "USA"
  }'
```

#### Step 4: Configure Locale/Currency
```bash
curl -X PUT http://localhost:8000/api/admin/store/config/locale \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "country": "United States",
    "countryCode": "US",
    "currency": "USD",
    "currencySymbol": "$",
    "timezone": "America/New_York",
    "locale": "en-US"
  }'
```

### Workflow 2: Setting Up Email

#### Step 1: Configure SMTP Settings
```bash
curl -X PUT http://localhost:8000/api/admin/store/config/smtp \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "smtp.gmail.com",
    "port": 587,
    "secure": false,
    "auth": {
      "user": "your-email@gmail.com",
      "pass_": "your-app-password"
    },
    "enabled": true
  }'
```

#### Step 2: Test SMTP Connection
```bash
curl -X POST http://localhost:8000/api/admin/store/config/smtp/test \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "smtp.gmail.com",
    "port": 587,
    "secure": false,
    "user": "your-email@gmail.com",
    "pass_": "your-app-password"
  }'
```

#### Step 3: Send Test Email
```bash
curl -X POST http://localhost:8000/api/admin/store/config/smtp/send-test \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "test@example.com",
    "use_saved_config": true
  }'
```

### Workflow 3: Managing Pickup Locations

#### Step 1: Create Pickup Location
```bash
curl -X POST http://localhost:8000/api/admin/store/pickup-locations \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown Store",
    "address": "123 Main Street",
    "city": "New York",
    "country": "USA",
    "phone": "+1-555-0100",
    "estimatedCapacity": 50,
    "isActive": true,
    "isDefault": true,
    "operatingHours": {
      "monday": { "open": "09:00", "close": "18:00", "closed": false },
      "tuesday": { "open": "09:00", "close": "18:00", "closed": false },
      "wednesday": { "open": "09:00", "close": "18:00", "closed": false },
      "thursday": { "open": "09:00", "close": "18:00", "closed": false },
      "friday": { "open": "09:00", "close": "18:00", "closed": false },
      "saturday": { "open": "10:00", "close": "16:00", "closed": false },
      "sunday": { "closed": true }
    }
  }'
```

#### Step 2: List All Pickup Locations
```bash
curl -X GET http://localhost:8000/api/admin/store/pickup-locations?page=1&limit=20 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Step 3: Toggle Location Active Status
```bash
curl -X POST http://localhost:8000/api/admin/store/pickup-locations/{LOCATION_ID}/toggle \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Step 4: Reorder Locations
```bash
curl -X POST http://localhost:8000/api/admin/store/pickup-locations/reorder \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order": [
      { "id": "LOCATION_ID_1", "sortOrder": 1 },
      { "id": "LOCATION_ID_2", "sortOrder": 2 },
      { "id": "LOCATION_ID_3", "sortOrder": 3 }
    ]
  }'
```

### Workflow 4: Managing Email Templates

#### Step 1: Get Available Template Variables
```bash
curl -X GET http://localhost:8000/api/admin/store/email-templates/variables \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Step 2: Create Custom Order Confirmation Template
```bash
curl -X POST http://localhost:8000/api/admin/store/email-templates \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "order_confirmation",
    "name": "Custom Order Confirmation",
    "subject": "Your Order {{orderNumber}} is Confirmed!",
    "htmlBody": "<html><body><h1>Thank you, {{userName}}!</h1><p>Your order {{orderNumber}} totaling {{orderTotal}} has been confirmed.</p><p><a href=\"{{orderUrl}}\">View Order</a></p></body></html>",
    "textBody": "Thank you, {{userName}}! Your order {{orderNumber}} totaling {{orderTotal}} has been confirmed. View order: {{orderUrl}}",
    "isActive": true
  }'
```

#### Step 3: Preview Template with Sample Data
```bash
curl -X POST http://localhost:8000/api/admin/store/email-templates/{TEMPLATE_ID}/preview \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "previewData": {
      "{{userName}}": "John Doe",
      "{{orderNumber}}": "ORD-12345",
      "{{orderTotal}}": "$99.99",
      "{{orderUrl}}": "https://mystore.com/orders/12345"
    }
  }'
```

#### Step 4: Send Test Email
```bash
curl -X POST http://localhost:8000/api/admin/store/email-templates/test \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "TEMPLATE_ID",
    "to_email": "test@example.com",
    "preview_data": {
      "{{userName}}": "Test User",
      "{{orderNumber}}": "TEST-001",
      "{{orderTotal}}": "$50.00",
      "{{orderUrl}}": "https://mystore.com/orders/test"
    }
  }'
```

#### Step 5: Reset Template to Default
```bash
curl -X POST http://localhost:8000/api/admin/store/email-templates/by-type/order_confirmation/reset \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Useful Queries

### Get Full Store Configuration
```bash
curl -X GET http://localhost:8000/api/admin/store/config \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Get Only SMTP Configuration
```bash
curl -X GET http://localhost:8000/api/admin/store/config/smtp \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### List Active Email Templates
```bash
curl -X GET "http://localhost:8000/api/admin/store/email-templates?active=true" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Get Active Template by Type
```bash
curl -X GET http://localhost:8000/api/admin/store/email-templates/by-type/magic_link \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### List Only Active Pickup Locations
```bash
curl -X GET "http://localhost:8000/api/admin/store/pickup-locations?active=true" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Response Format

All endpoints return responses in this format:

### Success Response
```json
{
  "success": true,
  "message": "Optional success message",
  "data": {
    // Response data here
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error Type",
  "detail": "Detailed error message"
}
```

## HTTP Status Codes

- `200 OK` - Successful GET/PUT request
- `201 Created` - Successful POST (creation)
- `400 Bad Request` - Invalid input data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Not authorized (not admin)
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Tips & Best Practices

### Store Configuration
1. Always get current config before updating to avoid overwriting
2. Use nested endpoints (e.g., `/config/branding`) for partial updates
3. Test SMTP before enabling it in production
4. Keep backup of working SMTP credentials

### Pickup Locations
1. Always have at least one active location
2. Set one location as default
3. Use descriptive slugs for URLs
4. Include operating hours for better UX
5. Keep sortOrder sequential (1, 2, 3, ...)

### Email Templates
1. Always preview templates before activating
2. Test templates with real data before production use
3. Only one template of each type can be active
4. Default templates can't be deleted (only deactivated)
5. Use variables consistently across templates

## Troubleshooting

### SMTP Connection Fails
- Check firewall rules
- Verify SMTP credentials
- Try with TLS/SSL settings
- Check port (587 for TLS, 465 for SSL)
- Enable "Less secure apps" for Gmail

### Template Variables Not Replacing
- Ensure variable names match exactly (case-sensitive)
- Include curly braces: `{{variableName}}`
- Check preview_data format in requests

### Pickup Location Reorder Not Working
- Ensure all IDs are valid MongoDB ObjectIds
- Provide sortOrder for all locations being reordered
- Check that locations exist before reordering

## Additional Resources

- Full API Documentation: http://localhost:8000/docs
- ReDoc Documentation: http://localhost:8000/redoc
- OpenAPI Specification: http://localhost:8000/openapi.json
- Implementation Summary: See IMPLEMENTATION_SUMMARY.md

## Support

For issues or questions:
1. Check the API documentation at /docs
2. Review error messages in responses
3. Check server logs for detailed errors
4. Verify admin authentication token is valid

---

**Happy configuring!** 🚀
