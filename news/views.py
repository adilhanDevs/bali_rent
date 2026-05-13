from rest_framework import viewsets, permissions
from .models import NewsArticle
from .serializers import NewsArticleSerializer, AdminNewsArticleSerializer


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsArticle.objects.filter(is_active=True).prefetch_related('translations')
    serializer_class = NewsArticleSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class AdminNewsArticleViewSet(viewsets.ModelViewSet):
    queryset = NewsArticle.objects.prefetch_related('translations').order_by('-published_at', '-id')
    serializer_class = AdminNewsArticleSerializer
    permission_classes = [permissions.IsAdminUser]
