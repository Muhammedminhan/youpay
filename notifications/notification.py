import logging

from core.mail_engine_base import MailEngineClient

logger = logging.getLogger(__name__)


class MailAlertView(MailEngineClient):

    def __init__(self, *args, **kwargs):
        super(MailAlertView, self).__init__()
        self.subject = str(kwargs.get('subject'))
        self.template_code = kwargs.get('template_code')
        self.mail_from = kwargs.get('mail_from')
        self.mail_to = kwargs.get('mail_to')
        self.template_data = kwargs.get('template_data')
        self.mail_engine_api = kwargs.get('mail_engine_api')

    def send_mail(self):
        """
        Method will trigger mail engine send mail post request
        with generated otp
        """
        mail_client = MailEngineClient()
        send_mail_url = self.mail_engine_api
        send_mail_payload = {
            "subject": self.subject,
            "mail_from": self.mail_from,
            "mail_to": self.mail_to,
            "template_data": self.template_data,
            "template_code": self.template_code,
        }

        logger.info("Mail payload {}".format(send_mail_payload))
        response_data = mail_client.service_post(send_mail_url,
                                                 send_mail_payload)
        logger.info("Response from mail engine with payload"
                    " {} is {}".format(send_mail_payload, response_data))

        if response_data.get('status_code') == 200:
            return response_data
        else:
            return None
