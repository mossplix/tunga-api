import json

from django.shortcuts import render, redirect
from dry_rest_permissions.generics import DRYObjectPermissions
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework import status
from django.http import Http404

from tunga_tasks.filterbackends import TaskFilterBackend
from tunga_tasks.filters import TaskFilter, ApplicationFilter, ParticipationFilter, TaskRequestFilter, SavedTaskFilter
from tunga_tasks.models import Task, Application, Participation, TaskRequest, SavedTask,Milestone,TaskUpdate,TaskMilestone
from tunga_tasks.serializers import TaskSerializer, ApplicationSerializer, ParticipationSerializer, \
    TaskRequestSerializer, SavedTaskSerializer,MilestoneSerializer,TaskMilestoneSerializer,TaskUpdateSerializer
from tunga_utils.filterbackends import DEFAULT_FILTER_BACKENDS


class TaskViewSet(viewsets.ModelViewSet):
    """
    Task Resource
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, DRYObjectPermissions]
    filter_class = TaskFilter
    filter_backends = DEFAULT_FILTER_BACKENDS + (TaskFilterBackend,)
    search_fields = ('title', 'description', 'skills__name')

    @detail_route(
        methods=['get'], url_path='meta',
        permission_classes=[IsAuthenticated]
    )
    def meta(self, request, pk=None):
        """
        Get task meta data
        """
        task = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, task)

        participation = json.dumps(task.meta_participation)
        payment_meta = task.meta_payment
        payment_meta['task_url'] = '%s://%s%s' % (request.scheme, request.get_host(), payment_meta['task_url'])
        payment = json.dumps(payment_meta)
        return Response({'task': task.id, 'participation': participation, 'payment': payment})


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    Task Application Resource
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_class = ApplicationFilter
    search_fields = ('task__title', 'task__skills__name', '^user__username', '^user__first_name', '^user__last_name')


class ParticipationViewSet(viewsets.ModelViewSet):
    """
    Task Participation Resource
    """
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticated]
    filter_class = ParticipationFilter
    search_fields = ('task__title', 'task__skills__name', '^user__username', '^user__first_name', '^user__last_name')


class TaskRequestViewSet(viewsets.ModelViewSet):
    """
    Task Request Resource
    """
    queryset = TaskRequest.objects.all()
    serializer_class = TaskRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_class = TaskRequestFilter
    search_fields = ('task__title', 'task__skills__name', '^user__username', '^user__first_name', '^user__last_name')


class SavedTaskViewSet(viewsets.ModelViewSet):
    """
    Saved Task Resource
    """
    queryset = SavedTask.objects.all()
    serializer_class = SavedTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_class = SavedTaskFilter
    search_fields = ('task__title', 'task__skills__name', '^user__username', '^user__first_name', '^user__last_name')


def task_webscrapers(request, pk=None):
    try:
        task = Task.objects.get(id=pk)
        participation = json.dumps(task.meta_participation)
        payment_meta = task.meta_payment
        payment_meta['task_url'] = '%s://%s%s' % (request.scheme, request.get_host(), payment_meta['task_url'])
        payment = json.dumps(payment_meta)
        return render(request, 'tunga/index.html', {'task': task, 'participation': participation, 'payment': payment})
    except (Task.DoesNotExist, Task.MultipleObjectsReturned):
        return redirect('/task/')

class TaskMilestonesViewSet(viewsets.ModelViewSet):
    """
    Task Milestone  Resource
    """
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = [IsAuthenticated, DRYObjectPermissions]

    @detail_route(
        methods=['get'], url_path='meta',
        permission_classes=[IsAuthenticated]
    )
    def meta(self, request, pk=None):
        """
        Get task meta data
        """
        task = get_object_or_404(Task, pk=pk)
        milestones = task.milestones.all()
        return Response({'milestones': milestones})



class ResourceDoesNotExist(APIException):
    status_code = 404


class MilestoneDetailEndpoint(APIView):
    permission_classes = [IsAuthenticated, DRYObjectPermissions]

    def get_object(self, pk):
        try:
            return Milestone.objects.get(pk=pk)
        except Milestone.DoesNotExist:
            raise Http404


    def get(self, request,pk):
        """
        Retrieve a milestone
        ````````````````````````
        Return details on an individual milestone
        :param string id: the if of the milestone
        """
        milestone  = self.get_object(pk)
        serializer = MilestoneSerializer(milestone)
        return Response(serializer.data)


    def put(self, request, pk):
        """
        Update an milestone
        ``````````````````````

        Update various attributes and configurable settings for the given
        organization.

        :pparam number id: id of the milestone

        """
        milestone  = self.get_object(pk)
        serializer = MilestoneSerializer(milestone, data=request.DATA,
                                            partial=True)
        if serializer.is_valid():
            milestone = serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, pk):
        """
        Delete a milestone
        ``````````````````````
        :pparam integer id: the id of the milestone
        """
        milestone = self.get_object(pk)
        milestone.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MilestoneIndexEndpoint(APIView):
    permission_classes = [IsAuthenticated, DRYObjectPermissions]

    def get_task(self, task_id):
        try:
            return Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            raise Http404


    def get(self, request,task_id):
        """
        List of Milestones For Task
        ```````````````````````
        Return a list of milestones for task
        """
        task = self.get_task(task_id)
        milestones = task.milestones.all()
        serializer = MilestoneSerializer(milestones, many=True)
        return Response(serializer.data)


    def post(self, request,task_id):
        """
        Create a New Milestone
        `````````````````````````
        """
        task = self.get_task(task_id)

        serializer =  MilestoneSerializer(data=request.DATA)

        if serializer.is_valid():
            milestone = serializer.save()
            task_milestone = TaskMilestone.objects.create(task=task,milestone=milestone)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskUpdateIndexEndpoint(APIView):
    permission_classes = [IsAuthenticated, DRYObjectPermissions]

    def get_task(self, task_id):
        try:
            return Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            raise Http404


    def get(self, request,task_id):
        """
        List of task updates  For Task
        ```````````````````````
        Return a list of milestones for task
        """
        task = self.get_task(task_id)
        task_updates = TaskUpdate.objects.filter(task_id=task_id)
        milestone = request.GET.get('milestone')
        if milestone:
            task_updates = task_updates.update(tags=milestone)
        serializer = TaskUpdateSerializer(task_updates, many=True)
        return Response(serializer.data)


    def post(self, request,task_id):
        """
        Create a New Milestone
        `````````````````````````
        """
        task = self.get_task(task_id)
        data=request.data
        data["task"] = task

        serializer =  MilestoneSerializer(data=request.data)

        if serializer.is_valid():
            milestone = serializer.save()
            task_update = TaskUpdate.objects.create(task=task,milestone=milestone)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)