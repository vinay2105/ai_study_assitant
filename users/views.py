import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser
from .forms import SignUpForm, OTPForm

# Signup view
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # user can't login until verified
            user.save()

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.save()

            # Send OTP email
            send_mail(
                subject="Your StudyAssistant OTP",
                message=f"Your OTP is {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
            )

            request.session['otp_user_id'] = user.id
            return redirect('verify_otp')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


# OTP verification
def verify_otp_view(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('signup')
    user = CustomUser.objects.get(id=user_id)

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if user.otp == entered_otp:
                user.is_active = True
                user.is_verified = True
                user.otp = None
                user.save()
                login(request, user)
                return redirect('home')
            else:
                form.add_error('otp', 'Invalid OTP')
    else:
        form = OTPForm()

    return render(request, 'otp_verify.html', {'form': form})


# Login view (can also use Django's built-in LoginView)
class CustomLoginView(LoginView):
    template_name = 'login.html'


# Logout
def logout_view(request):
    logout(request)
    return redirect('login')

from django.contrib.auth.decorators import login_required

@login_required(login_url='login')  # redirect to login if not authenticated
def home(request):
    return render(request, 'home.html')


