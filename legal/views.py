from django.shortcuts import render


def privacy(request):
    return render(request, "legal/privacy.html")


def terms(request):
    return render(request, "legal/terms.html")


def disclaimer(request):
    return render(request, "legal/disclaimer.html")

# Create your views here.
