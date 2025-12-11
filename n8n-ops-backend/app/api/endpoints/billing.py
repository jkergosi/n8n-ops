from fastapi import APIRouter, HTTPException, status, Request
from typing import List
from datetime import datetime

from app.schemas.billing import (
    SubscriptionPlanResponse,
    SubscriptionResponse,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PortalSessionResponse,
    PaymentHistoryResponse,
    InvoiceResponse,
    UpcomingInvoiceResponse
)
from app.services.database import db_service
from app.services.stripe_service import stripe_service

router = APIRouter()

# TODO: Replace with actual tenant ID from authenticated user
MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000000"


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        response = db_service.client.table("subscription_plans").select("*").eq("is_active", True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch subscription plans: {str(e)}"
        )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_current_subscription():
    """Get current subscription for tenant"""
    try:
        # Get subscription with plan details
        response = db_service.client.table("subscriptions").select(
            "*, plan:plan_id(*)"
        ).eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )

        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch subscription: {str(e)}"
        )


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(checkout: CheckoutSessionCreate):
    """Create a Stripe checkout session for subscription"""
    try:
        # Get tenant info
        tenant_response = db_service.client.table("tenants").select("*").eq("id", MOCK_TENANT_ID).single().execute()
        tenant = tenant_response.data

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Check if tenant has existing subscription
        sub_response = db_service.client.table("subscriptions").select("*").eq("tenant_id", MOCK_TENANT_ID).execute()

        customer_id = None
        if sub_response.data and len(sub_response.data) > 0:
            customer_id = sub_response.data[0].get("stripe_customer_id")

        # Create Stripe customer if not exists
        if not customer_id:
            customer = await stripe_service.create_customer(
                email=tenant.get("email"),
                name=tenant.get("name"),
                tenant_id=MOCK_TENANT_ID
            )
            customer_id = customer["id"]

        # Create checkout session
        session = await stripe_service.create_checkout_session(
            customer_id=customer_id,
            price_id=checkout.price_id,
            success_url=checkout.success_url,
            cancel_url=checkout.cancel_url,
            tenant_id=MOCK_TENANT_ID,
            billing_cycle=checkout.billing_cycle
        )

        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(return_url: str):
    """Create a Stripe customer portal session"""
    try:
        # Get subscription with customer ID
        response = db_service.client.table("subscriptions").select("stripe_customer_id").eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data or not response.data.get("stripe_customer_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        customer_id = response.data["stripe_customer_id"]

        # Create portal session
        session = await stripe_service.create_portal_session(
            customer_id=customer_id,
            return_url=return_url
        )

        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portal session: {str(e)}"
        )


@router.post("/cancel")
async def cancel_subscription(at_period_end: bool = True):
    """Cancel current subscription"""
    try:
        # Get subscription
        response = db_service.client.table("subscriptions").select("*").eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data or not response.data.get("stripe_subscription_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        subscription_id = response.data["stripe_subscription_id"]

        # Cancel in Stripe
        result = await stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=at_period_end
        )

        # Update database
        db_service.client.table("subscriptions").update({
            "cancel_at_period_end": result["cancel_at_period_end"],
            "canceled_at": datetime.fromtimestamp(result["canceled_at"]).isoformat() if result.get("canceled_at") else None,
            "status": result["status"]
        }).eq("tenant_id", MOCK_TENANT_ID).execute()

        return {"message": "Subscription canceled successfully", "cancel_at_period_end": at_period_end}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/reactivate")
async def reactivate_subscription():
    """Reactivate a canceled subscription"""
    try:
        # Get subscription
        response = db_service.client.table("subscriptions").select("*").eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data or not response.data.get("stripe_subscription_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )

        subscription_id = response.data["stripe_subscription_id"]

        # Reactivate in Stripe
        result = await stripe_service.reactivate_subscription(subscription_id)

        # Update database
        db_service.client.table("subscriptions").update({
            "cancel_at_period_end": False,
            "status": result["status"]
        }).eq("tenant_id", MOCK_TENANT_ID).execute()

        return {"message": "Subscription reactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate subscription: {str(e)}"
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(limit: int = 10):
    """Get invoices for current tenant"""
    try:
        # Get subscription with customer ID
        response = db_service.client.table("subscriptions").select("stripe_customer_id").eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data or not response.data.get("stripe_customer_id"):
            return []

        customer_id = response.data["stripe_customer_id"]

        # Get invoices from Stripe
        invoices = await stripe_service.list_invoices(customer_id, limit)
        return invoices

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch invoices: {str(e)}"
        )


@router.get("/upcoming-invoice", response_model=UpcomingInvoiceResponse)
async def get_upcoming_invoice():
    """Get upcoming invoice for current tenant"""
    try:
        # Get subscription with customer ID
        response = db_service.client.table("subscriptions").select("stripe_customer_id").eq("tenant_id", MOCK_TENANT_ID).single().execute()

        if not response.data or not response.data.get("stripe_customer_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )

        customer_id = response.data["stripe_customer_id"]

        # Get upcoming invoice from Stripe
        invoice = await stripe_service.get_upcoming_invoice(customer_id)

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No upcoming invoice found"
            )

        return invoice

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch upcoming invoice: {str(e)}"
        )


