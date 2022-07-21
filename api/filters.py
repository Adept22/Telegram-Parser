import django_filters
import base.models as base_models


class ChatFilter(django_filters.FilterSet):
    phone = django_filters.CharFilter(
        field_name='chatphone__phone__number', label='Phone number', lookup_expr='contains'
    )

    class Meta:
        model = base_models.Chat
        fields = ["id", "internal_id", "link", "title", "status", "phone"]


class PhoneFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.Phone
        fields = "__all__"
        exclude = ["api"]


class MessageFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.Message
        fields = "__all__"


class MemberFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.Member
        fields = "__all__"


class ChatMemberFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.ChatMember
        fields = "__all__"


class ChatMemberRoleFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.ChatMemberRole
        fields = "__all__"


class ChatPhoneFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.ChatPhone
        fields = "__all__"


class ParserFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.Parser
        fields = "__all__"


class TaskFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.Task
        fields = "__all__"


class MemberMediaFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.MemberMedia
        fields = "__all__"


class ChatMediaFilter(django_filters.FilterSet):
    class Meta:
        model = base_models.ChatMedia
        fields = "__all__"

