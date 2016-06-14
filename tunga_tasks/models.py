# encoding=utf8
from __future__ import unicode_literals

import re
import urllib

import requests
import datetime
import tagulous.models
import tagulous
from django.db import models
from django.db.models.query_utils import Q
from django.template.defaultfilters import floatformat
from django.utils.html import strip_tags
from dry_rest_permissions.generics import allow_staff_or_superuser
from django.template.defaultfilters import slugify


from tunga import settings
from tunga.settings.base import TUNGA_SHARE_PERCENTAGE, TUNGA_SHARE_EMAIL
from tunga_auth.models import USER_TYPE_DEVELOPER, USER_TYPE_PROJECT_OWNER
from tunga_profiles.models import Skill, Connection
from tunga_settings.models import VISIBILITY_DEVELOPER, VISIBILITY_MY_TEAM, VISIBILITY_CUSTOM, VISIBILITY_CHOICES
from tunga_comments.models import Comment
from django.db.models.signals import post_save
from .tasks import send_owner_email
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator,MinValueValidator


CURRENCY_EUR = 'EUR'
CURRENCY_USD = 'USD'

CURRENCY_CHOICES = (
    (CURRENCY_EUR, 'EUR'),
    (CURRENCY_USD, 'USD')
)

CURRENCY_SYMBOLS = {
    'EUR': '€',
    'USD': '$'
}

UPDATE_SCHEDULE_HOURLY = 1
UPDATE_SCHEDULE_DAILY = 2
UPDATE_SCHEDULE_WEEKLY = 3
UPDATE_SCHEDULE_MONTHLY = 4
UPDATE_SCHEDULE_QUATERLY = 5
UPDATE_SCHEDULE_ANNUALLY = 6

UPDATE_SCHEDULE_CHOICES = (
    (UPDATE_SCHEDULE_HOURLY, 'Hour'),
    (UPDATE_SCHEDULE_DAILY, 'Day'),
    (UPDATE_SCHEDULE_WEEKLY, 'Week'),
    (UPDATE_SCHEDULE_MONTHLY, 'Month'),
    (UPDATE_SCHEDULE_QUATERLY, 'Quarter'),
    (UPDATE_SCHEDULE_ANNUALLY, 'Annual')
)


TASK_REQUEST_CLOSE = 1
TASK_REQUEST_PAY = 2

TASK_REQUEST_CHOICES = (
    (TASK_REQUEST_CLOSE, 'Close Request'),
    (TASK_REQUEST_PAY, 'Payment Request')
)


