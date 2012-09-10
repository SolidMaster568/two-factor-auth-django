# coding=utf-8
from django.contrib.auth.models import User
from django.contrib.sites.models import get_current_site
from django.core.signing import Signer, BadSignature
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.http import urlencode
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from two_factor.forms import ComputerVerificationForm

signer = Signer()

@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the two factor login action.
    """
    redirect_to = request.REQUEST.get(redirect_field_name, '')

    if request.method == 'POST':
        form = authentication_form(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            params = {
                redirect_field_name: redirect_to,
                'user': signer.sign(user.pk),
            }
            return HttpResponseRedirect(
                '/accounts/verify/?' + urlencode(params)
            )

    else:
        form = authentication_form(request)

    request.session.set_test_cookie()

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
        current_app=current_app)

@sensitive_post_parameters()
@csrf_protect
@never_cache
def verify_computer(request, template_name='registration/verify_computer.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          computer_verification_form=ComputerVerificationForm,
          current_app=None, extra_context=None):
    redirect_to = request.REQUEST.get(redirect_field_name, '')

    try:
        user = User.objects.get(pk=signer.unsign(request.GET.get('user')))
    except (User.DoesNotExist, BadSignature):
        return HttpResponseRedirect('/accounts/login/')

    if request.method == 'POST':
        form = computer_verification_form(user=user, data=request.POST)
        if form.is_valid():
            # Use default setting if redirect_to is empty
            if not redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Heavier security check -- don't allow redirection to a different
            # host.
            elif netloc and netloc != request.get_host():
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Okay, security checks complete. Log the user in.
            auth_login(request, user)

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            return HttpResponseRedirect(redirect_to)
    else:
        form = computer_verification_form(request, user)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
        current_app=current_app)