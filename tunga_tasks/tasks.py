from celery.task import Task, task
from celery.registry import tasks
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

@periodic_task(run_every=(crontab(minute='*/15')), name="some_task", ignore_result=True)
def send_milestones():
    send_reminder_email()


@task
def send_email(task):

    subject=""
    message = render_to_string(
                'tunga/email/email_new_task.txt',
                {
                    'owner': instance.user,
                    'task': instance,
                    'task_url': 'http://tunga.io/task/%s/' % instance.id
                }
            )
    EmailMessage(subject, message, to=to).send()


def send_reminder_email():
    pass