# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-11 09:38
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import tagulous.models.fields
import tagulous.models.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tunga_tasks', '0012_auto_20160527_1220'),
    ]

    operations = [
        migrations.CreateModel(
            name='_Tagulous_Milestone_tags',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('slug', models.SlugField()),
                ('count', models.IntegerField(default=0, help_text='Internal counter of how many times this tag is in use')),
                ('protected', models.BooleanField(default=False, help_text='Will not be deleted when the count reaches 0')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=(tagulous.models.models.BaseTagModel, models.Model),
        ),
        migrations.CreateModel(
            name='Milestone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('slug', models.SlugField(blank=True, editable=False, max_length=200, null=True)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('state', models.IntegerField(choices=[(0, 'Completed'), (1, 'Overdue'), (2, 'active'), (3, 'closed')], default=2)),
                ('description', models.TextField()),
                ('percentage_done', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(100), django.core.validators.MinValueValidator(0)])),
                ('order', models.SmallIntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('tags', tagulous.models.fields.TagField(_set_tag_meta=True, help_text='Enter a comma-separated tag string', initial='Kampala, Entebbe, Jinja, Nairobi, Mombosa, Dar es Salaam, Kigali, Amsterdam', to='tunga_tasks._Tagulous_Milestone_tags')),
            ],
        ),
        migrations.CreateModel(
            name='TaskMilestone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('milestone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tunga_tasks.Milestone')),
            ],
        ),
        migrations.CreateModel(
            name='TaskUpdate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(default='on schedule', max_length=50)),
                ('accomplished', models.CharField(blank=True, max_length=400, null=True)),
                ('percentage_done', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(100), django.core.validators.MinValueValidator(0)])),
                ('next_steps', models.CharField(blank=True, max_length=400, null=True)),
                ('other_remarks', models.CharField(blank=True, max_length=400, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('milestone', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tunga_tasks.Milestone')),
            ],
        ),
        migrations.CreateModel(
            name='TaskUpdateFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('file', models.FileField(upload_to='task_update_files')),
                ('size', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(20000), django.core.validators.MinValueValidator(1)])),
                ('type', models.CharField(max_length=64)),
                ('task_update', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='tunga_tasks.TaskUpdate')),
            ],
        ),
        migrations.AlterField(
            model_name='task',
            name='skills',
            field=tagulous.models.fields.TagField(_set_tag_meta=True, blank=True, help_text='Enter a comma-separated tag string', initial='Kampala, Entebbe, Jinja, Nairobi, Mombosa, Dar es Salaam, Kigali, Amsterdam', to='tunga_profiles.Skill'),
        ),
        migrations.AddField(
            model_name='taskmilestone',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tunga_tasks.Task'),
        ),
        migrations.AddField(
            model_name='milestone',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tunga_tasks.Task'),
        ),
        migrations.AddField(
            model_name='milestone',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='_tagulous_milestone_tags',
            unique_together=set([('slug',)]),
        ),
        migrations.AddField(
            model_name='task',
            name='milestones',
            field=models.ManyToManyField(blank=True, related_name='task_milestones', through='tunga_tasks.TaskMilestone', to='tunga_tasks.Milestone'),
        ),
    ]
