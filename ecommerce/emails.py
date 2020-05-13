from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def order_confirmation_mail(order_id, email):
    context = {
        'order': order_id
    }

    message = EmailMessage()
    message.content_subtype = 'html'
    message.subject = 'E-Commerce: подтверждение заказа'
    message.body = render_to_string('order_confirmation.html', context)
    message.to = [email]
    return message
