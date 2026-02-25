"""
Stripe Webhook endpoint for TuExpertoFiscal

Receives Stripe payment events (checkout.session.completed,
subscription.updated/deleted, invoice.payment_succeeded/failed)
and updates user subscriptions in Supabase.

Run standalone: python -m app.api.stripe_webhook
Or integrate into bot via run_webhook_server()
"""

import os
import logging

import stripe
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TuExpertoFiscal Stripe Webhook",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# Initialized on startup
subscription_service: SubscriptionService | None = None


@app.on_event("startup")
async def startup():
    global subscription_service
    subscription_service = SubscriptionService()
    logger.info("✅ Stripe webhook server started")


@app.get("/")
async def root():
    return {"service": "TuExpertoFiscal Stripe Webhook", "status": "running"}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """
    Receive and process Stripe webhook events.

    Stripe sends POST requests with JSON payload and
    Stripe-Signature header for verification.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    if not subscription_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret or webhook_secret.startswith("whsec_your"):
        # No secret configured — log raw event for debugging, skip verification
        logger.warning("STRIPE_WEBHOOK_SECRET not configured, skipping signature verification")
        try:
            event = stripe.Event.construct_from(
                stripe.util.json.loads(payload), stripe.api_key
            )
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Webhook construction error: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event["type"]
    logger.info(f"📩 Stripe event: {event_type} (id={event['id']})")

    try:
        success = await subscription_service.handle_event(event)
        if success:
            logger.info(f"✅ Processed: {event_type}")
        else:
            logger.warning(f"⚠️ handle_event returned False for {event_type}")
    except Exception as e:
        logger.error(f"❌ Error processing {event_type}: {e}")
        # Return 200 anyway to prevent Stripe retries on our errors
        return JSONResponse(status_code=200, content={"status": "error", "detail": str(e)})

    return JSONResponse(status_code=200, content={"status": "ok"})


async def run_webhook_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Run the webhook server programmatically (for integration with bot).

    Usage in bot's main():
        asyncio.create_task(run_webhook_server(port=8000))
    """
    import uvicorn

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.stripe_webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
