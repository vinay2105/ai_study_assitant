import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser
from .forms import SignUpForm, OTPForm
from django.contrib.auth.decorators import login_required

# -----------------------------
# Signup View (Session Based)
# -----------------------------
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Save cleaned data to session
            request.session['signup_data'] = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password1'],  # password1 from UserCreationForm
            }

            # Generate OTP and store in session
            otp = str(random.randint(100000, 999999))
            request.session['signup_otp'] = otp

            # Send OTP email
            send_mail(
                subject="Your StudyAssistant OTP",
                message=f"Your OTP is {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[form.cleaned_data['email']],
            )

            return redirect('verify_otp')
    else:
        form = SignUpForm()

    return render(request, 'signup.html', {'form': form})

# -----------------------------
# OTP Verification View
# -----------------------------
def verify_otp_view(request):
    signup_data = request.session.get('signup_data')
    otp = request.session.get('signup_otp')

    if not signup_data or not otp:
        return redirect('signup')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if entered_otp == otp:
                # Create and activate user
                user = CustomUser.objects.create_user(
                    username=signup_data['username'],
                    email=signup_data['email'],
                    password=signup_data['password']
                )
                user.is_active = True
                user.is_verified = True
                user.save()

                # Clean up session and login
                del request.session['signup_data']
                del request.session['signup_otp']
                login(request, user)
                return redirect('home')
            else:
                form.add_error('otp', 'Invalid OTP')
    else:
        form = OTPForm()

    return render(request, 'otp_verify.html', {'form': form})

# -----------------------------
# Login View (Optional Custom)
# -----------------------------
class CustomLoginView(LoginView):
    template_name = 'login.html'

# -----------------------------
# Logout View
# -----------------------------
def logout_view(request):
    logout(request)
    return redirect('login')

# -----------------------------
# Home View (Protected)
# -----------------------------
@login_required(login_url='login')
def home(request):
    return render(request, 'home.html')



