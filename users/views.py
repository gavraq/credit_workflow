from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

@login_required
def profile_view(request):
    """View for displaying user profile information."""
    return render(request, 'registration/profile.html')

class ProfileView(LoginRequiredMixin, TemplateView):
    """Class-based view for displaying user profile information."""
    template_name = 'registration/profile.html'


@csrf_protect
@require_http_methods(["GET", "POST"])
def custom_logout(request):
    """Custom logout view that handles both GET and POST requests."""
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    else:
        # For GET requests, show a confirmation page with a form that will POST
        return render(request, 'registration/logout_confirm.html')
