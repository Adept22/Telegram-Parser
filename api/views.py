import glob
import os.path
import random
import string
import tempfile
from functools import reduce
from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework import permissions, viewsets, status
import api.serializers as serializers
from api.paginators import CustomPagination
import base.models as base_models
import api.filters as base_filters


class Phones(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.PhoneListSerializer
    queryset = base_models.Phone.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = base_filters.PhoneFilter

    def get_serializer_class(self):
        if self.action == "update":
            return serializers.PhoneUpdateSerializer
        return self.serializer_class

    @action(methods=["get"], detail=True)
    def chat_phones(self, request, pk=None):
        obj = self.get_object()
        serializer = serializers.ChatPhoneListSerializer(obj.chatphone_set.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class Chats(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ChatListSerializer
    queryset = base_models.Chat.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = base_filters.ChatFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            chat, created = base_models.Chat.objects.update_or_create(
                link=serializer.validated_data["link"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(chat)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=True)
    def chat_phones(self, request, pk=None):
        obj = self.get_object()
        serializer = serializers.ChatPhoneListSerializer(obj.chatphone_set.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatPhones(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ChatPhoneListSerializer
    queryset = base_models.ChatPhone.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = base_filters.ChatPhoneFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.ChatPhone.objects.update_or_create(
                chat=serializer.validated_data["chat"],
                phone=serializer.validated_data["phone"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Parsers(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ParserListSerializer
    queryset = base_models.Parser.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.ParserFilter


class Messages(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.MessageListSerializer
    queryset = base_models.Message.objects.all()
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    pagination_class = CustomPagination
    ordering_fields = ["internal_id", "created_at"]
    filter_class = base_filters.MessageFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.Message.objects.update_or_create(
                chat=serializer.validated_data["chat"],
                internal_id=serializer.validated_data["internal_id"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageMedias(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.MessageMediaListSerializer
    queryset = base_models.MessageMedia.objects.all()
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.MessageMedia.objects.update_or_create(
                internal_id=serializer.validated_data["internal_id"],
                message=serializer.validated_data["message"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def make_path(self, current, *, depth: 'int' = 0):
        if depth >= settings.MEDIA_PATH_DEPTH:
            return current

        name = ''.join([random.choice(string.digits + string.ascii_lowercase) for c in range(0, 2)])

        current = os.path.join(current, name)

        if not os.path.exists(current):
            os.mkdir(current, 0o775)

        return self.make_path(current, depth=depth + 1)

    @action(methods=["post", "get"], detail=True)
    def chunk(self, request, pk=None):
        if request.method == "POST":
            request.data['filename'] = request.query_params.get('filename')
            request.data['chunk_number'] = request.query_params.get('chunk_number')
            request.data['total_size'] = request.query_params.get('total_size')
            request.data['total_chunks'] = request.query_params.get('total_chunks')
            request.data['chunk_size'] = request.query_params.get('chunk_size')

            serializer = serializers.ChunkCreateSerializer(data=request.data)

            if serializer.is_valid():
                chunk = serializer.validated_data['chunk']
                filename = serializer.validated_data['filename']
                chunk_number = serializer.validated_data['chunk_number']
                total_size = serializer.validated_data['total_size']
                total_chunks = serializer.validated_data['total_chunks']

                tmp_dir = tempfile.gettempdir()

                tmp_path = os.path.join(tmp_dir, f"{filename}.part{chunk_number}")

                with open(tmp_path, 'wb') as tmpf:
                    tmpf.write(chunk.read())

                if chunk_number >= total_chunks - 1:
                    chunks = glob.glob(os.path.join(tmp_dir, f"{filename}.part[0-9]*"))
                    if chunks:
                        computed = reduce(lambda x, y: x + y, [os.path.getsize(c) for c in chunks])
                        if computed >= total_size:
                            obj = self.get_object()

                            path = self.make_path(settings.MEDIA_ROOT)
                            name, ext = os.path.splitext(filename)
                            media_path = os.path.join(path, f"{obj.id}{ext}")

                            with open(media_path, "wb") as mf:
                                for chunk in sorted(chunks):
                                    with open(chunk, "rb") as cf:
                                        mf.write(cf.read())

                                    os.remove(chunk)

                            obj.path = os.path.join('uploads', os.path.relpath(media_path, settings.MEDIA_ROOT))
                            obj.save()

                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = serializers.ChunkViewSerializer(data=request.GET)

            if serializer.is_valid():
                req = serializer.validated_data

                tmp_dir = tempfile.gettempdir()

                if os.path.exists(os.path.join(tmp_dir, u"{}.part{}".format(req["filename"], req["chunk_number"]))):
                    return Response(status=status.HTTP_204_NO_CONTENT)

                return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Members(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.MemberListSerializer
    queryset = base_models.Member.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.MemberFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.Member.objects.update_or_create(
                internal_id=serializer.validated_data["internal_id"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatMembers(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ChatMemberListSerializer
    queryset = base_models.ChatMember.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.ChatMemberFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.ChatMember.objects.update_or_create(
                chat=serializer.validated_data["chat"],
                member=serializer.validated_data["member"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatMemberRoles(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ChatMemberRoleListSerializer
    queryset = base_models.ChatMemberRole.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.ChatMemberRoleFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.ChatMemberRole.objects.update_or_create(
                member=serializer.validated_data["member"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemberMedias(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.MemberMediaListSerializer
    queryset = base_models.MemberMedia.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.MemberMediaFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.MemberMedia.objects.update_or_create(
                internal_id=serializer.validated_data["internal_id"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def make_path(self, current, *, depth: 'int' = 0):
        if depth >= settings.MEDIA_PATH_DEPTH:
            return current

        name = ''.join([random.choice(string.digits + string.ascii_lowercase) for c in range(0, 2)])

        current = os.path.join(current, name)

        if not os.path.exists(current):
            os.mkdir(current, 0o775)

        return self.make_path(current, depth=depth + 1)

    @action(methods=["post", "get"], detail=True)
    def chunk(self, request, pk=None):
        if request.method == "POST":
            request.data['filename'] = request.query_params.get('filename')
            request.data['chunk_number'] = request.query_params.get('chunk_number')
            request.data['total_size'] = request.query_params.get('total_size')
            request.data['total_chunks'] = request.query_params.get('total_chunks')
            request.data['chunk_size'] = request.query_params.get('chunk_size')

            serializer = serializers.ChunkCreateSerializer(data=request.data)

            if serializer.is_valid():
                chunk = serializer.validated_data['chunk']
                filename = serializer.validated_data['filename']
                chunk_number = serializer.validated_data['chunk_number']
                total_size = serializer.validated_data['total_size']
                total_chunks = serializer.validated_data['total_chunks']

                tmp_dir = tempfile.gettempdir()

                tmp_path = os.path.join(tmp_dir, f"{filename}.part{chunk_number}")

                with open(tmp_path, 'wb') as tmpf:
                    tmpf.write(chunk.read())

                if chunk_number >= total_chunks - 1:
                    chunks = glob.glob(os.path.join(tmp_dir, f"{filename}.part[0-9]*"))
                    if chunks:
                        computed = reduce(lambda x, y: x + y, [os.path.getsize(c) for c in chunks])
                        if computed >= total_size:
                            obj = self.get_object()

                            path = self.make_path(settings.MEDIA_ROOT)
                            name, ext = os.path.splitext(filename)
                            media_path = os.path.join(path, f"{obj.id}{ext}")

                            with open(media_path, "wb") as mf:
                                for chunk in sorted(chunks):
                                    with open(chunk, "rb") as cf:
                                        mf.write(cf.read())

                                    os.remove(chunk)

                            obj.path = os.path.join('uploads', os.path.relpath(media_path, settings.MEDIA_ROOT))
                            obj.save()

                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = serializers.ChunkViewSerializer(data=request.GET)

            if serializer.is_valid():
                req = serializer.validated_data

                tmp_dir = tempfile.gettempdir()

                if os.path.exists(os.path.join(tmp_dir, u"{}.part{}".format(req["filename"], req["chunk_number"]))):
                    return Response(status=status.HTTP_204_NO_CONTENT)

                return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatMedias(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ChatMediaListSerializer
    queryset = base_models.ChatMedia.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.ChatMediaFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            obj, created = base_models.ChatMedia.objects.update_or_create(
                internal_id=serializer.validated_data["internal_id"],
                defaults=serializer.validated_data,
            )
            serializer = self.get_serializer(obj)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def make_path(self, current, *, depth: 'int' = 0):
        if depth >= settings.MEDIA_PATH_DEPTH:
            return current

        name = ''.join([random.choice(string.digits + string.ascii_lowercase) for c in range(0, 2)])

        current = os.path.join(current, name)

        if not os.path.exists(current):
            os.mkdir(current, 0o775)

        return self.make_path(current, depth=depth + 1)

    @action(methods=["post", "get"], detail=True)
    def chunk(self, request, pk=None):
        if request.method == "POST":
            request.data['filename'] = request.query_params.get('filename')
            request.data['chunk_number'] = request.query_params.get('chunk_number')
            request.data['total_size'] = request.query_params.get('total_size')
            request.data['total_chunks'] = request.query_params.get('total_chunks')
            request.data['chunk_size'] = request.query_params.get('chunk_size')

            serializer = serializers.ChunkCreateSerializer(data=request.data)

            if serializer.is_valid():
                chunk = serializer.validated_data['chunk']
                filename = serializer.validated_data['filename']
                chunk_number = serializer.validated_data['chunk_number']
                total_size = serializer.validated_data['total_size']
                total_chunks = serializer.validated_data['total_chunks']

                tmp_dir = tempfile.gettempdir()

                tmp_path = os.path.join(tmp_dir, f"{filename}.part{chunk_number}")

                with open(tmp_path, 'wb') as tmpf:
                    tmpf.write(chunk.read())

                if chunk_number >= total_chunks - 1:
                    chunks = glob.glob(os.path.join(tmp_dir, f"{filename}.part[0-9]*"))
                    if chunks:
                        computed = reduce(lambda x, y: x + y, [os.path.getsize(c) for c in chunks])
                        if computed >= total_size:
                            obj = self.get_object()

                            path = self.make_path(settings.MEDIA_ROOT)
                            name, ext = os.path.splitext(filename)
                            media_path = os.path.join(path, f"{obj.id}{ext}")

                            with open(media_path, "wb") as mf:
                                for chunk in sorted(chunks):
                                    with open(chunk, "rb") as cf:
                                        mf.write(cf.read())

                                    os.remove(chunk)

                            obj.path = os.path.join('uploads', os.path.relpath(media_path, settings.MEDIA_ROOT))
                            obj.save()

                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = serializers.ChunkViewSerializer(data=request.GET)

            if serializer.is_valid():
                req = serializer.validated_data

                tmp_dir = tempfile.gettempdir()

                if os.path.exists(os.path.join(tmp_dir, u"{}.part{}".format(req["filename"], req["chunk_number"]))):
                    return Response(status=status.HTTP_204_NO_CONTENT)

                return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Hosts(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.HostListSerializer
    queryset = base_models.Host.objects.all()
    pagination_class = CustomPagination


class Tasks(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.TaskListSerializer
    queryset = base_models.Task.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter)
    filter_class = base_filters.TaskFilter

