from src.exceptions import ARCIPError


class NotAuthenticated(ARCIPError):
    """User is not authenticated"""
    def __init__(self, message: str = "Not Authenticated"):
        self.message = message
        super().__init__(message)


class InvalidToken(ARCIPError):
    """User has provided an invalid or expired token"""
    def __init__(self, message: str = "Invalid token or token expired"):
        self.message = message
        super().__init__(message)


class RevokedToken(ARCIPError):
    """User has provided a token that has been revoked"""
    def __init__(self, message: str = "Token has been revoked"):
        self.message = message
        super().__init__(message)


class AccessTokenRequired(ARCIPError):
    """User has provided a refresh token when an access token is needed"""
    def __init__(self, message: str = "Access token required"):
        self.message = message
        super().__init__(message)


class RefreshTokenRequired(ARCIPError):
    """User has provided an access token when a refresh token is needed"""
    def __init__(self, message: str = "Refresh token required"):
        self.message = message
        super().__init__(message)


class UserNotActive(ARCIPError):
    """User account is disabled"""
    def __init__(self, message: str = "Your account has been disabled. Please contact support for assistance"):
        self.message = message
        super().__init__(message)


class GoogleAuthenticationFailed(ARCIPError):
    """Google authentication failed"""
    def __init__(self, message: str = "Google authentication failed"):
        self.message = message
        super().__init__(message)
