# User Avatar Handling

This document describes how user avatars are handled in iqoqo.

- Backend: The `User` model contains an `avatar_url` column for storing an externally-hosted profile picture (e.g. Google profile image). An Alembic migration adding this column exists at `migrations/versions/2973a4475ace_add_user_profiles_auth_and_rbac.py`.
- Google OAuth: The Google ID token `picture` claim is extracted and stored in `User.avatar_url` during the OAuth callback (see `app/api/auth.py`).
- Frontend: A small `Avatar` UI component was added at `frontend/components/ui/avatar.tsx`. It prefers `src` images and falls back to rendered initials when `avatar_url` is not available. The Navbar and Profile pages use this component.
- Next.js config: `frontend/next.config.ts` allows `lh3.googleusercontent.com` as an image source for remote optimisation.
- Testing: A unit test `tests/test_profile.py::test_user_to_dict_includes_avatar` asserts that `User.to_dict()` includes `avatar_url`.
- Notes: If the database in your deployment does not yet have the `avatar_url` column, apply migrations (Alembic) to add it.
