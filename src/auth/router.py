"""
Controller / Route Handler Layer
==================================
Outermost application layer. Handles incoming HTTP requests and delegates
to the service layer for all business logic.

Dependency direction: inward only.
  - Imports from: services, dependencies, domain/schemas, providers, infrastructure
  - Must NOT be imported by any inner layer

Controllers are deliberately thin — they:
  1. Extract validated input (via Pydantic schemas or dependency injection)
  2. Call a single service method per logical operation
  3. Map the result to an HTTP response

If a controller grows complex logic, move it to the service layer.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.auth.config import auth_settings
from src.auth.dependencies import (
    RefreshTokenBearer,
    RoleChecker,
    get_current_user,
    get_redis,
)
from src.auth.errors import (
    GoogleAuthenticationFailed,
)
from src.auth.oauth_config import oauth
from src.auth.redis import RedisService
from src.auth.schema_examples import (
    LOGOUT_ALL_RESPONSES,
    LOGOUT_RESPONSES,
    REFRESH_TOKEN_RESPONSES,
)
from src.auth.schemas import (
    UserCreateOAuth,
)
from src.auth.service import UserService
from src.db.database import get_session
from src.mail import send_email_by_type

router = APIRouter()

_user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


@router.post(
    "/token/refresh",
    status_code=status.HTTP_200_OK,
    description="Refresh an expired access token using a valid refresh token",
    responses=REFRESH_TOKEN_RESPONSES,  # type: ignore
    
)
async def refresh_token(
    redis: RedisService = Depends(get_redis),
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(RefreshTokenBearer()),
):
    old_jti = token_details["jti"]
    user_id = token_details["user"]["user_id"]

    # Rotate: revoke old JTI before issuing a new pair
    await redis.remove_jti_from_user_sessions(user_id=user_id, jti=old_jti)
    tokens = await _user_service.create_token_pair(token_details["user"], session, redis)

    return {"status": "success", "message": "Token refreshed successfully", **tokens}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    responses=LOGOUT_RESPONSES,  # type: ignore
)
async def logout(
    token_details: dict = Depends(RefreshTokenBearer()),
    redis: RedisService = Depends(get_redis),
):
    await _user_service.revoke_token(
        user_id=token_details["user"]["user_id"],
        jti=token_details["jti"],
        redis=redis
    )
    return {"status": "success", "message": "Logged out successfully"}


@router.post(
    "/logout/all",
    status_code=status.HTTP_200_OK,
    responses=LOGOUT_ALL_RESPONSES,  # type: ignore
)
async def logout_all(
    user=Depends(get_current_user),
    redis: RedisService = Depends(get_redis),
):
    await _user_service.revoke_all_tokens(user_id=str(user.id), redis=redis)
    return {"status": "success", "message": "Logged out of all devices successfully."}


# Google OAuth

@router.get(
    "/google",
    status_code=status.HTTP_302_FOUND,
    description="""
**Google OAuth Authentication**

Initiates the Google OAuth flow. This endpoint performs a browser redirect —
it will not work correctly in Swagger UI. To test:

1. Copy the full URL: `http://127.0.0.1:8000/api/v1/auth/google`
2. Paste it directly into your browser's address bar
3. After authenticating, you will be redirected back to the callback URL
    """,
    responses={302: {"description": "Redirect to Google OAuth authorization page"}},
)
async def google_auth(request: Request):
    return await oauth.google.authorize_redirect(request, auth_settings.GOOGLE_REDIRECT_URI)


@router.get("/google/callback", include_in_schema=False)
async def google_auth_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: RedisService = Depends(get_redis),
):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        email = user_info.get("email")
        AUTH_PROVIDER = "google"

        existing_user = await _user_service.get_user_by_email(email, session)

        if existing_user and existing_user.auth_provider == AUTH_PROVIDER:
            # Returning OAuth user — log them in
            tokens = await _user_service.handle_oauth_login(existing_user, session, redis=redis)
            redirect_url = (
                f"{settings.FRONTEND_CALLBACK_URL}"
                f"?access={tokens['access']}&refresh={tokens['refresh']}&is_new=false"
            )
            return RedirectResponse(redirect_url)

        # New OAuth user — register them
        user_create_obj = UserCreateOAuth(
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            email=email,
            google_id=user_info.get("sub"),
            auth_provider=AUTH_PROVIDER,
        )

        new_user, tokens = await _user_service.handle_oauth_register(
            user_create_obj, session, redis
        )

        send_email_by_type(
            background_tasks, "welcome", new_user.email, new_user.first_name
        )

        redirect_url = (
            f"{settings.FRONTEND_CALLBACK_URL}"
            f"?access={tokens['access']}&refresh={tokens['refresh']}&is_new=true"
        )
        return RedirectResponse(redirect_url)

    except Exception as e:
        logging.exception(f"Google authentication failed: {e}")
        raise GoogleAuthenticationFailed()