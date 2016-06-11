from django.contrib.auth import get_user_model
from django.db.models.query_utils import Q
from rest_framework import serializers

from tunga.settings.base import TUNGA_SHARE_PERCENTAGE
from tunga_auth.serializers import SimpleUserSerializer, UserSerializer
from tunga_tasks.emails import send_new_task_email, send_task_application_not_accepted_email
from tunga_tasks.models import Task, Application, Participation, TaskRequest, SavedTask,TaskUpdate,Milestone,TaskMilestone,UPDATE_SCHEDULE_DAILY
from tunga_utils.serializers import ContentTypeAnnotatedSerializer, DetailAnnotatedSerializer, SkillSerializer, \
    CreateOnlyCurrentUserDefault, SimpleUserSerializer


class SimpleTaskSerializer(ContentTypeAnnotatedSerializer):
    user = SimpleUserSerializer()

    class Meta:
        model = Task
        fields = ('id', 'user', 'title', 'currency', 'fee', 'closed', 'paid', 'display_fee')

class MilestoneSerializer(serializers.HyperlinkedModelSerializer):
    task = SimpleTaskSerializer()
    class Meta:
        model = Milestone


class SimpleApplicationSerializer(ContentTypeAnnotatedSerializer):
    user = SimpleUserSerializer()

    class Meta:
        model = Application
        exclude = ('created_at',)


class SimpleParticipationSerializer(ContentTypeAnnotatedSerializer):
    user = SimpleUserSerializer()

    class Meta:
        model = Participation
        exclude = ('created_at',)


class TaskDetailsSerializer(ContentTypeAnnotatedSerializer):
    user = SimpleUserSerializer()
    skills = SkillSerializer(many=True)
    assignee = serializers.SerializerMethodField(required=False, read_only=True)
    applications = SimpleApplicationSerializer(many=True, source='application_set')
    participation = SimpleParticipationSerializer(many=True, source='participation_set')
    milestones = SimpleParticipationSerializer(many=True, source='milestone_set')

    class Meta:
        model = Task
        fields = ('user', 'skills', 'assignee', 'applications', 'participation','milestones')

    def get_assignee(self, obj):
        try:
            assignee = obj.participation_set.get((Q(accepted=True) | Q(responded=False)), assignee=True)
            return {
                'user': SimpleUserSerializer(assignee.user).data,
                'accepted': assignee.accepted,
                'responded': assignee.responded
            }
        except:
            return None


class TaskSerializer(ContentTypeAnnotatedSerializer, DetailAnnotatedSerializer):
    user = serializers.PrimaryKeyRelatedField(required=False, read_only=True, default=CreateOnlyCurrentUserDefault())
    display_fee = serializers.SerializerMethodField(required=False, read_only=True)
    excerpt = serializers.CharField(required=False, read_only=True)
    skills = serializers.CharField(required=True, allow_blank=True, allow_null=True)
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    can_apply = serializers.SerializerMethodField(read_only=True, required=False)
    can_save = serializers.SerializerMethodField(read_only=True, required=False)
    is_participant = serializers.SerializerMethodField(read_only=True, required=False)
    my_participation = serializers.SerializerMethodField(read_only=True, required=False)
    summary = serializers.CharField(read_only=True, required=False)
    assignee = serializers.SerializerMethodField(required=False, read_only=True)
    participants = serializers.PrimaryKeyRelatedField(many=True, queryset=get_user_model().objects.all(), required=False, write_only=True)
    milestones =  MilestoneSerializer(many=True)
    open_applications = serializers.SerializerMethodField(required=False, read_only=True)
    update_schedule_display = serializers.SerializerMethodField(required=False, read_only=True)

    class Meta:
        model = Task
        exclude = ('applicants',)
        read_only_fields = ('created_at',)
        details_serializer = TaskDetailsSerializer

    def create(self, validated_data):
        skills = None
        participants = None
        if 'skills' in validated_data:
            skills = validated_data.pop('skills')
        if 'participants' in validated_data:
            participants = validated_data.pop('participants')
        instance = super(TaskSerializer, self).create(validated_data)
        self.save_skills(instance, skills)
        self.save_participants(instance, participants)


        # Triggered here instead of in the post_save signal to allow skills to be attached first
        # TODO: Consider moving this trigger
        send_new_task_email(instance)
        return instance

    def update(self, instance, validated_data):
        initial_apply = instance.apply
        skills = None
        participants = None
        if 'skills' in validated_data:
            skills = validated_data.pop('skills')
        if 'participants' in validated_data:
            participants = validated_data.pop('participants')
        instance = super(TaskSerializer, self).update(instance, validated_data)
        self.save_skills(instance, skills)
        self.save_participants(instance, participants)

        # TODO: Consider moving this trigger
        if initial_apply and not instance.apply:
            send_task_application_not_accepted_email(instance)
        return instance

    def save_skills(self, task, skills):
        if skills is not None:
            task.skills = skills
            task.save()

    def save_participants(self, task, participants):
        if participants:
            assignee = self.initial_data.get('assignee', None)
            confirmed_participants = self.initial_data.get('confirmed_participants', None)
            rejected_participants = self.initial_data.get('rejected_participants', None)
            created_by = task.user
            request = self.context.get("request", None)
            if request:
                user = getattr(request, "user", None)
                if user:
                    created_by = user

            changed_assignee = False
            for user in participants:
                try:
                    defaults = {'created_by': created_by}
                    if assignee:
                        defaults['assignee'] = bool(user.id == assignee)
                    if rejected_participants and user.id in rejected_participants:
                        defaults['accepted'] = False
                        defaults['responded'] = True
                    if confirmed_participants and user.id in confirmed_participants:
                        defaults['accepted'] = True
                        defaults['responded'] = True

                    Participation.objects.update_or_create(task=task, user=user, defaults=defaults)
                    if user.id == assignee:
                        changed_assignee = True
                except:
                    pass
            if assignee and changed_assignee:
                Participation.objects.exclude(user__id=assignee).filter(task=task).update(assignee=False)

    def __get_current_user(self):
        request = self.context.get("request", None)
        if request:
            return getattr(request, "user", None)
        return None

    def get_display_fee(self, obj):
        user = self.__get_current_user()
        amount = None
        if user and user.is_developer:
            amount = obj.fee*(1 - TUNGA_SHARE_PERCENTAGE*0.01)
        return obj.display_fee(amount=amount)


    def get_can_apply(self, obj):
        if obj.closed or not obj.apply:
            return False
        request = self.context.get("request", None)
        if request:
            user = getattr(request, "user", None)
            if user:
                if obj.user == user:
                    return False
                return obj.applicants.filter(id=user.id).count() == 0 and \
                       obj.participation_set.filter(user=user).count() == 0
        return False

    def get_can_save(self, obj):
        request = self.context.get("request", None)
        if request:
            user = getattr(request, "user", None)
            if user:
                if obj.user == user:
                    return False
                return obj.savedtask_set.filter(user=user).count() == 0
        return False

    def get_is_participant(self, obj):
        request = self.context.get("request", None)
        if request:
            user = getattr(request, "user", None)
            if user:
                return obj.participation_set.filter((Q(accepted=True) | Q(responded=False)), user=user).count() == 1
        return False

    def get_my_participation(self, obj):
        request = self.context.get("request", None)
        if request:
            user = getattr(request, "user", None)
            if user:
                try:
                    participation = obj.participation_set.get(user=user)
                    return {
                        'id': participation.id,
                        'user': participation.user.id,
                        'assignee': participation.assignee,
                        'accepted': participation.accepted,
                        'responded': participation.responded
                    }
                except:
                    pass
        return None

    def get_assignee(self, obj):
        try:
            assignee = obj.participation_set.get((Q(accepted=True) | Q(responded=False)), assignee=True)
            return {
                'user': assignee.user.id,
                'accepted': assignee.accepted,
                'responded': assignee.responded
            }
        except:
            return None

    def get_open_applications(self, obj):
        return obj.application_set.filter(responded=False).count()

    def get_update_schedule_display(self, obj):
        if obj.update_interval and obj.update_interval_units:
            if obj.update_interval == 1 and obj.update_interval_units == UPDATE_SCHEDULE_DAILY:
                return 'Daily'
            interval_units = str(obj.get_update_interval_units_display()).lower()
            if obj.update_interval == 1:
                return 'Every %s' % interval_units
            return 'Every %s %ss' % (obj.update_interval, interval_units)
        return None