class Task(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='tasks_created', on_delete=models.DO_NOTHING)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=1000, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    fee = models.BigIntegerField()
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default=CURRENCY_CHOICES[0][0])
    deadline = models.DateTimeField(blank=True, null=True)
    skills = tagulous.models.TagField(Skill, blank=True)
    visibility = models.PositiveSmallIntegerField(choices=VISIBILITY_CHOICES, default=VISIBILITY_CHOICES[0][0])
    update_interval = models.PositiveIntegerField(blank=True, null=True)
    update_interval_units = models.PositiveSmallIntegerField(choices=UPDATE_SCHEDULE_CHOICES, blank=True, null=True)
    apply = models.BooleanField(default=True)
    closed = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    applicants = models.ManyToManyField(
            settings.AUTH_USER_MODEL, through='Application', through_fields=('task', 'user'),
            related_name='task_applications', blank=True)
    participants = models.ManyToManyField(
            settings.AUTH_USER_MODEL, through='Participation', through_fields=('task', 'user'),
            related_name='task_participants', blank=True)
    milestones = models.ManyToManyField('Milestone',
         blank = True,
         related_name='task_milestones',through='TaskMilestone',through_fields=('task', 'milestone')
         )
    satisfaction = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    apply_closed_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return self.summary

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'title', 'fee')

    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return True

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        if self.has_object_update_permission(request):
            return True
        if self.visibility == VISIBILITY_DEVELOPER:
            return request.user.type == USER_TYPE_DEVELOPER
        elif self.visibility == VISIBILITY_MY_TEAM:
            return bool(
                Connection.objects.exclude(accepted=False).filter(
                    Q(from_user=self.user, to_user=request.user) | Q(from_user=request.user, to_user=self.user)
                ).count()
            )
        elif self.visibility == VISIBILITY_CUSTOM:
            return self.participation_set.filter((Q(accepted=True) | Q(responded=False)), user=request.user).count()
        return False

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return request.user.type == USER_TYPE_PROJECT_OWNER

    @staticmethod
    @allow_staff_or_superuser
    def has_update_permission(request):
        return True

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user

    @allow_staff_or_superuser
    def has_object_update_permission(self, request):
        if self.has_object_write_permission(request):
            return True
        # Participants can edit participation info directly on task object
        if request.method in ['PUT', 'PATCH']:
            allowed_keys = ['assignee', 'participants', 'confirmed_participants', 'rejected_participants']
            if not [x for x in request.data.keys() if not x in allowed_keys]:
                return self.participation_set.filter((Q(accepted=True) | Q(responded=False)), user=request.user).count()
        return False

    def display_fee(self, amount=None):
        if amount is None:
            amount = self.fee
        if self.currency in CURRENCY_SYMBOLS:
            return '%s%s' % (CURRENCY_SYMBOLS[self.currency], floatformat(amount, arg=-2))
        return amount

    @property
    def summary(self):
        return '%s - Fee: %s' % (self.title, self.display_fee())

    @property
    def excerpt(self):
        try:
            return strip_tags(self.description).strip()
        except:
            return None

    def get_default_participation(self):
        tags = ['tunga.io', 'tunga']
        if self.skills:
            tags.extend(str(self.skills).split(','))
        return {
            'type': 'payment', 'language': 'EN', 'title': self.summary, 'description': self.excerpt or self.summary,
            'keywords': tags, 'participants': [
                {'id': 'mailto:%s' % TUNGA_SHARE_EMAIL, 'role': 'owner', 'share': '{share}%'.format(**{'share': TUNGA_SHARE_PERCENTAGE})}
            ]
        }

    def mobbr_participation(self, check_only=False):
        participation_meta = self.get_default_participation()
        if not self.url:
            return participation_meta, False

        mobbr_info_url = '%s?url=%s' % ('https://api.mobbr.com/api_v1/uris/info', urllib.quote_plus(self.url))
        r = requests.get(mobbr_info_url, **{'headers': {'Accept': 'application/json'}})
        has_script = False
        if r.status_code == 200:
            response = r.json()
            task_script = response['result']['script']
            for meta_key in participation_meta:
                if meta_key == 'keywords':
                    if isinstance(task_script[meta_key], list):
                        participation_meta[meta_key].extend(task_script[meta_key])
                elif meta_key == 'participants':
                    if isinstance(task_script[meta_key], list):
                        absolute_shares = []
                        relative_shares = []
                        absolute_participants = []
                        relative_participants = []

                        for key, participant in enumerate(task_script[meta_key]):
                            if re.match(r'\d+%$', participant['share']):
                                share = int(participant['share'].replace("%", ""))
                                if share > 0:
                                    absolute_shares.append(share)
                                    new_participant = participant
                                    new_participant['share'] = share
                                    absolute_participants.append(new_participant)
                            else:
                                share = int(participant['share'])
                                if share > 0:
                                    relative_shares.append(share)
                                    new_participant = participant
                                    new_participant['share'] = share
                                    relative_participants.append(new_participant)

                        additional_participants = []
                        total_absolutes = sum(absolute_shares)
                        total_relatives = sum(relative_shares)
                        if total_absolutes >= 100 or total_relatives == 0:
                            additional_participants = absolute_participants
                        elif total_absolutes == 0:
                            additional_participants = relative_participants
                        else:
                            additional_participants = absolute_participants
                            for participant in relative_participants:
                                share = int(round(((participant['share']*(100-total_absolutes))/total_relatives), 0))
                                if share > 0:
                                    new_participant = participant
                                    new_participant['share'] = share
                                    additional_participants.append(new_participant)
                        if len(additional_participants):
                            participation_meta[meta_key].extend(additional_participants)
                            has_script = True
                elif meta_key in task_script:
                    participation_meta[meta_key] = task_script[meta_key]
        return participation_meta, has_script

    @property
    def meta_participation(self):
        participation_meta, has_script = self.mobbr_participation()
        # TODO: Update local participation script to use defined shares
        if not has_script:
            participants = self.participation_set.filter(accepted=True).order_by('share')
            total_shares = 100 - TUNGA_SHARE_PERCENTAGE
            num_participants = participants.count()
            for participant in participants:
                participation_meta['participants'].append(
                    {
                        'id': 'mailto:%s' % participant.user.email,
                        'role': participant.role,
                        'share': int(total_shares/num_participants)
                    }
                )
        return participation_meta

    @property
    def meta_payment(self):
        return {'task_url': '/task/%s/' % self.id, 'amount': self.fee, 'currency': self.currency}

    @property
    def skills_list(self):
        return str(self.skills)


