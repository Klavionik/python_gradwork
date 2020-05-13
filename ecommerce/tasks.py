from celery import shared_task

from ecommerce.emails import order_confirmation_mail


@shared_task
def send_order_confirmation(order_id, email):
    email = order_confirmation_mail(order_id, email)
    email.send()
