from rest_framework import serializers, views, response, status, permissions
from .models import AnalyticsEvent
import json

class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = ['event_name', 'payload', 'session_id', 'device_id']

    def validate_payload(self, value):
        # Limit payload size to 10KB
        payload_str = json.dumps(value)
        if len(payload_str) > 10240:
            raise serializers.ValidationError("Payload too large. Max 10KB.")
        return value

class AnalyticsEventCreateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AnalyticsEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        serializer.save(
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        return response.Response({"status": "captured"}, status=status.HTTP_201_CREATED)
