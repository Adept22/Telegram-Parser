from rest_framework import serializers
import base.models as base_models


class HostViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Host
        fields = ("id", "created_at", "local_ip", "public_ip", "name")
        read_only_fields = ("id",)


class ParserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Parser
        fields = ("id", "created_at", "status", "host")
        read_only_fields = ("id",)


class ParserSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(model_field=base_models.Parser()._meta.get_field("id"))

    class Meta:
        model = base_models.Parser
        fields = ("id", "created_at", "status")
        read_only_fields = ("id", "created_at")


class PhoneListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Phone
        fields = ("id", "number", "internal_id", "session", "first_name", "last_name", "status", "code", "created_at",
                  "parser", "api", "takeout")
        read_only_fields = ("id", "created_at")


class PhoneUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Phone
        fields = (
            "id", "number", "internal_id", "session", "first_name", "last_name", "code", "created_at",
            "status_text", "status", "parser", "api", "takeout"
        )
        read_only_fields = ("id", "created_at")


class PhoneViewSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = base_models.Phone
        fields = ("id", "number", "internal_id", "session", "first_name", "status", "created_at", "code", "takeout")
        read_only_fields = ("id",)


class ChatListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Chat
        fields = (
            "id", "created_at", "link", "internal_id", "title", "status", "parser", "total_members", "total_messages"
        )
        read_only_fields = ("id", "created_at")
        extra_kwargs = {"link": {"validators": [], "required": True}}


class ChatMiniSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(model_field=base_models.Chat()._meta.get_field("id"))

    class Meta:
        model = base_models.Chat
        fields = ("id",)
        read_only_fields = ("id",)


class ChatViewSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = base_models.Chat
        fields = ("id", "link", "internal_id", "status", "title", "created_at", "date", "description")
        read_only_fields = ("id",)


class PhoneMiniSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(model_field=base_models.Phone()._meta.get_field("id"))

    class Meta:
        model = base_models.Phone
        fields = ("id",)
        read_only_fields = ("id",)


class ChatPhoneListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.ChatPhone
        fields = ("id", "chat", "phone", "is_using", "created_at")
        read_only_fields = ("id",)


class MemberViewSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(model_field=base_models.Member()._meta.get_field("id"))

    class Meta:
        model = base_models.Member
        fields = ("id", "internal_id", "username", "first_name", "last_name", "phone", "about")
        read_only_fields = ("id",)


class MemberListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Member
        fields = ("id", "internal_id", "username", "first_name", "last_name", "phone", "about")
        read_only_fields = ("id",)
        extra_kwargs = {"internal_id": {"validators": [], "required": True}}


class ChatMemberListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.ChatMember
        fields = ("id", "chat", "member", "is_left", "date", "chat_id")
        read_only_fields = ("id",)


class ChatMemberSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(model_field=base_models.ChatMember()._meta.get_field("id"))

    class Meta:
        model = base_models.ChatMember
        fields = ("id",)
        read_only_fields = ("id",)


class ChatMemberRoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.ChatMemberRole
        fields = ("id", "member", "title", "code")
        read_only_fields = ("id",)


class MemberMediaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.MemberMedia
        fields = ("id", "member", "internal_id", "path", "date", "created_at")
        read_only_fields = ("id", "path", "created_at")
        extra_kwargs = {"internal_id": {"validators": [], "required": True}}


class ChatMediaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.ChatMedia
        fields = ("id", "chat", "internal_id", "path", "date", "created_at")
        read_only_fields = ("id", "path", "created_at")
        extra_kwargs = {"internal_id": {"validators": [], "required": True}}


class HostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Host
        fields = ("id", "created_at", "public_ip", "local_ip", "name")
        read_only_fields = ("id", "created_at")


class MessageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Message
        fields = ("id", "member", "reply_to", "internal_id", "text", "is_pinned", "forwarded_from_id",
                  "forwarded_from_name", "created_at", "chat", "grouped_id", "date")
        read_only_fields = ("id", "created_at")
        write_only_fields = ("internal_id",)


class MessageMediaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.MessageMedia
        fields = ("id", "message", "path", "internal_id", "date", "created_at")
        read_only_fields = ("id", "path", "created_at")
        extra_kwargs = {"internal_id": {"validators": [], "required": True}}


class ChunkCreateSerializer(serializers.Serializer):
    chunk_number = serializers.IntegerField(required=True)
    chunk_size = serializers.IntegerField(required=True)
    filename = serializers.CharField(required=True)
    total_size = serializers.IntegerField(required=True)
    total_chunks = serializers.IntegerField(required=True)
    chunk = serializers.FileField(required=False)


class ChunkViewSerializer(serializers.Serializer):
    chunk_number = serializers.IntegerField(required=True)
    chunk_size = serializers.IntegerField(required=False)
    filename = serializers.CharField(required=True)
    total_size = serializers.IntegerField(required=False)
    total_chunks = serializers.IntegerField(required=False)
    chunk = serializers.FileField(required=False)


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = base_models.Task
        fields = "__all__"
        read_only_fields = ("id", "created_at")

