"""Stripe integration for payment processing"""

import stripe
from app.config import settings
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


async def create_checkout_session(
    line_items: List[Dict],
    customer_email: str,
    success_url: str,
    cancel_url: str,
    metadata: Optional[Dict] = None
) -> stripe.checkout.Session:
    """
    Create a Stripe Checkout Session

    Args:
        line_items: List of items with price and quantity
        customer_email: Customer's email address
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
        metadata: Optional metadata to attach to the session

    Returns:
        Stripe Checkout Session object
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        logger.info(f"Created checkout session: {session.id}")
        return session
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise


async def create_payment_intent(
    amount: int,
    currency: str = "usd",
    customer_email: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> stripe.PaymentIntent:
    """
    Create a Stripe Payment Intent

    Args:
        amount: Amount in cents (e.g., 1000 for $10.00)
        currency: Currency code (default: "usd")
        customer_email: Optional customer email
        metadata: Optional metadata to attach to the payment intent

    Returns:
        Stripe PaymentIntent object
    """
    try:
        payment_intent_data = {
            "amount": amount,
            "currency": currency,
            "metadata": metadata or {},
        }

        if customer_email:
            payment_intent_data["receipt_email"] = customer_email

        payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
        logger.info(f"Created payment intent: {payment_intent.id}")
        return payment_intent
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {str(e)}")
        raise


async def retrieve_checkout_session(session_id: str) -> stripe.checkout.Session:
    """
    Retrieve a Stripe Checkout Session

    Args:
        session_id: Stripe session ID

    Returns:
        Stripe Checkout Session object
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving session: {str(e)}")
        raise


async def verify_webhook_signature(payload: bytes, signature: str) -> Dict:
    """
    Verify Stripe webhook signature

    Args:
        payload: Raw request body
        signature: Stripe signature header

    Returns:
        Verified event dictionary
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {str(e)}")
        raise