class Application(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    accepted = models.BooleanField(default=False)
    responded = models.BooleanField(default=False)
    pitch = models.CharField(max_length=1000, blank=True, null=True)
    hours_needed = models.PositiveIntegerField(blank=True, null=True)
    hours_available = models.PositiveIntegerField(blank=True, null=True)
    deliver_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s - %s' % (self.user.get_short_name() or self.user.username, self.task.title)

    class Meta:
        unique_together = ('user', 'task')

    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return True

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return self.has_object_update_permission(request)

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return request.user.type == USER_TYPE_DEVELOPER

    @staticmethod
    @allow_staff_or_superuser
    def has_update_permission(request):
        return True

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user

    @allow_staff_or_superuser
    def has_object_update_permission(self, request):
        # Task owner can update applications
        return request.user == self.user or request.user == self.task.user


class Participation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    accepted = models.BooleanField(default=False)
    responded = models.BooleanField(default=False)
    assignee = models.BooleanField(default=False)
    role = models.CharField(max_length=100, default='Developer')
    share = models.IntegerField(blank=True, null=True)
    satisfaction = models.SmallIntegerField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='participants_added')
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s - %s' % (self.user.get_short_name() or self.user.username, self.task.title)

    class Meta:
        unique_together = ('user', 'task')
        verbose_name_plural = 'participation'

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return self.task.has_object_read_permission(request)

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user or request.user == self.task.user


class TaskRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    type = models.PositiveSmallIntegerField(choices=TASK_REQUEST_CHOICES, help_text=','.join(['%s - %s' % (item[0], item[1]) for item in TASK_REQUEST_CHOICES]))
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s - %s' % (self.get_type_display(), self.task.title)

    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return True

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return self.task.has_object_read_permission(request)

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return request.user.type == USER_TYPE_DEVELOPER

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user


class SavedTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s - %s' % (self.user.get_short_name() or self.user.username, self.task.title)


    @staticmethod
    @allow_staff_or_superuser
    def has_read_permission(request):
        return True

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        return request.user == self.user

    @staticmethod
    @allow_staff_or_superuser
    def has_write_permission(request):
        return request.user.type == USER_TYPE_DEVELOPER

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user

