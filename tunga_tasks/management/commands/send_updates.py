#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.core.management import BaseCommand
from django.db import transaction
from tunga_tasks.tasks import send_update_email
from tunga_tasks.models import Milestone
import datetime
from time import sleep

class Command(BaseCommand):
    help = """ Send out Update
    """

    def sendall(self):

        try:
            now = datetime.datetime.now()
            tosend = Milestone.objects.filter(due_date__gte=now,type__in=[1,3]).exclude(update_sent=True)
            send_update_email.delay(tosend)

        except Exception, exc:
            print exc

    def handle(self, **options):
        while (True):
            self.sendall()
            sleep(3600)