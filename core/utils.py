from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status

class MultiSerializerViewSetMixin:
    """
    Mixin to use different serializers for different actions
    """
    serializers = {
        'default': None,
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])

class PaginationMixin:
    """
    Mixin to add pagination to viewsets
    """
    paginate_by = 25
    paginate_by_param = 'page_size'
    max_paginate_by = 100

class QueryFilterMixin:
    """
    Mixin to add query filtering to viewsets
    """
    filter_fields = []
    search_fields = []

    def get_queryset(self):
        queryset = super().get_queryset()
        query_params = self.request.query_params

        # Field filtering
        for field in self.filter_fields:
            if field in query_params:
                queryset = queryset.filter(**{field: query_params[field]})

        # Search filtering
        if 'search' in query_params and self.search_fields:
            search_query = query_params['search']
            search_filters = Q()
            for field in self.search_fields:
                search_filters |= Q(**{f'{field}__icontains': search_query})
            queryset = queryset.filter(search_filters)

        return queryset

def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses
    """
    from rest_framework.views import exception_handler
    
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'status': 'error',
            'code': response.status_code,
            'message': 'An error occurred',
            'details': response.data
        }
        response.data = custom_response

    return response

def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Standard success response format
    """
    response_data = {
        'status': 'success',
        'message': message,
    }
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)

def error_response(message="An error occurred", details=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Standard error response format
    """
    response_data = {
        'status': 'error',
        'message': message,
    }
    if details is not None:
        response_data['details'] = details
    return Response(response_data, status=status_code)