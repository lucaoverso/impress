import unittest
from unittest.mock import patch

from fastapi import HTTPException

from modules.users.schemas import ProfileUpdateIn
from modules.users.service import update_own_profile


class UsersServiceTests(unittest.TestCase):
    @patch("modules.users.service.repository.update_profile", return_value=True)
    @patch("modules.users.service.repository.email_belongs_to_another_user", return_value=False)
    def test_updates_only_editable_profile_fields(self, _email_exists, update_profile):
        payload = ProfileUpdateIn(nome="  Ana   Silva  ", email="ANA@ESCOLA.COM")

        update_own_profile({"id": 7, "cargo": "PROFESSOR"}, payload)

        update_profile.assert_called_once_with(
            7, "Ana Silva", "ana@escola.com", password_hash=None, nt_hash=None
        )

    @patch("modules.users.service.repository.email_belongs_to_another_user", return_value=True)
    def test_rejects_email_used_by_another_user(self, _email_exists):
        payload = ProfileUpdateIn(nome="Ana Silva", email="ana@escola.com")

        with self.assertRaises(HTTPException) as raised:
            update_own_profile({"id": 7}, payload)

        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
