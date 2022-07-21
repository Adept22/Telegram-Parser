from django.conf import settings
from post_office import mail
from post_office.models import EmailTemplate


def send_templated_mail(template_name, context, recipients, sender=None, cc=None):
    if not sender:
        sender = settings.DEFAULT_FROM_EMAIL
    try:
        t = EmailTemplate.objects.get(name__iexact=template_name)
    except EmailTemplate.DoesNotExist:
        print(u"Error: EmailTemplate '{}' does not exist!".format(template_name))
        return False
    mail.send(
        recipients=recipients,
        sender=sender,
        context=context,
        template=t,
        cc=cc,
    )
    return True

