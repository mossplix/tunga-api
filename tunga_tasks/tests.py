
from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient
from tunga_auth.models import USER_TYPE_PROJECT_OWNER, USER_TYPE_DEVELOPER
from tunga_tasks.models import Task, Participation


class APITaskTestCase(APITestCase):

    def setUp(self):
        self.project_owner = get_user_model().objects.create_user(
            'project_owner', 'po@example.com', 'secret', **{'type': USER_TYPE_PROJECT_OWNER})
        self.developer = get_user_model().objects.create_user(
            'developer', 'developer@example.com', 'secret', **{'type': USER_TYPE_DEVELOPER})
        self.admin = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'secret')

        self.factory = RequestFactory()

    def test_create_task(self):
        """
        Only project owners and admins can create tasks
        """
        url = reverse('task-list')
        data = {'title': 'Task 1', 'skills': 'Django, React.js', 'fee': 10}

        self.client.force_authenticate(user=None)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.developer)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.project_owner)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data['title'] = 'Task 2'
        data['participation'] = [{'user': self.developer.id}]
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['participation']), 1)
        self.assertEqual(response.data['participation'][0]['user'], self.developer.id)

        data['title'] = 'Task 3'
        data.update({'participants': [self.developer.id], 'assignee': self.developer.id})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['participation']), 1)
        self.assertEqual(response.data['participation'][0]['user'], self.developer.id)
        self.assertTrue(response.data['participation'][0]['assignee'])

    def test_update_task(self):
        """
        Only the task creator or admin can update tasks
        """
        task = Task.objects.create(**{'title': 'Task 1', 'skills': 'Django, React.js', 'fee': 10, 'user': self.project_owner})

        url = reverse('task-detail', args=[task.id])
        data = {'title': 'Task 1 Edit', 'fee': 15}

        self.client.force_authenticate(user=None)
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.developer)
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.project_owner)
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        participation_data = {'participation': [{'user': self.developer.id}]}
        response = self.client.patch(url, participation_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['participation']), 1)
        self.assertEqual(response.data['participation'][0]['user'], self.developer.id)

        response = self.client.patch(url, {'participants': [self.developer.id], 'assignee': self.developer.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['participation']), 1)
        self.assertEqual(response.data['participation'][0]['user'], self.developer.id)
        self.assertTrue(response.data['participation'][0]['assignee'])

        self.client.force_authenticate(user=self.developer)
        response = self.client.patch(url, {'participants': [self.developer.id], 'confirmed_participants': [self.developer.id]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['participation']), 1)
        self.assertEqual(response.data['participation'][0]['user'], self.developer.id)
        self.assertTrue(response.data['participation'][0]['accepted'])

        response = self.client.patch(url, {'participants': [self.developer.id], 'rejected_participants': [self.developer.id]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['participation']), 1)
        self.assertEqual(response.data['participation'][0]['user'], self.developer.id)
        self.assertFalse(response.data['participation'][0]['accepted'])

        task.user = self.admin
        task.save()

        data = {'title': 'Task 1 Edit 2', 'fee': 20}
        self.client.force_authenticate(user=self.project_owner)
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

