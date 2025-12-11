"""Authentication endpoints for Auth0 integration."""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Union, List

from app.services.auth_service import (
    auth_service,
    get_current_user,
    get_current_user_optional
)
from app.services.database import db_service
from app.services.feature_service import feature_service
from app.services.entitlements_service import entitlements_service
from app.services.stripe_service import stripe_service
from app.services.email_service import email_service
import secrets

router = APIRouter()


class OnboardingRequest(BaseModel):
    """Request body for completing onboarding."""
    organization_name: Optional[str] = None


class CheckEmailRequest(BaseModel):
    """Request to check if email exists."""
    email: EmailStr


class CheckEmailResponse(BaseModel):
    """Response for email check."""
    exists: bool
    has_auth0_account: bool
    has_n8n_ops_account: bool
    message: Optional[str] = None


class OnboardingOrganizationRequest(BaseModel):
    """Request for organization setup step."""
    organization_name: str
    industry: Optional[str] = None
    company_size: Optional[str] = None


class OnboardingPlanRequest(BaseModel):
    """Request for plan selection step."""
    plan_name: str  # "free", "pro", "enterprise"
    billing_cycle: Optional[str] = "monthly"  # "monthly" or "yearly"


class OnboardingPaymentRequest(BaseModel):
    """Request for payment setup step."""
    plan_name: str
    billing_cycle: str
    success_url: str
    cancel_url: str


class TeamInviteRequest(BaseModel):
    """Request for team invitation."""
    email: EmailStr
    role: str  # "developer" or "viewer"


class OnboardingTeamRequest(BaseModel):
    """Request for team setup step."""
    invites: List[TeamInviteRequest]


class OnboardingCompleteRequest(BaseModel):
    """Request to complete onboarding."""
    pass


