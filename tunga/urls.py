"""tunga URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token

from tunga_auth.views import VerifyUserView, AuthUserView, AccountInfoView
from tunga_comments.views import CommentViewSet
from tunga_messages.views import MessageViewSet, ReplyViewSet
from tunga_profiles.views import ProfileView, EducationViewSet, WorkViewSet, ConnectionViewSet, SocialLinkViewSet
from tunga_tasks.views import TaskViewSet, ApplicationViewSet, ParticipationViewSet, TaskRequestViewSet, \
    SavedTaskViewSet
from tunga_activity.views import ActionViewSet

router = DefaultRouter()
router.register(r'task', TaskViewSet)
router.register(r'application', ApplicationViewSet)
router.register(r'participation', ParticipationViewSet)
router.register(r'task-request', TaskRequestViewSet)
router.register(r'saved-task', SavedTaskViewSet)
router.register(r'social-link', SocialLinkViewSet)
router.register(r'education', EducationViewSet)
router.register(r'work', WorkViewSet)
router.register(r'connection', ConnectionViewSet)
router.register(r'comment', CommentViewSet)
router.register(r'message', MessageViewSet)
router.register(r'reply', ReplyViewSet)
router.register(r'activity', ActionViewSet)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('allauth.urls')),
    url(r'api/', include(router.urls)),
    url(r'^api/auth/registration/', include('rest_auth.registration.urls')),
    url(r'^api/auth/verify/', VerifyUserView.as_view(), name='auth-verify'),
    url(r'^api/auth/user/', AuthUserView.as_view(), name='auth-user'),
    url(r'^api/auth/account/', AccountInfoView.as_view(), name='account-info'),
    url(r'^api/auth/profile/', ProfileView.as_view(), name='profile-info'),
    url(r'^api/auth/', include('rest_auth.urls')),
    url(r'api/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^api/jwt/token/', obtain_jwt_token),
    url(r'^api/jwt/refresh/', refresh_jwt_token),
    url(r'^api/jwt/verify/', verify_jwt_token),
    url(r'^api/docs/', include('rest_framework_swagger.urls')),
]