from rest_framework import views, permissions
from rest_framework.response import Response
from .models import Wallet
from .serializers import WalletSerializer

class MyWalletView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        # Sort transactions safely
        serializer = WalletSerializer(wallet)
        data = serializer.data
        data['transactions'] = sorted(data['transactions'], key=lambda x: x['created_at'], reverse=True)
        return Response(data)
