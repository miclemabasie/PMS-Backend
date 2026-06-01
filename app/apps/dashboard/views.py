from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import LandlordDashboardService


class LandlordDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, "owner_profile"):
            return Response({"detail": "User is not a landlord"}, status=403)

        service = LandlordDashboardService()
        stats = service.get_stats(user.owner_profile.pkid)
        return Response(stats)