@router.get("/payment-history", response_model=List[PaymentHistoryResponse])
async def get_payment_history(limit: int = 10):
    """Get payment history from database"""
    try:
        response = db_service.client.table("payment_history").select("*").eq(
            "tenant_id", MOCK_TENANT_ID
        ).order("created_at", desc=True).limit(limit).execute()

        return response.data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payment history: {str(e)}"
        )


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )

        # Verify webhook signature
        event = stripe_service.construct_webhook_event(payload, sig_header)

        # Handle different event types
        if event.type == "checkout.session.completed":
            session = event.data.object
            await handle_checkout_completed(session)

        elif event.type == "customer.subscription.updated":
            subscription = event.data.object
            await handle_subscription_updated(subscription)

        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            await handle_subscription_deleted(subscription)

        elif event.type == "invoice.payment_succeeded":
            invoice = event.data.object
            await handle_payment_succeeded(invoice)

        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            await handle_payment_failed(invoice)

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook error: {str(e)}"
        )


# Webhook handlers
async def handle_checkout_completed(session):
    """Handle successful checkout"""
    tenant_id = session.metadata.get("tenant_id")
    billing_cycle = session.metadata.get("billing_cycle", "monthly")

    # Get subscription from Stripe
    subscription = await stripe_service.get_subscription(session.subscription)

    # Get plan ID from price
    price_id = subscription["items"]["data"][0]["price"]["id"]
    plan_response = db_service.client.table("subscription_plans").select("id").or_(
        f"stripe_price_id_monthly.eq.{price_id},stripe_price_id_yearly.eq.{price_id}"
    ).single().execute()

    # Update or create subscription in database
    db_service.client.table("subscriptions").upsert({
        "tenant_id": tenant_id,
        "plan_id": plan_response.data["id"],
        "stripe_customer_id": session.customer,
        "stripe_subscription_id": session.subscription,
        "status": subscription["status"],
        "billing_cycle": billing_cycle,
        "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
        "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
    }).execute()
    
    # Activate tenant if it's still pending (important for onboarding flow)
    tenant_response = db_service.client.table("tenants").select("status").eq("id", tenant_id).single().execute()
    if tenant_response.data and tenant_response.data.get("status") == "pending":
        db_service.client.table("tenants").update({
            "status": "active"
        }).eq("id", tenant_id).execute()


async def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    # Update subscription in database
    db_service.client.table("subscriptions").update({
        "status": subscription["status"],
        "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
        "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
        "cancel_at_period_end": subscription["cancel_at_period_end"],
        "canceled_at": datetime.fromtimestamp(subscription["canceled_at"]).isoformat() if subscription.get("canceled_at") else None,
    }).eq("stripe_subscription_id", subscription["id"]).execute()


async def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    # Move to free plan
    free_plan = db_service.client.table("subscription_plans").select("id").eq("name", "free").single().execute()

    db_service.client.table("subscriptions").update({
        "plan_id": free_plan.data["id"],
        "status": "canceled",
        "canceled_at": datetime.now().isoformat()
    }).eq("stripe_subscription_id", subscription["id"]).execute()


async def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    # Get tenant from customer
    sub_response = db_service.client.table("subscriptions").select("id, tenant_id").eq(
        "stripe_customer_id", invoice["customer"]
    ).single().execute()

    if sub_response.data:
        # Record payment in history
        db_service.client.table("payment_history").insert({
            "tenant_id": sub_response.data["tenant_id"],
            "subscription_id": sub_response.data["id"],
            "stripe_payment_intent_id": invoice.get("payment_intent"),
            "stripe_invoice_id": invoice["id"],
            "amount": invoice["amount_paid"] / 100,
            "currency": invoice["currency"].upper(),
            "status": "succeeded",
            "description": "Subscription payment"
        }).execute()


async def handle_payment_failed(invoice):
    """Handle failed payment"""
    # Get tenant from customer
    sub_response = db_service.client.table("subscriptions").select("id, tenant_id").eq(
        "stripe_customer_id", invoice["customer"]
    ).single().execute()

    if sub_response.data:
        # Record failed payment
        db_service.client.table("payment_history").insert({
            "tenant_id": sub_response.data["tenant_id"],
            "subscription_id": sub_response.data["id"],
            "stripe_invoice_id": invoice["id"],
            "amount": invoice["amount_due"] / 100,
            "currency": invoice["currency"].upper(),
            "status": "failed",
            "description": "Failed subscription payment"
        }).execute()

        # Update subscription status
        db_service.client.table("subscriptions").update({
            "status": "past_due"
        }).eq("id", sub_response.data["id"]).execute()
