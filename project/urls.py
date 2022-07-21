from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from api import views as api_views


router = DefaultRouter()
# router.register(r'bots', api_views.Bots)
router.register(r'chats', api_views.Chats)
router.register(r'chats-medias', api_views.ChatMedias)
router.register(r'chats-members', api_views.ChatMembers)
router.register(r'chats-members-roles', api_views.ChatMemberRoles)
router.register(r'chats-phones', api_views.ChatPhones)
router.register(r'hosts', api_views.Hosts)
router.register(r'members', api_views.Members)
router.register(r'members-medias', api_views.MemberMedias)
router.register(r'messages', api_views.Messages)
router.register(r'messages-medias', api_views.MessageMedias)
router.register(r'parsers', api_views.Parsers)
router.register(r'phones', api_views.Phones)
router.register(r'chats-tasks', api_views.Tasks)


urlpatterns = [
    # path('admin/', admin.site.urls),
    re_path(r'^api/v1/', include(router.urls)),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Администрирование парсера телеграм'