class UserUpdateRequest(BaseModel):
    """Request body for updating user profile."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    """Response containing user and tenant info."""
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    tenant_name: str
    subscription_plan: str
    has_environment: bool
    is_new: bool = False


@router.get("/me")
async def get_current_user_info(user_info: dict = Depends(get_current_user)):
    """Get current authenticated user information."""
    user = user_info.get("user")
    tenant = user_info.get("tenant")

    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user has any environments
    env_response = db_service.client.table("environments").select(
        "id", count="exact"
    ).eq("tenant_id", tenant["id"]).execute()
    has_environment = (env_response.count or 0) > 0

    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        tenant_id=tenant["id"],
        tenant_name=tenant["name"],
        subscription_plan=tenant.get("subscription_tier", "free"),
        has_environment=has_environment,
        is_new=False
    )


@router.get("/status")
async def get_auth_status(user_info: dict = Depends(get_current_user_optional)):
    """Check authentication status and whether onboarding is needed."""
    is_new = user_info.get("is_new", False)
    user = user_info.get("user")
    tenant = user_info.get("tenant")

    if is_new and user is None:
        # User needs to complete onboarding
        return {
            "authenticated": True,
            "onboarding_required": True,
            "user": None,
            "auth0_id": user_info.get("auth0_id"),
            "email": user_info.get("email"),
            "name": user_info.get("name")
        }

    # Check if user has any environments
    has_environment = False
    if tenant:
        env_response = db_service.client.table("environments").select(
            "id", count="exact"
        ).eq("tenant_id", tenant["id"]).execute()
        has_environment = (env_response.count or 0) > 0

    # Get plan features and usage for authenticated users
    features = None
    usage = None
    entitlements = None
    if tenant:
        try:
            usage = await feature_service.get_usage_summary(tenant["id"])
            features = usage.get("features", {})
        except Exception:
            features = None
            usage = None

        # Get entitlements from new entitlements service
        try:
            entitlements = await entitlements_service.get_tenant_entitlements(tenant["id"])
        except Exception:
            entitlements = None

    return {
        "authenticated": True,
        "onboarding_required": False,
        "has_environment": has_environment,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        } if user else None,
        "tenant": {
            "id": tenant["id"],
            "name": tenant["name"],
            "subscription_plan": tenant.get("subscription_tier", "free")
        } if tenant else None,
        "features": features,
        "usage": {
            "environments": usage.get("environments") if usage else None,
            "team_members": usage.get("team_members") if usage else None,
        } if usage else None,
        "entitlements": {
            "plan_id": entitlements.get("plan_id") if entitlements else None,
            "plan_name": entitlements.get("plan_name", "free") if entitlements else "free",
            "entitlements_version": entitlements.get("entitlements_version", 0) if entitlements else 0,
            "features": entitlements.get("features", {}) if entitlements else {},
        } if entitlements else None,
    }


@router.post("/onboarding")
async def complete_onboarding(
    request: OnboardingRequest,
    user_info: dict = Depends(get_current_user_optional)
):
    """Complete user onboarding - creates user and tenant."""
    if not user_info.get("is_new") or user_info.get("user") is not None:
        # User already exists
        user = user_info.get("user")
        tenant = user_info.get("tenant")

        # Check if user has any environments
        has_environment = False
        if tenant:
            env_response = db_service.client.table("environments").select(
                "id", count="exact"
            ).eq("tenant_id", tenant["id"]).execute()
            has_environment = (env_response.count or 0) > 0

        return {
            "success": True,
            "message": "User already exists",
            "user": UserResponse(
                id=user["id"],
                email=user["email"],
                name=user["name"],
                role=user["role"],
                tenant_id=tenant["id"],
                tenant_name=tenant["name"],
                subscription_plan=tenant.get("subscription_tier", "free"),
                has_environment=has_environment,
                is_new=False
            )
        }

    # Create new user and tenant
    auth0_id = user_info.get("auth0_id")
    email = user_info.get("email")
    name = user_info.get("name")

    if not auth0_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required user information"
        )

    result = await auth_service.create_user_and_tenant(
        auth0_id=auth0_id,
        email=email,
        name=name,
        organization_name=request.organization_name
    )

    user = result["user"]
    tenant = result["tenant"]

    return {
        "success": True,
        "message": "User and tenant created successfully",
        "user": UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            tenant_id=tenant["id"],
            tenant_name=tenant["name"],
            subscription_plan=tenant.get("subscription_tier", "free"),
            has_environment=False,
            is_new=True
        )
    }


@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email(request: CheckEmailRequest):
    """Check if email exists in Auth0 or n8n-ops database."""
    email = request.email.lower().strip()
    
    # Check if email exists in n8n-ops database
    user_response = db_service.client.table("users").select("id, email").eq("email", email).execute()
    has_n8n_ops_account = user_response.data and len(user_response.data) > 0
    
    # Note: Auth0 check would require Auth0 Management API
    # For now, we'll check if user exists in our database
    # In production, you'd want to check Auth0 as well
    has_auth0_account = has_n8n_ops_account  # Simplified for now
    
    if has_n8n_ops_account:
        return CheckEmailResponse(
            exists=True,
            has_auth0_account=has_auth0_account,
            has_n8n_ops_account=has_n8n_ops_account,
            message="An account with this email already exists. Please sign in instead."
        )
    
    return CheckEmailResponse(
        exists=False,
        has_auth0_account=False,
        has_n8n_ops_account=False,
        message=None
    )


@router.post("/onboarding/organization")
async def onboarding_organization(
    request: OnboardingOrganizationRequest,
    user_info: dict = Depends(get_current_user_optional)
):
    """Step 1: Create organization/tenant."""
    if not user_info.get("is_new") or user_info.get("user") is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an account. Please sign in instead."
        )
    
    auth0_id = user_info.get("auth0_id")
    email = user_info.get("email")
    name = user_info.get("name")
    
    if not auth0_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required user information. Please ensure you're properly authenticated."
        )
    
    # Validate organization name
    if not request.organization_name or not request.organization_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name is required and cannot be empty."
        )
    
    if len(request.organization_name.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name must be at least 2 characters long."
        )
    
    if len(request.organization_name.strip()) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name must be 100 characters or less."
        )
    
    # Create tenant with pending status
    result = await auth_service.create_user_and_tenant(
        auth0_id=auth0_id,
        email=email,
        name=name,
        organization_name=request.organization_name
    )
    
    # Update tenant with additional info
    tenant = result["tenant"]
    update_data = {"status": "pending"}
    if request.industry:
        update_data["metadata"] = {"industry": request.industry}
    if request.company_size:
        if "metadata" not in update_data:
            update_data["metadata"] = {}
        update_data["metadata"]["company_size"] = request.company_size
    
    if update_data:
        db_service.client.table("tenants").update(update_data).eq("id", tenant["id"]).execute()
    
    return {
        "success": True,
        "tenant_id": tenant["id"],
        "tenant_name": tenant["name"]
    }


@router.post("/onboarding/select-plan")
async def onboarding_select_plan(
    request: OnboardingPlanRequest,
    user_info: dict = Depends(get_current_user_optional)
):
    """Step 2: Select subscription plan."""
    user = user_info.get("user")
    tenant = user_info.get("tenant")
    
    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User or tenant not found. Please complete organization setup first."
        )
    
    # Validate plan name
    valid_plans = ["free", "pro", "enterprise"]
    if not request.plan_name or request.plan_name not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan selected. Please choose one of: {', '.join(valid_plans)}"
        )
    
    # Validate billing cycle
    if request.billing_cycle and request.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing cycle. Must be 'monthly' or 'yearly'"
        )
    
    # Update tenant subscription tier
    db_service.client.table("tenants").update({
        "subscription_tier": request.plan_name
    }).eq("id", tenant["id"]).execute()
    
    return {
        "success": True,
        "plan": request.plan_name,
        "billing_cycle": request.billing_cycle
    }


@router.post("/onboarding/payment")
async def onboarding_payment(
    request: OnboardingPaymentRequest,
    user_info: dict = Depends(get_current_user_optional)
):
    """Step 3: Setup payment for paid plans."""
    user = user_info.get("user")
    tenant = user_info.get("tenant")
    
    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User or tenant not found. Please complete previous onboarding steps first."
        )
    
    # Validate plan name
    if request.plan_name not in ["free", "pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan name: {request.plan_name}"
        )
    
    # Validate billing cycle
    if request.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing cycle. Must be 'monthly' or 'yearly'"
        )
    
    # If free plan, skip payment
    if request.plan_name == "free":
        # Activate tenant
        db_service.client.table("tenants").update({
            "status": "active"
        }).eq("id", tenant["id"]).execute()
        
        return {
            "success": True,
            "requires_payment": False,
            "message": "Free plan selected. No payment required."
        }
    
    # Get plan details
    plan_response = db_service.client.table("subscription_plans").select("*").eq(
        "name", request.plan_name
    ).eq("is_active", True).single().execute()
    
    if not plan_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription plan '{request.plan_name}' is not available. Please select a different plan."
        )
    
    plan = plan_response.data
    
    # Get price ID based on billing cycle
    price_id = None
    if request.billing_cycle == "monthly":
        price_id = plan.get("stripe_price_id_monthly")
    else:
        price_id = plan.get("stripe_price_id_yearly")
    
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Price ID not configured for {request.plan_name} plan ({request.billing_cycle})"
        )
    
    # Check if tenant already has Stripe customer
    customer_id = None
    sub_response = db_service.client.table("subscriptions").select("stripe_customer_id").eq(
        "tenant_id", tenant["id"]
    ).execute()
    
    if sub_response.data and len(sub_response.data) > 0:
        customer_id = sub_response.data[0].get("stripe_customer_id")
    
    # Create Stripe customer if needed
    if not customer_id:
        customer = await stripe_service.create_customer(
            email=user["email"],
            name=user["name"],
            tenant_id=tenant["id"]
        )
        customer_id = customer["id"]
    
    # Create checkout session
    session = await stripe_service.create_checkout_session(
        customer_id=customer_id,
        price_id=price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        tenant_id=tenant["id"],
        billing_cycle=request.billing_cycle
    )
    
    return {
        "success": True,
        "requires_payment": True,
        "checkout_url": session["url"],
        "session_id": session["session_id"]
    }


@router.post("/onboarding/invite-team")
async def onboarding_invite_team(
    request: OnboardingTeamRequest,
    user_info: dict = Depends(get_current_user)
):
    """Step 4: Invite team members."""
    user = user_info.get("user")
    tenant = user_info.get("tenant")
    
    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User or tenant not found. Please complete organization setup first."
        )
    
    # Validate invites
    if not request.invites or len(request.invites) == 0:
        return {
            "success": True,
            "invited_count": 0,
            "message": "No invitations sent"
        }
    
    # Validate invite list size (prevent abuse)
    if len(request.invites) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite more than 50 team members at once. Please split into multiple requests."
        )
    
    invited_count = 0
    errors = []
    
    # Email validation regex
    import re
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    for invite in request.invites:
        try:
            # Validate email format
            if not invite.email or not invite.email.strip():
                errors.append(f"Invalid email: Email address is required")
                continue
            
            email_lower = invite.email.strip().lower()
            if not email_pattern.match(email_lower):
                errors.append(f"{invite.email}: Invalid email format")
                continue
            
            # Validate role
            valid_roles = ["developer", "viewer", "admin"]
            if invite.role not in valid_roles:
                errors.append(f"{invite.email}: Invalid role. Must be one of: {', '.join(valid_roles)}")
                continue
            
            # Check if user already exists
            existing = db_service.client.table("users").select("id").eq(
                "email", email_lower
            ).eq("tenant_id", tenant["id"]).execute()
            
            if existing.data and len(existing.data) > 0:
                errors.append(f"{invite.email}: User is already a member of this organization")
                continue
            
            # Create team member with pending status
            import uuid
            from datetime import datetime
            
            team_member_id = str(uuid.uuid4())
            # Generate invitation token
            invitation_token = secrets.token_urlsafe(32)
            
            team_data = {
                "id": team_member_id,
                "tenant_id": tenant["id"],
                "email": email_lower,  # Store normalized email
                "role": invite.role,
                "status": "pending",
                "invited_by": user["id"],
                "invitation_token": invitation_token,
                "invited_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            db_service.client.table("users").insert(team_data).execute()
            
            # Send invitation email
            try:
                # Get inviter name
                inviter_name = user.get("name", "A team member")
                # Get organization name
                org_name = tenant.get("name", "the organization")
                
                email_sent = await email_service.send_team_invitation(
                    to_email=email_lower,
                    to_name=None,  # We don't have the invitee's name yet
                    organization_name=org_name,
                    inviter_name=inviter_name,
                    role=invite.role,
                    invitation_token=invitation_token
                )
                
                if not email_sent:
                    # Log warning but don't fail the invitation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to send invitation email to {email_lower}, but user record was created")
            except Exception as email_error:
                # Log error but don't fail the invitation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending invitation email to {email_lower}: {str(email_error)}")
            
            # Send invitation email
            try:
                # Get inviter name
                inviter_name = user.get("name", "A team member")
                # Get organization name
                org_name = tenant.get("name", "the organization")
                
                email_sent = await email_service.send_team_invitation(
                    to_email=invite.email,
                    to_name=None,  # We don't have the invitee's name yet
                    organization_name=org_name,
                    inviter_name=inviter_name,
                    role=invite.role,
                    invitation_token=invitation_token
                )
                
                if not email_sent:
                    # Log warning but don't fail the invitation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to send invitation email to {invite.email}, but user record was created")
            except Exception as email_error:
                # Log error but don't fail the invitation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending invitation email to {invite.email}: {str(email_error)}")
            
            invited_count += 1
        except Exception as e:
            errors.append(f"{invite.email}: {str(e)}")
    
    return {
        "success": True,
        "invited_count": invited_count,
        "errors": errors if errors else None
    }


@router.post("/onboarding/complete")
async def onboarding_complete(
    request: OnboardingCompleteRequest,
    user_info: dict = Depends(get_current_user)
):
    """Step 5: Complete onboarding."""
    user = user_info.get("user")
    tenant = user_info.get("tenant")
    
    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User or tenant not found"
        )
    
    # Activate tenant if not already active
    if tenant.get("status") != "active":
        db_service.client.table("tenants").update({
            "status": "active"
        }).eq("id", tenant["id"]).execute()
    
    # Mark user onboarding as complete
    db_service.client.table("users").update({
        "onboarding_completed": True
    }).eq("id", user["id"]).execute()
    
    return {
        "success": True,
        "message": "Onboarding completed successfully"
    }


# =============================================================================
# DEV MODE ENDPOINTS - Bypass Auth0 for local development
# =============================================================================

@router.get("/dev/users")
async def get_dev_users():
    """Get all users for dev mode - allows switching between users."""
    try:
        response = db_service.client.table("users").select("id, email, name, tenant_id, role").execute()
        return {"users": response.data or []}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.post("/dev/login-as/{user_id}")
async def dev_login_as(user_id: str):
    """Login as a specific user in dev mode - bypasses Auth0."""
    try:
        # Get user
        user_response = db_service.client.table("users").select("*").eq("id", user_id).single().execute()
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user = user_response.data

        # Get tenant
        tenant_response = db_service.client.table("tenants").select("*").eq("id", user["tenant_id"]).single().execute()
        if not tenant_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        tenant = tenant_response.data

        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user.get("role", "admin"),
            },
            "tenant": {
                "id": tenant["id"],
                "name": tenant["name"],
                "subscription_tier": tenant.get("subscription_tier", "free"),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to login as user: {str(e)}"
        )


@router.post("/dev/create-user")
async def dev_create_user(organization_name: Optional[str] = None):
    """Create a new user and tenant in dev mode for initial setup."""
    import uuid
    from datetime import datetime

    try:
        # Create tenant
        tenant_id = str(uuid.uuid4())
        tenant_data = {
            "id": tenant_id,
            "name": organization_name or "Dev Organization",
            "subscription_tier": "free",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        tenant_response = db_service.client.table("tenants").insert(tenant_data).execute()
        tenant = tenant_response.data[0]

        # Create user
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": "dev@example.com",
            "name": "Dev User",
            "role": "admin",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        user_response = db_service.client.table("users").insert(user_data).execute()
        user = user_response.data[0]

        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
            },
            "tenant": {
                "id": tenant["id"],
                "name": tenant["name"],
                "subscription_tier": tenant.get("subscription_tier", "free"),
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


# =============================================================================
# END DEV MODE ENDPOINTS
# =============================================================================


@router.patch("/me")
async def update_current_user(
    updates: UserUpdateRequest,
    user_info: dict = Depends(get_current_user)
):
    """Update current user's profile information."""
    user = user_info.get("user")
    tenant = user_info.get("tenant")

    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build update data (only include fields that are provided)
    update_data = {}
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.email is not None:
        update_data["email"] = updates.email
    if updates.role is not None:
        # Only allow role updates if current user is admin
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update user roles"
            )
        update_data["role"] = updates.role

    if not update_data:
        # No updates provided
        return UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            tenant_id=tenant["id"],
            tenant_name=tenant["name"],
            subscription_plan=tenant.get("subscription_tier", "free"),
            has_environment=False,
            is_new=False
        )

    try:
        # Update user in database
        response = db_service.client.table("users").update(update_data).eq(
            "id", user["id"]
        ).eq("tenant_id", tenant["id"]).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updated_user = response.data[0]

        # Check if user has any environments
        env_response = db_service.client.table("environments").select(
            "id", count="exact"
        ).eq("tenant_id", tenant["id"]).execute()
        has_environment = (env_response.count or 0) > 0

        return UserResponse(
            id=updated_user["id"],
            email=updated_user["email"],
            name=updated_user["name"],
            role=updated_user["role"],
            tenant_id=tenant["id"],
            tenant_name=tenant["name"],
            subscription_plan=tenant.get("subscription_tier", "free"),
            has_environment=has_environment,
            is_new=False
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )
