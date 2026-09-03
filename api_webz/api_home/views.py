from django.http import HttpResponse
from django.shortcuts import render, redirect 


#program imports
from .auth import authenticate_user

TESTING = False  # set false for production
# recent change
HOME_TEMPLATE = "api_home/index.html"
WEEK_TEMPLATE = "api_home/week.html"
LOGIN_TEMPLATE = "login.html"
ERROR_TEMPLATE = "error.html"


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            return render(
                request, LOGIN_TEMPLATE, {"error": "Both fields are required"}
            )

        # bypass LDAP
        if TESTING:
            if username == "abc@xyz.com" and password == "1234":
                request.session["username"] = username
                request.session.set_expiry(3600)
                return redirect("home")

            return render(
                request, LOGIN_TEMPLATE, {"error": "Invalid test credentials"}
            )

        auth_response = authenticate_user(username, password)

        if auth_response.get("success"):
            request.session["username"] = username
            request.session.set_expiry(3600)  # 1 hour config karo

            return redirect("home")

        else:
            return render(
                request,
                LOGIN_TEMPLATE,
                {"error": auth_response.get("message", "Authentication failed")},
            )

    return render(request, LOGIN_TEMPLATE)

def logout_view(request):
    request.session.flush()
    return redirect("login")


def check_auth(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        username = request.session.get("username")
        if not username:
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


@check_auth
def index(request):
    print(HOME_TEMPLATE)
    username = request.session.get("username")
    return render(request,HOME_TEMPLATE, {"username": username})

@check_auth
def week(request):
    return render(request,WEEK_TEMPLATE,{"username": request.session.get("username")})



def logout_view(request):
    request.session.flush()
    # request.session.clear()
    return redirect("login")
