"""HTTP API for the billing bounded context.

`/v1/billing/webhook` is the one endpoint in this whole service deliberately
NOT behind `get_current_identity` — Stripe calls it directly, authenticated
by its own request signature (docs/ARCHITECTURE.md §9), not a Supabase JWT.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core_api.billing.api.schemas import (
    CheckoutSessionResponse,
    CreateCheckoutSessionRequest,
    CreatePortalSessionRequest,
    PortalSessionResponse,
    SubscriptionResponse,
)
from core_api.billing.application.use_cases import (
    CreateCheckoutSessionInput,
    CreateCheckoutSessionUseCase,
    CreatePortalSessionInput,
    CreatePortalSessionUseCase,
    GetSubscriptionUseCase,
    HandleStripeWebhookEventUseCase,
)
from core_api.billing.domain.entities import SubscriptionStatus, SubscriptionTier
from core_api.billing.domain.exceptions import NoStripeCustomerError
from core_api.billing.domain.repositories import StripeEventRepository, SubscriptionRepository
from core_api.billing.domain.stripe_port import (
    StripeClient,
    StripeError,
    StripeWebhookSignatureError,
)
from core_api.dependencies import (
    get_current_identity,
    get_stripe_client,
    get_stripe_event_repository,
    get_subscription_repository,
)
from core_api.identity.application.use_cases import AuthenticatedIdentity

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    subscription_repository: Annotated[
        SubscriptionRepository, Depends(get_subscription_repository)
    ],
) -> SubscriptionResponse:
    subscription = await GetSubscriptionUseCase(subscription_repository).execute(identity.id)
    if subscription is None:
        return SubscriptionResponse(
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_end=None,
        )
    return SubscriptionResponse(
        tier=subscription.tier.value,
        status=subscription.status.value,
        current_period_end=subscription.current_period_end,
    )


@router.post(
    "/checkout-session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    subscription_repository: Annotated[
        SubscriptionRepository, Depends(get_subscription_repository)
    ],
    stripe_client: Annotated[StripeClient, Depends(get_stripe_client)],
) -> CheckoutSessionResponse:
    use_case = CreateCheckoutSessionUseCase(subscription_repository, stripe_client)
    try:
        result = await use_case.execute(
            CreateCheckoutSessionInput(
                user_id=identity.id,
                user_email=identity.email,
                price_id=payload.price_id,
                success_url=payload.success_url,
                cancel_url=payload.cancel_url,
            )
        )
    except StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is temporarily unavailable",
        ) from exc
    return CheckoutSessionResponse(checkout_url=result.checkout_url)


@router.post("/portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    payload: CreatePortalSessionRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    subscription_repository: Annotated[
        SubscriptionRepository, Depends(get_subscription_repository)
    ],
    stripe_client: Annotated[StripeClient, Depends(get_stripe_client)],
) -> PortalSessionResponse:
    use_case = CreatePortalSessionUseCase(subscription_repository, stripe_client)
    try:
        result = await use_case.execute(
            CreatePortalSessionInput(user_id=identity.id, return_url=payload.return_url)
        )
    except NoStripeCustomerError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No subscription to manage"
        ) from exc
    except StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is temporarily unavailable",
        ) from exc
    return PortalSessionResponse(portal_url=result.portal_url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    subscription_repository: Annotated[
        SubscriptionRepository, Depends(get_subscription_repository)
    ],
    stripe_event_repository: Annotated[
        StripeEventRepository, Depends(get_stripe_event_repository)
    ],
    stripe_client: Annotated[StripeClient, Depends(get_stripe_client)],
) -> dict[str, str]:
    payload = await request.body()
    signature_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.construct_webhook_event(payload, signature_header)
    except StripeWebhookSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        ) from exc

    await HandleStripeWebhookEventUseCase(subscription_repository, stripe_event_repository).execute(
        event
    )
    return {"status": "ok"}
