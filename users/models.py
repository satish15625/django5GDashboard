# users/models.py
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png')

    def __str__(self):
        return self.user.username

    # Optional method to get avatar URL for login icon or profile display
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default.png'  # fallback if avatar missing


# Signal to automatically create or update Profile when User is created
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()



class Integration(models.Model):
    name = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=(('Success','Success'),('Failed','Failed')))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



class SMTPConfig(models.Model):
    host = models.CharField(max_length=255, default='smtp.gmail.com')
    port = models.IntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    username = models.EmailField()
    password = models.CharField(max_length=255)  # store securely in production
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({'Active' if self.active else 'Inactive'})"