class Milestone(models.Model):
    CLOSED = 3
    ACTIVE = 2
    OVERDUE = 1
    COMPLETED = 0
    title = models.CharField(max_length=50)
    slug = models.SlugField(editable=False, null=True, blank=True, max_length=200)
    task = models.ForeignKey(Task,on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    due_date = models.DateTimeField(blank=True, null=True)
    state = models.IntegerField(choices=((COMPLETED,"Completed"),(OVERDUE,"Overdue"),( ACTIVE,"active"),(CLOSED,"closed")),default=2,)
    type = models.IntegerField(choices=((1,"interval"),(2,"update"),( 3,"update_request"),( 4,"start")),default=2,)
    description = models.TextField()
    percentage_done = models.PositiveIntegerField(validators=[MaxValueValidator(100),MinValueValidator(0)],null=True,blank=True)
    order = models.SmallIntegerField(default=0)
    update_sent = models.NullBooleanField()
    tags = tagulous.models.TagField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


    def overdue(self):
        pass

    def due_thisweek(self):
        pass

    def due_thismonth(self):
        pass

class TaskUpdate(models.Model):
    milestone = models.ForeignKey(Milestone,null=True,blank=True)
    status = models.CharField(max_length=50,default="on schedule")
    accomplished  = models.CharField(max_length=400,blank=True,null=True)
    percentage_done = models.PositiveIntegerField(validators=[MaxValueValidator(100),MinValueValidator(0)],null=True,blank=True)
    next_steps = models.CharField(max_length=400,blank=True,null=True)
    other_remarks =  models.CharField(max_length=400,blank=True,null=True)
    comments = GenericRelation(Comment,null=True, blank=True, default=None)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)




class TaskUpdateFile(models.Model):
    name = models.CharField(max_length=200)
    task_update = models.ForeignKey(TaskUpdate,related_name="files")
    file = models.FileField(upload_to="task_update_files")
    size = models.PositiveIntegerField(validators=[MaxValueValidator(20000),MinValueValidator(1)]) #20 mbs
    type = models.CharField(max_length=64)



class TaskMilestone(models.Model):
    task = models.ForeignKey(Task,on_delete=models.CASCADE)
    milestone = models.ForeignKey(Milestone,on_delete=models.CASCADE)





def handle_task_update(sender, instance, created, **kwargs):

    send_owner_email.delay(instance.pk)

def create_initial_milestones(sender, instance, created, **kwargs):
    if created:

        milestone = Milestone.objects.create(title="Task Created",type=4,task=instance,order=0,description=str(instance.created_at),user=instance.user,due_date=instance.created_at)
        TaskMilestone.objects.create(milestone=milestone,task=instance)

    if instance.participants.all().exists():
        devs =  " ".join(instance.participants.values_list("first_name",flat=True))
        milestone,_ = Milestone.objects.get_or_create(title="Dev(s) Selected",order=1,task=instance,description=devs,user=instance.user,due_date=instance.created_at)
        TaskMilestone.objects.get_or_create(milestone=milestone,task=instance)

    if instance.deadline:
        milestone,_ = Milestone.objects.get_or_create(title="Deadline",task=instance,description=str(instance.deadline),user=instance.user,due_date=instance.deadline)
        TaskMilestone.objects.create(milestone=milestone,task=instance)
    if instance.update_interval and instance.deadline and instance.participation.all().exists():

        last_milestone = Milestone.objects.get(order=1)
        seconds = (instance.deadline - last_milestone.created).total_seconds()

        interval = dict(
            UPDATE_SCHEDULE_HOURLY = 3600,
            UPDATE_SCHEDULE_DAILY = 86400,
            UPDATE_SCHEDULE_WEEKLY = 604800,
            UPDATE_SCHEDULE_MONTHLY = 2592000,
            UPDATE_SCHEDULE_QUATERLY = 7776000,
            UPDATE_SCHEDULE_ANNUALLY = 31536000,

        )
        update_interval = interval(instance.update_interval_units)*instance.update_interval #seconds
        for r in range(update_interval,update_interval,seconds):
            milestone,_ = Milestone.objects.get_or_create(title="Update",task=instance,description=str(instance.deadline),user=instance.user,due_date=(last_milestone.created+datetime.timedelta(seconds=r)))
            TaskMilestone.objects.get_or_create(milestone=milestone,task=instance)


def create_milestones(sender, instance, created, **kwargs):
    if created:
        milestone = Milestone.objects.create(title="Update",task=instance,description="",user=instance.user)
        TaskMilestone.objects.create(milestone=milestone,task=instance)



post_save.connect(create_initial_milestones, sender=Task,weak=False)

post_save.connect(create_milestones, sender=TaskUpdate,weak=False)

post_save.connect(handle_task_update, sender=Task,weak=False)



