from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import NewsArticle, NewsArticleImage
from .serializers import NewsArticleSerializer, AdminNewsArticleSerializer, NewsArticleImageSerializer


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsArticle.objects.filter(is_active=True).prefetch_related('translations', 'images')
    serializer_class = NewsArticleSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class AdminNewsArticleViewSet(viewsets.ModelViewSet):
    queryset = NewsArticle.objects.prefetch_related('translations', 'images').order_by('-published_at', '-id')
    serializer_class = AdminNewsArticleSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'], url_path='images')
    def upload_images(self, request, pk=None):
        article = self.get_object()
        files = request.FILES.getlist('images') or request.FILES.getlist('image')
        if not files and 'image' in request.FILES:
            files = [request.FILES['image']]
        if not files:
            return Response({'detail': 'No images provided.'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        current_count = article.images.count()
        for idx, f in enumerate(files):
            img = NewsArticleImage.objects.create(
                article=article,
                image=f,
                sort_order=current_count + idx,
            )
            if not article.image:
                article.image = f
                article.save(update_fields=['image'])
            created.append(NewsArticleImageSerializer(img).data)
        return Response(created, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'images/(?P<image_id>\d+)')
    def delete_image(self, request, pk=None, image_id=None):
        article = self.get_object()
        img = article.images.filter(id=image_id).first()
        if not img:
            return Response({'detail': 'Image not found.'}, status=status.HTTP_404_NOT_FOUND)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
