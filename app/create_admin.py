"""
Create (or reset the password of) the Soleslay admin user.

Usage:
    python -m app.create_admin --username owner
    python -m app.create_admin --username owner --password 'some-strong-password'

If --password is omitted you'll be prompted securely (input hidden,
never echoed or logged). The password is hashed with bcrypt before
touching the database — plaintext never gets written anywhere.
"""
import argparse
import getpass
import sys

from .db import Base, engine, session_scope
from .auth import hash_password
from .models_db import AdminUser


def create_or_update_admin(username: str, password: str) -> None:
    Base.metadata.create_all(bind=engine)
    if len(password) < 10:
        print("Error: password must be at least 10 characters.", file=sys.stderr)
        sys.exit(1)

    with session_scope() as db:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if user:
            user.password_hash = hash_password(password)
            user.is_active = True
            print(f"Password updated for existing admin user '{username}'.")
        else:
            user = AdminUser(username=username, password_hash=hash_password(password))
            db.add(user)
            print(f"Admin user '{username}' created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or reset the Soleslay admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", default=None, help="If omitted, you'll be prompted (hidden input).")
    args = parser.parse_args()

    pw = args.password or getpass.getpass("New admin password (min 10 chars): ")
    confirm = args.password or getpass.getpass("Confirm password: ")
    if pw != confirm:
        print("Error: passwords did not match.", file=sys.stderr)
        sys.exit(1)

    create_or_update_admin(args.username, pw)
