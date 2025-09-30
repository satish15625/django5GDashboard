from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import UserForm, ProfileForm
from .models import Profile
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from .forms import UserForm, UserUpdateForm, ProfileForm
from .models import Integration  # Assuming you have an Integration model
from django.contrib import messages

from django.core.mail import send_mail
from django.shortcuts import render

from .models import SMTPConfig

@login_required
def dashboard(request):
    # Integration stats
    integrations = Integration.objects.all()  # Or filter by user if normal user
    integration_count = integrations.filter(status='Success').count()

    # For normal users, show only integration stats
    if not request.user.is_superuser:
        return render(request, 'dashboard.html', {
            'integration_count': integration_count,
            'integrations': integrations.filter(created_by=request.user)  # show only their integrations
        })

    # For admin, show user stats too
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users

    return render(request, 'dashboard.html', {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'integration_count': integration_count,
        'integrations': integrations,  # show all
    })


@login_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})


# Only admin can access user creation
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_create(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            
            # Check if profile exists, else create
            profile, created = Profile.objects.get_or_create(user=user)
            # Update profile fields
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            profile.save()

            return redirect('user_list')
    else:
        user_form = UserForm()
        profile_form = ProfileForm()
    return render(request, 'user_form.html', {'user_form': user_form, 'profile_form': profile_form})



@login_required
def user_update(request, id):
    user = get_object_or_404(User, id=id)
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('user_list')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })



@login_required
def profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'users/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important, keeps user logged in
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})


# Only admin can delete users
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_delete(request, id):
    user = get_object_or_404(User, id=id)
    user.delete()
    return redirect('user_list')


@login_required
def percent_integration(request):
    if request.method == 'POST' and request.FILES.get('text_file'):
        text_file = request.FILES['text_file']
        fs = FileSystemStorage()
        filename = fs.save(text_file.name, text_file)
        uploaded_file_url = fs.url(filename)
        return render(request, '5g_integration.html', {'uploaded_file_url': uploaded_file_url})

    return render(request, '5g_integration.html')




def update_avatar(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Avatar updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'users/profile.html', {'form': form})

@login_required
def user_detail(request, id):
    user = get_object_or_404(User, id=id)
    return render(request, 'user_detail.html', {'user': user})


@login_required
def toggle_user_status(request, id):
    if not request.user.is_superuser:
        return redirect('dashboard')

    user = get_object_or_404(User, id=id)

    # Prevent admin from deactivating themselves
    if user == request.user:
        messages.warning(request, "You cannot deactivate your own account!")
        return redirect('user_list')

    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User {user.username} has been {status}.")
    return redirect('user_list')


def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))



def user_login(request):
    if request.method == "POST":
        if "login" in request.POST:  # login form submitted
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect("dashboard")   # replace with your dashboard/home
            else:
                messages.error(request, "Invalid username or password")  # Error message

        elif "reset" in request.POST:  # reset form submitted
            identifier = request.POST.get("identifier")
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=identifier)
                except User.DoesNotExist:
                    messages.error(request, "No user found with that Username/Email")
                    return redirect("login")

            # generate & save new password
            new_password = generate_random_password()
            user.set_password(new_password)
            user.save()

            messages.success(request, f"Password reset successful! New password: {new_password}")
            return redirect("login")

    return render(request, "users/login.html")


def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

def reset_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            # Generate a random password
            new_password = generate_random_password()
            user.set_password(new_password)
            user.save()

            # Send email
            send_mail(
                subject="Your Password Has Been Reset",
                message=f"Hello {user.username},\n\nYour new password is: {new_password}\n\nPlease login and change it immediately.",
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, "A new password has been sent to your email.")
        except User.DoesNotExist:
            messages.error(request, "No user is registered with this email.")
    return render(request, "reset_password.html")



def smtp_config_view(request):
    smtp = SMTPConfig.objects.first()
    if request.method == "POST":
        host = request.POST.get("host")
        port = request.POST.get("port")
        use_tls = request.POST.get("use_tls") == 'on'
        username = request.POST.get("username")
        password = request.POST.get("password")
        active = request.POST.get("active") == 'on'

        if smtp:
            smtp.host = host
            smtp.port = port
            smtp.use_tls = use_tls
            smtp.username = username
            smtp.password = password
            smtp.active = active
            smtp.save()
        else:
            SMTPConfig.objects.create(
                host=host, port=port, use_tls=use_tls,
                username=username, password=password, active=active
            )
        messages.success(request, "SMTP configuration saved successfully.")
        return redirect("smtp_config")

    return render(request, "smtp_config.html", {"smtp": smtp})







