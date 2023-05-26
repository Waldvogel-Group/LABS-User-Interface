from unittest import TestCase, main

import os
import sys

### Add the parent directory to the path, otherwise the import of the app module will fail ###
topdir = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(topdir)


from flask import Flask
from app import create_app, db


app = create_app(environment="testing")


class TestApp(TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_ctx = app.app_context()
        self.app_ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_ctx.pop()

    def register(
        self,
        username,
        email,
        shortID,
        password="password",
        confirmation="password",
    ):
        return self.client.post(
            "/register",
            data=dict(
                username=username,
                shortID=shortID,
                email=email,
                password=password,
                password_confirmation=confirmation,
            ),
            follow_redirects=True,
        )

    def login(self, user_id, password="password"):
        return self.client.post(
            "/login",
            data=dict(user_id=user_id, password=password),
            follow_redirects=True,
        )

    def logout(self):
        return self.client.get("/logout", follow_redirects=True)

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_registration_page(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_registration(self):
        # Valid data should register successfully.
        response = self.register("alice", "alice@example.com", "ALI")
        self.assertIn(b"Registration successful. You are logged in.", response.data)
        # Password/Confirmation mismatch should fail.
        response = self.register(
            "bob",
            "bob@example.org",
            "BOB",
            password="password",
            confirmation="Password",
        )
        self.assertIn(b"The given data was invalid.", response.data)
        # Existing username registration should fail.
        response = self.register(
            "alice",
            "alice01@example.com",
            "XYZ",
        )
        self.assertIn(b"The given data was invalid.", response.data)
        # Existing email registration should fail.
        response = self.register("alicia", "alice@example.com", "XYZ")
        self.assertIn(b"The given data was invalid.", response.data)

    def test_login_and_logout(self):
        # Access to logout view before login should fail.
        response = self.logout()
        self.assertIn(b"Please log in to access this page.", response.data)
        # New user will be automatically logged in.
        self.register("sam", "sam@example.com", "SAM")
        # Should successfully logout the currently logged in user.
        response = self.logout()
        self.assertIn(b"You were logged out.", response.data)
        # Incorrect login credentials should fail.
        response = self.login("sam@example.com", "wrongpassword")
        self.assertIn(b"Wrong user ID or password.", response.data)
        # Correct credentials should login
        response = self.login("sam")
        self.assertIn(b"Login successful.", response.data)


if __name__ == "__main__":
    main()
