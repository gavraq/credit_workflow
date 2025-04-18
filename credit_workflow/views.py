from django.shortcuts import render

def welcome(request):
    return render(request, 'credit_workflow/welcome.html')
