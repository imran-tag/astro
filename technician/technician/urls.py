"""
URL configuration for technician project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# technician/urls.py
# technician/urls.py
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.http import HttpResponse
from django.conf.urls.static import static
from portal.views import (LoginView, LogoutView, InterventionListView, InterventionDetailView,
                         InterventionUpdateStatusView, SecurityChecklistView,
                         PhotoUploadView, PhotosAfterView, CommentView, QualityControlView,
                         SignatureView, FinishInterventionView, GetInterventionFilesView)

def test_view(request):
    return HttpResponse("Django is working!")

urlpatterns = [
                  path('test/', test_view, name='test'),
                  path('', InterventionListView.as_view(), name='home'),  # Add this for root URL
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('interventions/', InterventionListView.as_view(), name='interventions'),
    path('interventions/<str:intervention_id>/update_status/',
         InterventionUpdateStatusView.as_view(),
         name='intervention_update_status'),
    path('interventions/<str:intervention_id>/', InterventionDetailView.as_view(), name='intervention_detail'),
    path('interventions/<str:intervention_id>/security-checklist/',
         SecurityChecklistView.as_view(),
         name='security_checklist'),
    path('interventions/<str:intervention_id>/photo-upload/',
         PhotoUploadView.as_view(),
         name='photo_upload'),
    path('interventions/<str:intervention_id>/photos-after/',
         PhotosAfterView.as_view(),
         name='photos_after'),
    path('interventions/<str:intervention_id>/comment/',
     CommentView.as_view(),
     name='comment'),
path('interventions/<str:intervention_id>/quality-control/',
     QualityControlView.as_view(),
     name='quality_control'),
path('interventions/<str:intervention_id>/signature/',
         SignatureView.as_view(),
         name='signature'),
    path('interventions/<str:intervention_id>/finish/',
         FinishInterventionView.as_view(),
         name='finish_intervention'),
path('interventions/<str:intervention_id>/files/',
         GetInterventionFilesView.as_view(),
         name='get_intervention_files'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)