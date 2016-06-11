from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _
from dry_rest_permissions.generics import allow_staff_or_superuser
import tagulous

from tunga import settings


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField()
    tags = tagulous.models.TagField( blank=True,null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        msg = self.body
        msg = msg and len(msg) > 100 and msg[:100] + '...' or msg
        return '%s - %s' % (self.user.get_short_name() or self.user.username, msg)

    class Meta:
        ordering = ['-created_at']

    @allow_staff_or_superuser
    def has_object_write_permission(self, request):
        return request.user == self.user
