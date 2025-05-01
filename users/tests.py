from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(username='testuser', password='pass')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('pass'))

class UserAuthTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='authuser', password='pass')
        self.client = APIClient()

    def test_login(self):
        logged_in = self.client.login(username='authuser', password='pass')
        self.assertTrue(logged_in)
        # Logout and test login API endpoint if implemented
        self.client.logout()
        # If you have a login API endpoint, test it here (example):
        # response = self.client.post('/api/auth/login/', {'username': 'authuser', 'password': 'pass'})
        # self.assertEqual(response.status_code, 200)
