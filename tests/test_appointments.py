import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import unquote
from modules.appointments.appointments import AppointmentsModule

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
        return {k: v if isinstance(v, list) else [v] for k, v in self.form.items()}

class TestAppointmentsModule(unittest.TestCase):

    @patch('modules.appointments.appointments.current_user')
    @patch('modules.appointments.appointments.db')
    def test_create_appointment_success(self, mock_db, mock_current_user):
        mock_current_user.return_value = {"id": 1, "role": "customer", "full_name": "Customer"}
        
        form_data = {
            "service_id": ["1", "2"],
            "pet_name": "Buddy",
            "pet_type": "Dog",
            "appointment_date": "2026-06-10",
            "appointment_time": "14:00",
            "note": "Test note"
        }
        handler = MockHandler(form=form_data)
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        
        # mock fetchall for services selection
        mock_cursor.fetchall.return_value = [
            (1, "Service 1", "desc", 100000), 
            (2, "Service 2", "desc", 150000)
        ]
        
        # mock fetchone for OUTPUT INSERTED.id
        mock_cursor.fetchone.return_value = [10]
        
        AppointmentsModule.create_appointment(handler)
        
        self.assertEqual(mock_conn.execute.call_count, 4) # SELECT + 1 INSERT appt + 2 INSERT appt_services
        self.assertTrue(handler.redirect_path.startswith("/appointments?msg="))

    @patch('modules.appointments.appointments.current_user')
    def test_create_appointment_no_service(self, mock_current_user):
        mock_current_user.return_value = {"id": 1, "role": "customer", "full_name": "Customer"}
        
        form_data = {
            "service_id": [], # no service selected
            "pet_name": "Buddy",
            "pet_type": "Dog",
            "appointment_date": "2026-06-10",
            "appointment_time": "14:00",
        }
        handler = MockHandler(form=form_data)
        
        AppointmentsModule.create_appointment(handler)
        
        self.assertTrue(handler.redirect_path.startswith("/appointments/new?msg="))
        self.assertIn("ít nhất một dịch vụ", unquote(handler.redirect_path).lower())

    @patch('modules.appointments.appointments.current_user')
    @patch('modules.appointments.appointments.db')
    def test_cancel_appointment(self, mock_db, mock_current_user):
        mock_current_user.return_value = {"id": 1, "role": "customer", "full_name": "Customer"}
        
        form_data = {"appointment_id": "10"}
        handler = MockHandler(form=form_data)
        
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        AppointmentsModule.cancel_appointment(handler)
        
        mock_conn.execute.assert_called_once()
        args, _ = mock_conn.execute.call_args
        self.assertIn("UPDATE appointments SET status = 'cancelled'", args[0])
        self.assertTrue(handler.redirect_path.startswith("/appointments?msg="))

if __name__ == "__main__":
    unittest.main()
