from django.test import TestCase
from tunga_auth.models import TungaUser
from actstream.models import Action, Follow
from tunga_comments.models import Comment
from tunga_tasks.models import Application, Milestone, Participation, SavedTask, Task, TaskRequest
from djcelery.models import CrontabSchedule, IntervalSchedule, PeriodicTask, PeriodicTasks, TaskMeta, TaskSetMeta, TaskState, WorkerState


# Create your tests here.
class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        user,_ = TungaUser.objects.get_or_create(title="milestone_1")
        milestone1 =  Milestone.objects.create(title="d",task=t[0])
        """
        Create a default survey for all test cases
        """

    def test_milestones(self):
        pass


