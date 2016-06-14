from celery.task import Task, task
from celery.registry import tasks
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


@task
def send_owner_email(task):
    to = task.user.email

    subject="New Task Update"
    message = render_to_string(
                'tunga_tasks/email/email_update.txt',
                {
                    'milestone': ms,

                    'ms_update_url': 'http://tunga.io/task/%s/%s' % (ms.task.id,ms.id)
                }
            )
    EmailMessage(subject, message, to=to).send()


@task
def send_email(ms):

    subject="Please Send Us An Update On Your Task"
    to = ms.user.email
    message = render_to_string(
                'tunga_tasks/email/email_update.txt',
                {
                    'milestone': ms,

                    'ms_update_url': 'http://tunga.io/task/%s/%s' % (ms.task.id,ms.id)
                }
            )
    EmailMessage(subject, message, to=to).send()

@task
def send_update_email(update_list):
    for ms in update_list:
        send_email(ms)
