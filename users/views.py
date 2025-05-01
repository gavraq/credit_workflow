from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required
def profile_view(request):
    """View for displaying user profile information."""
    return render(request, 'registration/profile.html')

class ProfileView(LoginRequiredMixin, TemplateView):
    """Class-based view for displaying user profile information."""
    template_name = 'registration/profile.html'
