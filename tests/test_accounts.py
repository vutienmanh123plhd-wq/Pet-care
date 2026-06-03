import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import unquote
from modules.auth.accounts import AccountsModule
from database import password_hash

class MockHandler:
    def __init__(self, path="/", form=None, headers=None):
        self.path = path
        self.form = form or {}
        self.headers = headers or {}
        self.html_response = None
        self.redirect_path = None
        self.cookie_sent = None
        
        class MockServer:
            SESSIONS = {}
        self.server = MockServer()
        
    def send_html(self, html):
        self.html_response = html
        
    def redirect(self, path, cookie=None):
        self.redirect_path = path
        self.cookie_sent = cookie
        
    def read_form(self):
        return {k: [v] for k, v in self.form.items()}

class TestAccountsModule(unittest.TestCase):

    @patch('modules.auth.accounts.db')
    def test_login_action_success(self, mock_db):
        handler = MockHandler(form={"email": "test@example.com", "password": "password123"})
        
        # Mocking DB context manager and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = (1, "Test User", "test@example.com", password_hash("password123"))
        mock_cursor.description = [("id",), ("full_name",), ("email",), ("password_hash",)]
        
        AccountsModule.login_action(handler)
        
        self.assertEqual(handler.redirect_path, "/dashboard")
        self.assertIsNotNone(handler.cookie_sent)
        self.assertIn("sid=", handler.cookie_sent)

    @patch('modules.auth.accounts.db')
    def test_login_action_fail(self, mock_db):
        handler = MockHandler(form={"email": "test@example.com", "password": "wrong"})
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        
        # Return None for no user found or password mismatch will happen
        mock_cursor.fetchone.return_value = (1, "Test User", "test@example.com", password_hash("password123"))
        mock_cursor.description = [("id",), ("full_name",), ("email",), ("password_hash",)]
        
        AccountsModule.login_action(handler)
        
        self.assertTrue(handler.redirect_path.startswith("/login?msg="))
        self.assertIn("không đúng", unquote(handler.redirect_path))

    @patch('modules.auth.accounts.db')
    def test_register_action_success(self, mock_db):
        form_data = {
            "full_name": "New User",
            "email": "new@example.com",
            "phone": "0123456789",
            "address": "Hanoi",
            "password": "pass",
            "confirm": "pass"
        }
        handler = MockHandler(form=form_data)
        
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        mock_cursor = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, (1,), (1,)]
        
        AccountsModule.register_action(handler)
        
        self.assertTrue(mock_conn.execute.called)
        self.assertTrue(handler.redirect_path.startswith("/login?msg="))

    def test_register_action_password_mismatch(self):
        form_data = {
            "full_name": "New User",
            "email": "new@example.com",
            "phone": "0123456789",
            "address": "Hanoi",
            "password": "pass",
            "confirm": "diff"
        }
        handler = MockHandler(form=form_data)
        
        AccountsModule.register_action(handler)
        
        self.assertTrue(handler.redirect_path.startswith("/register?msg="))

    @patch('modules.auth.accounts.current_user')
    @patch('modules.auth.accounts.db')
    def test_profile_edit_action(self, mock_db, mock_current_user):
        mock_current_user.return_value = {"id": 1, "email": "test@example.com"}
        
        form_data = {
            "full_name": "Updated User",
            "email": "updated@example.com",
            "phone": "0999999999",
            "address": "HCMC",
            "new_password": "",
            "confirm_password": ""
        }
        handler = MockHandler(form=form_data)
        
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        AccountsModule.profile_edit_action(handler)
        
        self.assertTrue(mock_conn.execute.called)
        self.assertTrue(handler.redirect_path.startswith("/profile?msg="))

    def test_logout(self):
        handler = MockHandler()
        handler.headers = {"Cookie": "sid=test-session-id"}
        handler.server.SESSIONS = {"test-session-id": 1}
        
        AccountsModule.logout(handler)
        
        self.assertNotIn("test-session-id", handler.server.SESSIONS)
        self.assertTrue(handler.redirect_path.startswith("/login?msg="))
        self.assertIn("sid=; Path=/; Max-Age=0", handler.cookie_sent)

if __name__ == "__main__":
    unittest.main()
