import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import unquote
from modules.auth.permissions import PermissionsModule

class MockHandler:
    def __init__(self, path="/", form=None):
        self.path = path
        self.form = form or {}
        self.html_response = None
        self.redirect_path = None
        
    def send_html(self, html):
        self.html_response = html
        
    def redirect(self, path):
        self.redirect_path = path
        
    def read_form(self):
        return {k: [v] for k, v in self.form.items()}

class TestPermissionsModule(unittest.TestCase):

    @patch('modules.auth.permissions.current_user')
    @patch('modules.auth.permissions.db')
    def test_add_employee_success(self, mock_db, mock_current_user):
        # mock manager user
        mock_current_user.return_value = {"id": 1, "role": "manager", "full_name": "Manager"}
        
        form_data = {
            "full_name": "Staff 1",
            "email": "staff@example.com",
            "phone": "0111222333",
            "address": "Address 1",
            "role": "staff",
            "password": "pass"
        }
        handler = MockHandler(form=form_data)
        
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        PermissionsModule.add_employee_action(handler)
        
        mock_conn.execute.assert_called_once()
        self.assertTrue(handler.redirect_path.startswith("/employees?msg="))

    @patch('modules.auth.permissions.current_user')
    def test_add_employee_not_manager(self, mock_current_user):
        mock_current_user.return_value = {"id": 2, "role": "staff", "full_name": "Staff"}
        handler = MockHandler()
        
        PermissionsModule.add_employee_action(handler)
        
        # User is not manager, so it sends error html instead of redirect
        self.assertIsNotNone(handler.html_response)
        self.assertIn("không có quyền", handler.html_response.lower())

    @patch('modules.auth.permissions.current_user')
    @patch('modules.auth.permissions.db')
    def test_edit_employee_action(self, mock_db, mock_current_user):
        mock_current_user.return_value = {"id": 1, "role": "manager", "full_name": "Manager"}
        
        form_data = {
            "full_name": "Staff updated",
            "email": "staff_new@example.com",
            "phone": "0111222333",
            "address": "Address 1",
            "role": "staff",
            "status": "inactive",
            "new_password": "",
            "confirm_password": ""
        }
        handler = MockHandler(form=form_data)
        
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        PermissionsModule.edit_employee_action(handler, emp_id="2")
        
        mock_conn.execute.assert_called_once()
        self.assertTrue(handler.redirect_path.startswith("/employees?msg="))

    @patch('modules.auth.permissions.current_user')
    @patch('modules.auth.permissions.db')
    def test_delete_employee_action(self, mock_db, mock_current_user):
        mock_current_user.return_value = {"id": 1, "role": "manager", "full_name": "Manager"}
        handler = MockHandler()
        
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        PermissionsModule.delete_employee_action(handler, emp_id="2")
        
        mock_conn.execute.assert_called_once()
        args, _ = mock_conn.execute.call_args
        self.assertIn("DELETE FROM users", args[0])
        self.assertTrue(handler.redirect_path.startswith("/employees?msg="))

    @patch('modules.auth.permissions.current_user')
    def test_delete_employee_self(self, mock_current_user):
        mock_current_user.return_value = {"id": 1, "role": "manager", "full_name": "Manager"}
        handler = MockHandler()
        
        PermissionsModule.delete_employee_action(handler, emp_id="1")
        
        self.assertTrue(handler.redirect_path.startswith("/employees?msg="))
        self.assertIn("chính bạn", unquote(handler.redirect_path).lower())

if __name__ == "__main__":
    unittest.main()
