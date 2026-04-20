from datetime import timedelta
from django.utils import timezone

from .models import Property, Owner, PropertyOwnership
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


def calculatate_occupancy_rate(property_id):
    units = Property.objects.get(id=property_id).units.all()
    occupied_units = units.filter(status="occupied").count()
    if occupied_units == 0:
        return 0
    return occupied_units / units.count()


def calculate_owner_occupancy_rate(property_id):
    """
    Calculate the occupancy rate of a specific owner taking into consideration his properties and all the units in every property
    """
    owner_id = PropertyOwnership.objects.get(property__id=property_id).owner_id
    properties = Owner.objects.get(pkid=owner_id).properties.all()
    occupied_units = 0
    total_units = 0
    for property in properties:
        units = property.units.all()
        occupied_units += units.filter(status="occupied").count()
        total_units += units.count()
    if total_units == 0:
        return 0
    return occupied_units / total_units


def get_total_properties_for_owner(property_id):
    owner_id = PropertyOwnership.objects.get(property__id=property_id).owner_id
    return Owner.objects.get(pkid=owner_id).properties.count()


def get_total_units_for_property(property_id):
    return Property.objects.get(id=property_id).units.count()


def get_monthly_revenue(property_id):
    # return Property.objects.get(id=property_id).monthly_revenue
    return 0


def get_total_number_of_properties_added_in_the_last_30_days_by_owner(property_id):
    # get all the latest properties that were added in the last 30 days
    owner_id = PropertyOwnership.objects.get(property__id=property_id).owner_id
    return (
        Owner.objects.get(pkid=owner_id)
        .properties.filter(created_at__gte=timezone.now() - timedelta(days=30))
        .count()
    )


def get_statistics(data):
    property_id = data[0].get("id")
    return {
        "occupancy_rate": calculatate_occupancy_rate(property_id),
        "owner_occupancy_rate": calculate_owner_occupancy_rate(property_id),
        "total_properties": get_total_properties_for_owner(property_id),
        "total_units": get_total_units_for_property(property_id),
        "monthly_revenue": get_monthly_revenue(property_id),
        "last_added_properties": get_total_number_of_properties_added_in_the_last_30_days_by_owner(
            property_id
        ),
    }


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
                "statistics": get_statistics(data),
            }
        )


class OwnerResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class UnitResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
