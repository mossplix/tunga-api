from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query_utils import Q
from django.utils.html import strip_tags
from django.utils.translation import ugettext_lazy as _
from dry_rest_permissions.generics import allow_staff_or_superuser

from tunga import settings
from tunga_profiles.models import Connection


class Message(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_broadcast = models.BooleanField(default=False)
    recipients = models.ManyToManyField(
            settings.AUTH_USER_MODEL, through='Reception', through_fields=('message', 'user'),
            related_name='messages_received', blank=True)
    subject = models.CharField(max_length=100)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return '%s - %s' % (self.user.get_short_name() or self.user.username, self.subject)

    class Meta:
        ordering = ['-created_at']

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        if self.has_object_write_permission(request):
            return True
        if self.is_broadcast:
            return bool(
                Connection.objects.exclude(accepted=False).filter(
                    Q(from_user=self.user, to_user=request.user) | Q(from_user=request.user, to_user=self.user)
                ).count()
            )
        return request.user in self.recipients.all()

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user

    @property
    def excerpt(self):
        return strip_tags(self.body)


class Reception(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return '%s - %s' % (self.user.get_short_name() or self.user.username, self.message.subject)

    class Meta:
        unique_together = ('user', 'message')


class Reply(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='replies')
    is_broadcast = models.BooleanField(default=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s -> %s' % (self.user.get_short_name() or self.user.username, self.body)

    class Meta:
        verbose_name_plural = 'replies'
        ordering = ['-created_at']

    @allow_staff_or_superuser
    def has_object_read_permission(self, request):
        if self.has_object_write_permission(request):
            return True
        if self.is_broadcast:
            return self.message.has_object_read_permission(request)
        return request.user == self.message.user

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user

    @property
    def excerpt(self):
        return strip_tags(self.body)


class Attachment(models.Model):
    file = models.FileField(verbose_name='Attachment', upload_to='attachments/%Y/%m/%d')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.file.name

    class Meta:
        ordering = ['-created_at']

