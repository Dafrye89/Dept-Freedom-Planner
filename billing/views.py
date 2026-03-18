from django.shortcuts import render


def pricing(request):
    return render(request, "billing/pricing.html")

# Create your views here.
