from django.urls import path
from . import views
from .views import DashboardView
from .views_wizard import CreditRequestWizard
from .views_sponsorship import BusinessSponsorshipView
from workflow.views import transition_request
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    
    # Credit Request Wizard URLs
    path('credit-request/wizard/', CreditRequestWizard.as_view(), name='creditrequest_wizard'),
    path('credit-request/wizard/<int:pk>/', CreditRequestWizard.as_view(), name='creditrequest_wizard_edit'),
    
    # Legacy URLs (redirected to wizard)
    path('credit-request/new/', RedirectView.as_view(pattern_name='creditrequest_wizard', permanent=False), 
         name='creditrequest_create'),
    path('credit-request/<int:pk>/edit/', RedirectView.as_view(pattern_name='creditrequest_wizard_edit', permanent=False), 
         name='creditrequest_edit'),
    
    # Assigned requests view
    path('assigned-requests/', views.AssignedRequestsView.as_view(), name='assigned_requests'),
    
    # Other existing URLs
    path('credit-review/<int:pk>/', views.CreditReviewUpdateView.as_view(), name='creditreview_edit'),
    path('credit-request/<int:pk>/', views.CreditRequestDetailView.as_view(), name='creditrequest_detail'),
    path('credit-request/', views.CreditRequestListView.as_view(), name='creditrequest_list'),
    
    # Business Sponsorship URL
    path('credit-request/<int:pk>/sponsor/', BusinessSponsorshipView.as_view(), name='business_sponsorship'),
    
    # Workflow transition URL
    path('credit-request/<int:credit_request_id>/transition/<int:to_state_id>/', transition_request, name='transition_request'),
    
    # Questionnaire URLs
    path('questionnaire/new/', views.CreditQuestionnaireCreateView.as_view(), name='creditquestionnaire_create'),
    path('questionnaire/<int:pk>/edit/', views.CreditQuestionnaireUpdateView.as_view(), name='creditquestionnaire_edit'),
    
    # Legal Review URLs
    path('legalreview/new/', views.LegalReviewCreateView.as_view(), name='legalreview_create'),
    path('legalreview/<int:pk>/edit/', views.LegalReviewUpdateView.as_view(), name='legalreview_edit'),
    
    # Document URLs
    path('documents/upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('documents/<int:credit_request_id>/', views.DocumentListView.as_view(), name='document_list'),
    
    # Notification URLs
    path('notifications/', views.NotificationCenterView.as_view(), name='notification_center'),
    path('notification-preferences/', views.NotificationPreferencesView.as_view(), name='notification_preferences'),
    path('notifications/<int:pk>/mark-read/', views.NotificationMarkReadView.as_view(), name='notification_mark_read'),
    
    # Debug URLs (for troubleshooting only)
    path('debug/questionnaire/<int:pk>/', views.DebugQuestionnaireView.as_view(), name='debug_questionnaire'),
    path('notifications/<int:pk>/dismiss/', views.NotificationDismissView.as_view(), name='notification_dismiss'),
    path('notifications/mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notifications_mark_all_read'),
    
    # Credit Analysis URLs
    path('creditanalysis/new/', views.CreditAnalysisCreateView.as_view(), name='creditanalysis_create'),
    path('creditanalysis/<int:pk>/edit/', views.CreditAnalysisUpdateView.as_view(), name='creditanalysis_edit'),
    path('creditanalysis/<int:pk>/', views.CreditAnalysisDetailView.as_view(), name='creditanalysis_detail'),
    
    # --- API endpoints ---
    path('api/notifications/', views.NotificationListAPI.as_view(), name='api_notification_list'),
    path('api/notifications/<int:pk>/mark-read/', views.NotificationMarkReadAPI.as_view(), name='api_notification_mark_read'),
    path('api/notifications/<int:pk>/dismiss/', views.NotificationDismissAPI.as_view(), name='api_notification_dismiss'),
]