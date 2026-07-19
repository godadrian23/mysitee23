from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="vocab_home"),
    path("api/words/", views.words_json, name="vocab_words"),
]
