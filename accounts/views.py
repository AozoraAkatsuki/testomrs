from django.shortcuts import render, redirect
import operator
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.forms import inlineformset_factory
from django.contrib.auth.forms import PasswordChangeForm

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from accounts.models import Movie, OnlineLink
from accounts.recommendations import load_recommendations
from functools import reduce
from django.db.models import Q
import json

# Create your views here.
from .models import *
from .forms import CreateUserForm, EditProfile


def registerPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        form = CreateUserForm()
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()
                user = form.cleaned_data.get('username')

                messages.success(request, 'Account was created for ' + user)
                return redirect('login')

        context = {'form': form}
        return render(request, 'accounts/register.html', context)


def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.info(request, 'Username OR password is incorrect')

        context = {}
        return render(request, 'accounts/login.html', context)


def logoutUser(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home(request):
    return render(request, 'accounts/dashboard.html')


@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfile(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = EditProfile(instance=request.user)
        args = {'form': form}
        return render(request, 'accounts/edit_profile.html', args)


@login_required(login_url='login')
def change_pass(request):
    if request.method == "POST":
        fm = PasswordChangeForm(user=request.user, data=request.POST)
        if fm.is_valid():
            fm.save()
            update_session_auth_hash(request, fm.user)
            return HttpResponseRedirect('/')
    else:
        fm = PasswordChangeForm(user=request.user)
    return render(request, 'accounts/password_change.html', {'form': fm})


# new functions
def search_movies(request):
    query = request.get('search_query')
    movies = Movie.objects.all()
    query_elements = query.split()
    filtered = movies.filter(reduce(operator.and_, (Q(title__icontains=q) for q in query_elements)))
    return {'search_results': filtered}


def detail(request, movie_id):
    if request.method == 'GET' and len(request.GET) > 0:
        search_results = search_movies(request.GET)
        return render(request, 'home.html', context=search_results)

    movie_object = Movie.objects.get(movie_id=movie_id)
    links = OnlineLink.objects.get(movie_id=movie_object.movie_id)

    imdb_link = '0' * (7 - len(links.imdb_id)) + links.imdb_id

    movie_detail = {
        'movie': {
            'id': movie_object.movie_id,
            'name': movie_object.title,
            'genres': movie_object.genres,
            'rating': movie_object.rating_mean,
            'liked': movie_object.liked,
            'comparable': movie_object.comparable,
        },
        'links': {
            'imdb': imdb_link,
            'youtube': links.youtube_id,
            'tmdb': links.tmdb_id
        },
        'detail': 'active',
    }
    return render(request, 'movie_detail.html', context=movie_detail)


def rate(request, movie_id):
    movie = Movie.objects.get(pk=movie_id)
    if 'liked' in request.POST:
        movie.liked = 1
    elif 'disliked' in request.POST:
        movie.liked = 0
    elif 'reset' in request.POST:
        movie.liked = None

    movie.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def recommendations(request):
    if request.method == 'GET' and len(request.GET) > 0:
        search_results = search_movies(request.GET)
        return render(request, '/', context=search_results)

    liked, not_liked = load_recommendations()
    context = {
        'recommendations': 'active',
        'liked': liked,
        'not_liked': not_liked,
    }
    return render(request, 'accounts/dashboard.html', context=context)
