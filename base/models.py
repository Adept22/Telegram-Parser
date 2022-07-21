import uuid
from django.db import models
from django.conf import settings
from telethon.utils import resolve_id


class BaseModel(models.Model):
    """ Абстрактная модель для использования UUID в качестве PK."""
    # Параметр blank=True позволяет работать с формами, он никогда не
    # будет пустым, см. метод save()

    id = models.UUIDField(primary_key=True, default=uuid.uuid1, editable=False)
    created_at = models.DateTimeField(u"дата создания", auto_now_add=True)

    class Meta:
        abstract = True


class Host(BaseModel):
    public_ip = models.CharField(max_length=15, blank=True, null=True)
    local_ip = models.CharField(max_length=15, blank=True, null=True, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = u"Host"
        verbose_name_plural = u"Hosts"
        db_table = 'telegram\".\"hosts'

    def __str__(self):
        return u"{}. {}".format(self.id, self.name)


class Parser(BaseModel):
    NEW_STATUS = 0
    IN_PROGRESS_STATUS = 1
    FAILED_STATUS = 2

    STATUS_CHOICES = (
        (NEW_STATUS, u"Создан"),
        (IN_PROGRESS_STATUS, u"В работе"),
        (FAILED_STATUS, u"Ошибка"),
    )

    host = models.ForeignKey(Host, verbose_name=u"host", on_delete=models.CASCADE)
    status = models.IntegerField(u"status", default=NEW_STATUS, choices=STATUS_CHOICES)

    class Meta:
        verbose_name = u"Parser"
        verbose_name_plural = u"Parsers"
        db_table = 'telegram\".\"parsers'

    def __str__(self):
        return u"{}".format(self.id)


class Phone(BaseModel):
    CREATED = 0
    READY = 1
    FLOOD = 2
    FULL = 3
    BAN = 4

    STATUS_CHOICES = (
        (CREATED, u"Создан"),
        (READY, u"Готов"),
        (FLOOD, u"В ожидании"),
        (FULL, u"Полон"),
        (BAN, u"Забанен"),
    )

    number = models.CharField(u"номер", max_length=20, blank=False, unique=True)
    first_name = models.CharField(u"first name", max_length=255, blank=True, null=True)
    last_name = models.CharField(u"last name", max_length=255, blank=True, null=True)
    status = models.IntegerField(u"status", default=CREATED, choices=STATUS_CHOICES)
    status_text = models.TextField(u"status text", blank=True, null=True)
    parser = models.ForeignKey(Parser, verbose_name=u"parser", on_delete=models.CASCADE, null=True, blank=False)
    code = models.CharField(u"code", max_length=10, blank=True, null=True)
    session = models.CharField(u"session", max_length=512, null=True, blank=True, unique=True)
    internal_id = models.BigIntegerField(blank=True, null=True, unique=True)
    api = models.JSONField(blank=True, null=True)
    takeout = models.BooleanField(u"takeout", default=True)

    class Meta:
        verbose_name = u"Phone"
        verbose_name_plural = u"Phones"
        db_table = 'telegram\".\"phones'

    def __str__(self):
        return u"{}. {}".format(self.id, self.number)


class Chat(BaseModel):
    CREATED = 0
    AVAILABLE = 1
    MONITORING = 2
    FAILED = 3

    STATUS_CHOICES = (
        (CREATED, u"Создан"),
        (AVAILABLE, u"Доступен"),
        (MONITORING, u"Мониторинг"),
        (FAILED, u"Ошибка"),
    )

    internal_id = models.BigIntegerField("internal id", null=True, blank=True, unique=True)
    link = models.CharField(u"link", max_length=255, blank=False, unique=True)
    title = models.CharField(u"title", max_length=255, blank=True)
    status = models.IntegerField(u"status", default=CREATED, choices=STATUS_CHOICES, blank=True)
    status_text = models.TextField(u"status text", blank=True, null=True)
    description = models.TextField(u"description", blank=True, null=True)
    parser = models.ForeignKey(Parser, verbose_name=u"parser", on_delete=models.CASCADE, null=True, blank=False)
    date = models.DateField(u"date", blank=True, null=True)
    total_messages = models.IntegerField(u"total messages", default=0, blank=True, null=True)
    total_members = models.IntegerField(u"total members", default=0, blank=True, null=True)

    class Meta:
        verbose_name = u"Chat"
        verbose_name_plural = u"Chats"
        db_table = 'telegram\".\"chats'

    def __str__(self):
        return f"{self.link}"

    @property
    def get_type(self):
        type = None

        if self.internal_id:
            type = resolve_id(self.internal_id)[1].__name__

        return type

    def get_chat_phones(self):
        chat_phones = self.chatphone_set.filter(
            is_using=True,
            phone__takeout=False
        )

        if chat_phones.count() >= settings.CHAT_PHONE_LINKS:
            return []

        phones = list(Phone.objects.filter(status=Phone.READY, takeout=False))

        return phones[:settings.CHAT_PHONE_LINKS - chat_phones.count()]


class ChatPhone(BaseModel):
    chat = models.ForeignKey(Chat, verbose_name=u"chat", on_delete=models.CASCADE)
    phone = models.ForeignKey(Phone, verbose_name=u"phone", on_delete=models.CASCADE)
    is_using = models.BooleanField(u"is using", default=True)

    class Meta:
        verbose_name = u"ChatPhone"
        verbose_name_plural = u"ChatPhones"
        db_table = 'telegram\".\"chats_phones'
        constraints = [
            models.UniqueConstraint(fields=["chat", "phone"], name="chat_phone_unique"),
        ]

    def __str__(self):
        return u"{}".format(self.id)


class ChatMedia(BaseModel):
    internal_id = models.BigIntegerField(u"internal id", unique=True)
    chat = models.ForeignKey(Chat, verbose_name=u"chat", on_delete=models.CASCADE, null=True, blank=False)
    path = models.CharField(max_length=3000, blank=True, null=True)
    date = models.DateTimeField(u"дата", blank=True, null=True)

    class Meta:
        verbose_name = u"ChatMedia"
        verbose_name_plural = u"ChatMedias"
        db_table = 'telegram\".\"chats_medias'

    def __str__(self):
        return u"{}. {}".format(self.id, self.chat)


class Member(BaseModel):
    internal_id = models.BigIntegerField(blank=True, unique=True)
    username = models.CharField(u"username", max_length=255, blank=True, null=True)
    first_name = models.CharField(u"first name", max_length=255, blank=True, null=True)
    last_name = models.CharField(u"last name", max_length=255, blank=True, null=True)
    about = models.TextField(u"about", blank=True, null=True)
    phone = models.CharField(u"phone", max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = u"Member"
        verbose_name_plural = u"Members"
        db_table = 'telegram\".\"members'

    def __str__(self):
        return u"{}. {}".format(self.id, self.username)


class MemberMedia(BaseModel):
    member = models.ForeignKey(Member, verbose_name=u"member media", on_delete=models.CASCADE)
    internal_id = models.BigIntegerField(u"internal id", unique=True)
    path = models.CharField(u"path", max_length=255, blank=True, null=True)
    date = models.DateTimeField(u"date", blank=True, null=True)

    class Meta:
        verbose_name = u"MemberMedia"
        verbose_name_plural = u"MemberMedias"
        db_table = 'telegram\".\"members_medias'

    def __str__(self):
        return u"{}. {}".format(self.id, self.member)


class ChatMember(BaseModel):
    chat = models.ForeignKey(Chat, verbose_name=u"chat", on_delete=models.CASCADE)
    member = models.ForeignKey(Member, verbose_name=u"member", on_delete=models.CASCADE)
    is_left = models.BooleanField(u"is left", default=False)
    date = models.DateTimeField(u"дата", blank=True, null=True)

    class Meta:
        verbose_name = u"ChatMember"
        verbose_name_plural = u"ChatMembers"
        db_table = 'telegram\".\"chats_members'
        constraints = [
            models.UniqueConstraint(fields=["chat", "member"], name="chat_member_unique"),
        ]

    def __str__(self):
        return u"{}. {} - {}".format(self.id, self.chat, self.member)


class ChatMemberRole(BaseModel):
    member = models.ForeignKey(ChatMember, verbose_name=u"member", on_delete=models.CASCADE)
    title = models.CharField(u"title", max_length=100)
    code = models.CharField(u"code", max_length=10)

    class Meta:
        verbose_name = u"ChatMemberRole"
        verbose_name_plural = u"ChatMemberRoles"
        db_table = 'telegram\".\"chats_members_roles'
        constraints = [
            models.UniqueConstraint(fields=["member", "title", "code"], name="chat_member_role_unique"),
        ]

    def __str__(self):
        return u"{}. {}".format(self.id, self.title)


class Message(BaseModel):
    member = models.ForeignKey(ChatMember, verbose_name=u"member", on_delete=models.CASCADE, blank=True, null=True)
    reply_to = models.ForeignKey("self", verbose_name=u"reply_to", blank=True, null=True, on_delete=models.CASCADE)
    internal_id = models.BigIntegerField(u"internal id")
    text = models.TextField(blank=True, null=True)
    is_pinned = models.BooleanField(u"is pinned", default=False)
    forwarded_from_id = models.BigIntegerField(u"forwarded from id", blank=True, null=True)
    forwarded_from_name = models.CharField(max_length=255, blank=True, null=True)
    chat = models.ForeignKey(Chat, verbose_name=u"chat", on_delete=models.CASCADE, null=True, blank=False)
    grouped_id = models.BigIntegerField(u"grouped id", blank=True, null=True)
    date = models.DateTimeField(u"date", blank=True, null=True)

    class Meta:
        verbose_name = u"Message"
        verbose_name_plural = u"Messages"
        db_table = 'telegram\".\"messages'
        constraints = [
            models.UniqueConstraint(fields=["internal_id", "chat"], name="message_unique"),
        ]

    def __str__(self):
        return u"{}. {}".format(self.id, self.text)


class MessageMedia(BaseModel):
    message = models.ForeignKey(Message, verbose_name=u"message media", on_delete=models.CASCADE)
    internal_id = models.BigIntegerField(u"internal id")
    path = models.CharField(u"path", max_length=255, blank=True, null=True)
    date = models.DateTimeField(u"date", blank=True, null=True)

    class Meta:
        verbose_name = u"MessageMedia"
        verbose_name_plural = u"MessageMedias"
        db_table = 'telegram\".\"messages_medias'
        constraints = [
            models.UniqueConstraint(fields=["internal_id", "message"], name="message_media_unique"),
        ]

    def __str__(self):
        return u"{}. {}".format(self.id, self.message)


class Task(BaseModel):
    CREATED_STATUS = 0
    STARTED_STATUS = 1
    SUCCESS_STATUS = 2
    FAILURE_STATUS = 3
    REVOKED_STATUS = 4

    STATUS_CHOICES = (
        (CREATED_STATUS, u"Создан"),
        (STARTED_STATUS, u"В работе"),
        (SUCCESS_STATUS, u"Выполнен"),
        (FAILURE_STATUS, u"Ошибка"),
        (REVOKED_STATUS, u"Отозван"),
    )

    MEMBER_TYPE = 0
    MESSAGE_TYPE = 1
    MONITORING_TYPE = 2

    TYPE_CHOICES = (
        (MEMBER_TYPE, u"Участники"),
        (MESSAGE_TYPE, u"Сообщения"),
        (MONITORING_TYPE, u"Мониторинг"),
    )

    chat = models.ForeignKey(Chat, verbose_name=u"chat", on_delete=models.CASCADE)
    status = models.IntegerField(u"status", default=CREATED_STATUS, choices=STATUS_CHOICES)
    status_text = models.TextField(u"status text", blank=True, null=True)
    started_at = models.DateTimeField(u"дата запуска", blank=True, null=True)
    ended_at = models.DateTimeField(u"дата завершения", blank=True, null=True)
    type = models.IntegerField(u"type", choices=TYPE_CHOICES)

    class Meta:
        verbose_name = u"Task"
        verbose_name_plural = u"Tasks"
        db_table = 'telegram\".\"chats_tasks'


TypeHost = Host
TypeParser = Parser
TypePhone = Phone
TypeMember = Member
TypeMemberMedia = MemberMedia
TypeMessage = Message
TypeMessageMedia = MessageMedia
TypeChat = Chat
TypeChatPhone = ChatPhone
TypeChatMember = ChatMember
TypeChatMemberRole = ChatMemberRole
TypeChatMedia = ChatMedia