class ApplicationDetailsSerializer(SimpleApplicationSerializer):
    user = UserSerializer()
    task = SimpleTaskSerializer()

    class Meta:
        model = Application
        fields = ('user', 'task')


class ApplicationSerializer(ContentTypeAnnotatedSerializer, DetailAnnotatedSerializer):
    user = serializers.PrimaryKeyRelatedField(required=False, read_only=True, default=CreateOnlyCurrentUserDefault())

    class Meta:
        model = Application
        details_serializer = ApplicationDetailsSerializer
        extra_kwargs = {
            'pitch': {'required': True, 'allow_blank': False, 'allow_null': False},
            'hours_needed': {'required': True, 'allow_null': False},
            'hours_available': {'required': True, 'allow_null': False},
            'deliver_at': {'required': True, 'allow_null': False}
        }


class ParticipationDetailsSerializer(SimpleParticipationSerializer):
    created_by = SimpleUserSerializer()
    task = SimpleTaskSerializer()

    class Meta:
        model = Participation
        fields = ('user', 'task', 'created_by')


class ParticipationSerializer(ContentTypeAnnotatedSerializer, DetailAnnotatedSerializer):
    created_by = serializers.PrimaryKeyRelatedField(required=False, read_only=True, default=CreateOnlyCurrentUserDefault())

    class Meta:
        model = Participation
        exclude = ('created_at',)
        details_serializer = ParticipationDetailsSerializer


class TaskRequestDetailsSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer()
    task = SimpleTaskSerializer()

    class Meta:
        model = TaskRequest
        fields = ('user', 'task')


class TaskRequestSerializer(ContentTypeAnnotatedSerializer, DetailAnnotatedSerializer):
    user = serializers.PrimaryKeyRelatedField(required=False, read_only=True, default=CreateOnlyCurrentUserDefault())

    class Meta:
        model = TaskRequest
        exclude = ('created_at',)
        details_serializer = TaskRequestDetailsSerializer


class SavedTaskDetailsSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer()
    task = SimpleTaskSerializer()

    class Meta:
        model = SavedTask
        fields = ('user', 'task')


class SavedTaskSerializer(ContentTypeAnnotatedSerializer, DetailAnnotatedSerializer):
    user = serializers.PrimaryKeyRelatedField(required=False, read_only=True, default=CreateOnlyCurrentUserDefault())

    class Meta:
        model = SavedTask
        exclude = ('created_at',)
        details_serializer = SavedTaskDetailsSerializer


class TaskUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskUpdate

    def save(self):
        tu = super(TaskUpdateSerializer, self).save()
        return tu

class TaskMilestoneSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskMilestone

    def save(self):
        tm = super(TaskMilestoneSerializer, self).save()
        return tm



