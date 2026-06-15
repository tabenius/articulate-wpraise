"""Payment routes for Stripe checkout, webhooks, and access validation."""

from __future__ import annotations

import logging
import os

import stripe
from starlette.requests import Request
from starlette.responses import JSONResponse

from articulate_mcp.database import db
from articulate_mcp.email_service import send_access_token_email
from articulate_mcp.product_manager import ProductManager

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
APP_URL = os.getenv("APP_URL", "https://app.ragbaz.cc")


# ---------------------------------------------------------------------------
# POST /payments/checkout
# ---------------------------------------------------------------------------

async def create_checkout_endpoint(request: Request) -> JSONResponse:
    """Create a Stripe Checkout Session for a product."""
    body = await request.json()
    product_id = body.get("product_id")
    if not product_id:
        return JSONResponse({"error": "product_id is required"}, status_code=400)

    product = await ProductManager.get_product(int(product_id))
    if not product:
        return JSONResponse({"error": "Product not found"}, status_code=404)

    if not product.get("is_active"):
        return JSONResponse({"error": "Product is not available"}, status_code=400)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": product.get("currency", "usd"),
                        "unit_amount": product["price_cents"],
                        "product_data": {
                            "name": product["name"],
                            "description": product.get("description") or product["name"],
                        },
                    },
                    "quantity": 1,
                },
            ],
            success_url=f"{APP_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/purchase/cancel",
            metadata={"product_id": str(product["id"])},
        )
    except stripe.StripeError as e:
        logger.error("Stripe checkout error: %s", e)
        return JSONResponse({"error": "Failed to create checkout session"}, status_code=502)

    return JSONResponse({"checkout_url": session.url, "session_id": session.id})


# ---------------------------------------------------------------------------
# POST /payments/webhook
# ---------------------------------------------------------------------------

async def stripe_webhook_endpoint(request: Request) -> JSONResponse:
    """Handle Stripe webhook events with signature verification."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError:
        logger.warning("Stripe webhook: invalid payload")
        return JSONResponse({"error": "Invalid payload"}, status_code=400)
    except stripe.SignatureVerificationError:
        logger.warning("Stripe webhook: invalid signature")
        return JSONResponse({"error": "Invalid signature"}, status_code=400)

    event_id = event["id"]
    event_type = event["type"]

    # Idempotency check
    existing = await db.fetchone(
        "SELECT id FROM articulate_stripe_events WHERE event_id = %s", (event_id,)
    )
    if existing:
        logger.info("Stripe webhook: duplicate event %s, skipping", event_id)
        return JSONResponse({"status": "duplicate"})

    # Record event (not yet processed)
    await db.insert(
        "INSERT INTO articulate_stripe_events (event_id, event_type, processed) VALUES (%s, %s, 0)",
        (event_id, event_type),
    )

    # Dispatch
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            await _handle_checkout_completed(session, event_id)
        except Exception:
            logger.exception("Error handling checkout.session.completed for %s", event_id)
    else:
        logger.info("Stripe webhook: unhandled event type %s", event_type)

    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Internal: handle checkout.session.completed
# ---------------------------------------------------------------------------

async def _handle_checkout_completed(session: dict, event_id: str) -> None:
    """Process a completed checkout session.

    Creates an access grant and sends the access token email.
    """
    metadata = session.get("metadata", {})
    product_id = metadata.get("product_id")
    if not product_id:
        logger.error("checkout.session.completed missing product_id in metadata")
        return

    customer_details = session.get("customer_details", {})
    customer_email = customer_details.get("email") or session.get("customer_email")
    customer_name = customer_details.get("name", "")

    if not customer_email:
        logger.error("checkout.session.completed missing customer email")
        return

    amount_total = session.get("amount_total", 0)
    currency = session.get("currency", "usd")
    payment_intent = session.get("payment_intent")

    grant = await ProductManager.create_access_grant(
        product_id=int(product_id),
        customer_email=customer_email,
        customer_name=customer_name,
        amount_paid=amount_total,
        currency=currency,
        stripe_session_id=session.get("id"),
        stripe_payment_intent_id=payment_intent,
    )

    # Look up product name for the email
    product = await ProductManager.get_product(int(product_id))
    product_name = product["name"] if product else "your purchase"

    send_access_token_email(
        to=customer_email,
        name=customer_name,
        product_name=product_name,
        access_token=grant["access_token"],
    )

    # Mark event as processed
    await db.execute(
        "UPDATE articulate_stripe_events SET processed = 1 WHERE event_id = %s",
        (event_id,),
    )

    logger.info(
        "Checkout completed: product=%s email=%s grant=%d",
        product_id, customer_email, grant["id"],
    )


# ---------------------------------------------------------------------------
# GET /payments/session/{session_id}
# ---------------------------------------------------------------------------

async def check_session_endpoint(request: Request) -> JSONResponse:
    """Check the status of a Stripe Checkout session by looking up the access grant."""
    session_id = request.path_params.get("session_id")
    if not session_id:
        return JSONResponse({"error": "session_id is required"}, status_code=400)

    grant = await db.fetchone(
        """
        SELECT g.access_token, g.customer_email, p.name AS product_name
        FROM articulate_access_grants g
        JOIN articulate_products p ON g.product_id = p.id
        WHERE g.stripe_session_id = %s
        """,
        (session_id,),
    )

    if grant:
        return JSONResponse({
            "status": "completed",
            "access_token": grant["access_token"],
            "product_name": grant["product_name"],
        })

    return JSONResponse({"status": "pending"})


# ---------------------------------------------------------------------------
# POST /payments/validate-token
# ---------------------------------------------------------------------------

async def validate_token_endpoint(request: Request) -> JSONResponse:
    """Validate an access token and return grant details."""
    body = await request.json()
    token = body.get("token")
    if not token:
        return JSONResponse({"error": "token is required"}, status_code=400)

    result = await ProductManager.validate_access_token(token)
    if result:
        return JSONResponse({"valid": True, **result})

    return JSONResponse({"valid": False})


# ---------------------------------------------------------------------------
# GET /payments/products
# ---------------------------------------------------------------------------

async def list_products_public_endpoint(request: Request) -> JSONResponse:
    """List active products with public fields only."""
    products = await ProductManager.list_products(active_only=True)

    public_products = [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "price_cents": p["price_cents"],
            "currency": p.get("currency", "usd"),
        }
        for p in products
    ]

    return JSONResponse({"products": public_products})
