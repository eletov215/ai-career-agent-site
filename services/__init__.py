"""Application services for AI Career Agent."""

from .oauth_identity import (
    OAuthIdentityError,
    OAuthIdentityOwnedByAnotherUser,
    OAuthIdentityResult,
    OAuthIdentityService,
    OAuthProviderSlotOccupied,
    UnsupportedOAuthProvider,
)

__all__ = [
    "OAuthIdentityError",
    "OAuthIdentityOwnedByAnotherUser",
    "OAuthIdentityResult",
    "OAuthIdentityService",
    "OAuthProviderSlotOccupied",
    "UnsupportedOAuthProvider",
]
