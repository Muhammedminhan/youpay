import json
import logging

import requests
from django.conf import settings
from rest_framework import status

from amazonpgclient.constants import PAYMENT_STATUS_ERROR
from core.constants import PAYMENT_GATEWAY_APPLEPAY, REQUEST_METHOD_POST
from integrations.constants import (APPLE_PAY_HUB_CODE,
                                    PAYMENT_REQUEST_TYPE_PAYMENT,
                                    PAYMENT_REQUEST_GENERATE_TOKEN,
                                    PAYMENT_REQUEST_VALIDATE_SESSION,
                                    APPLE_PAY_AED_KEY_PATH,
                                    APPLE_PAY_SANDBOX_AED_CERTIFICATE_PATH,
                                    APPLE_PAY_SANDBOX_SAR_CERTIFICATE_PATH,
                                    APPLE_PAY_PRODUCTION_AED_CERTIFICATE_PATH,
                                    APPLE_PAY_PRODUCTION_SAR_CERTIFICATE_PATH,
                                    APPLE_PAY_SAR_KEY_PATH)
from services.constants import (APPLEPAY_MERCHANT_IDENTIFIER,
                                APPLEPAY_DOMAIN_NAME, APPLEPAY_DISPLAY_NAME)
from services.v1.views.payment import PaymentRequestView
from services.v1.views.payment_handlers import PaymentHandlers

logger = logging.getLogger(__name__)


class ApplePayManager(PaymentRequestView, PaymentHandlers):

    def __init__(self):
        self.transaction_id = None
        self.payment_method = None
        self.payment_gateway = PAYMENT_GATEWAY_APPLEPAY
        self.payment_status = None
        self.payment_reference = None
        self.channel_code = None
        self.request_data = None
        self.response_data = None
        self.request_type = None
        self.request_method = None
        self.transaction_obj = None

    def configure_certificate(self, currency):
        logger.info(
            "Configuring certificate for currency {}".format(currency))
        logger.info("Environment : {}".format(settings.ENVIRONMENT))

        environment = settings.ENVIRONMENT

        return_dict = {}
        message = None
        status = True
        certificate = None
        key = None

        if environment == 'production':
            if currency == 'AED':
                certificate = APPLE_PAY_PRODUCTION_AED_CERTIFICATE_PATH
                key = APPLE_PAY_AED_KEY_PATH
            elif currency == "SAR":
                certificate = APPLE_PAY_PRODUCTION_SAR_CERTIFICATE_PATH
                key = APPLE_PAY_SAR_KEY_PATH
            else:
                message = "Invalid currency or not provided"
                status = False


        elif environment == 'sandbox':
            if currency == 'AED':
                certificate = APPLE_PAY_SANDBOX_AED_CERTIFICATE_PATH
                key = APPLE_PAY_AED_KEY_PATH
            elif currency == "SAR":
                certificate = APPLE_PAY_SANDBOX_SAR_CERTIFICATE_PATH
                key = APPLE_PAY_AED_KEY_PATH
            else:
                message = ("unsupported currency or not provided, got {}"
                           "".format(currency))
                status = False

        else:
            message = "Invalid environment, got '{}' ".format(environment)
            status = False

        return_dict['certificate'] = certificate
        return_dict['key'] = key
        return_dict['message'] = message
        return_dict['status'] = status

        logger.info("Certificate path : {}".format(certificate))
        logger.info("Key path : {}".format(key))

        return return_dict

    def validate_session(self, request_data):
        transaction_data = request_data.get('transaction_data')

        self.request_data = request_data.get('request_data')
        self.request_method = REQUEST_METHOD_POST
        self.request_type = PAYMENT_REQUEST_VALIDATE_SESSION
        self.transaction_id = transaction_data.get(
            'transaction_id')
        self.payment_method = request_data.get('payment_method')
        self.channel_code = APPLE_PAY_HUB_CODE
        self.transaction_obj = request_data.get('transaction_obj')

        logger.info("APPLE PAY Validating session {} ".format(
            self.transaction_obj.currency))

        """if transaction is verified then proceed with payment"""
        try:
            # get apple url from request body
            applepay_url = request_data.get('request_data').get(
                'applepayUrl')

            payload = {
                "merchantIdentifier": APPLEPAY_MERCHANT_IDENTIFIER,
                "domainName": APPLEPAY_DOMAIN_NAME,
                "displayName": APPLEPAY_DISPLAY_NAME,
            }

            logger.info("\n\nAPPLE PAY Validating session payload {} ".format(
                payload))

            # certificate secret and key
            response_dict = self.configure_certificate(
                self.transaction_obj.currency)
            print("Response dict : {}".format(response_dict))
            if response_dict['status']:
                certificate = response_dict['certificate']
                key = response_dict['key']
                cert_file = (certificate, key)
            else:
                logger.error("Error in configuring certificate : {}".format(
                    response_dict['message']))
                return ({"error": response_dict['message']},
                        self.APPLE_PAY_CONNECTION_ERROR)

            verify_response, verify_status = self.verify_transaction(
                transaction_data)
            logger.info("Verify response: {} - {}"
                        .format(verify_status, verify_response))

            payment_data_to_send = json.dumps(payload)
            logger.info("Youpay to applepay url : {}, data : {} "
                        .format(applepay_url, payload))

            # make request to applepay url
            response = requests.post(applepay_url,
                                     json=payment_data_to_send,
                                     cert=cert_file,
                                     headers={})
            whole_data = {
                "body": payload,
                "cert_file": cert_file,
            }

            logger.info(
                "Applepay validate session request response for "
                "transaction id {} is {}".format(self.transaction_id,
                                                 response))
            if response:
                self.response_data = {"response_data": response.json()}
                response_code = self.SUCCESS
            else:
                self.response_data = {"error": str(response),
                                      "response_data": str(response.text)}
                response_code = self.APPLE_PAY_CONNECTION_ERROR

            # storing Youpay to payment gateway request and response data
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=json.dumps(whole_data),
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=self.request_type,
            )

            return self.response_data, response_code

        except Exception as e:
            msg = (
                "Error while processing validating session for transaction "
                "id {}, err : {}".format(self.transaction_id, str(e)))
            logger.error(msg)
            return {"error": msg}, self.APPLE_PAY_CONNECTION_ERROR

    def pay(self, request_data):
        # Step 1 : Generate Token
        # Step 2 : Send Token to Apple Pay

        logger.info("APPLE PAY Paying")
        transaction_data = request_data.get('transaction_data')

        self.request_data = request_data.get('request_data')
        self.request_method = REQUEST_METHOD_POST
        self.request_type = 'validate_session'
        self.transaction_id = transaction_data.get(
            'transaction_id')
        self.payment_method = request_data.get('payment_method')
        self.channel_code = APPLE_PAY_HUB_CODE
        self.transaction_obj = request_data.get('transaction_obj')

        verify_response, verify_status = self.verify_transaction(
            transaction_data)
        logger.info(
            "Verify response: {} - {}".format(verify_status,
                                              verify_response))
        is_verified = verify_response.get('is_verified', False)

        """if transaction is verified then proceed with payment"""
        try:
            if verify_status == status.HTTP_200_OK and is_verified:

                """
                Step 1: Generate a Checkout.com token from the Apple Pay token
                """
                generate_token_response, response_code = self.generate_applepay_token()
                logger.info("Applepay generate token response for "
                            "transaction id {} is {}".format(
                    self.transaction_id, generate_token_response))

                """
                Step 2: Request a payment with the token 
                """
                request_payment_response, response_code = self.request_payment()
                logger.info(
                    "Applepay pay request response for transaction id {},is"
                    " {}".format(self.transaction_id,
                                 request_payment_response))

                if response_code == self.SUCCESS:
                    logger.info(
                        "Applepay validate session request response for "
                        "transaction id {} is {}".format(
                            self.transaction_id,
                            request_payment_response))
                    self.response_data = {
                        "error": str(request_payment_response)}
                    response_code = self.SUCCESS
                else:
                    logger.error(
                        "Error in applepay payment , {}".format(
                            request_payment_response))
                    self.response_data = {
                        "error": str(request_payment_response)}
                    response_code = self.APPLE_PAY_CONNECTION_ERROR

                return self.response_data, response_code

            else:
                msg = (
                    "Youpay transaction verification failed for transaction id "
                    "{} response is : {} ".format(self.transaction_id,
                                                  verify_response))
                logger.error(msg)
                return None, self.CLIENT_TRANSACTION_VERIFICATION_FAILED
        except Exception as e:
            error_msg = "Error while processing applepay payment for transaction id {}, err : {}".format(
                self.transaction_id, str(e))
            logger.error(error_msg)
            return {"error": error_msg}, self.APPLE_PAY_CONNECTION_ERROR

        finally:
            data_to_update = {
                'transaction_id': self.transaction_id,
                "payment_status": self.payment_status,
                "payment_reference": self.payment_reference,
                "payment_gateway": self.payment_gateway,
                "channel_code": self.channel_code,
                "payment_method": self.payment_method,
            }
            self.update_youpay_transaction_data(data_to_update)

    def generate_applepay_token(self):
        try:

            # TODO - Move this to serializer
            payload = {
                "type": "applepay",
                "token_data": {
                    "version": "EC_v1",
                    "data": "t7GeajLB9skXB6QSWfEpPA4WPhDqB7ekdd+F7588arLzvebKp3P0TekUslSQ8nkuacUgLdks2IKyCm7U3OL/PEYLXE7w60VkQ8WE6FXs/cqHkwtSW9vkzZNDxSLDg9slgLYxAH2/iztdipPpyIYKl0Kb6Rn9rboF+lwgRxM1B3n84miApwF5Pxl8ZOOXGY6F+3DsDo7sMCUTaJK74DUJJcjIXrigtINWKW6RFa/4qmPEC/Y+syg04x7B99mbLQQzWFm7z6HfRmynPM9/GA0kbsqd/Kn5Mkqssfhn/m6LuNKsqEmbKi85FF6kip+F17LRawG48bF/lT8wj/QEuDY0G7t/ryOnGLtKteXmAf0oJnwkelIyfyj2KI8GChBuTJonGlXKr5klPE89/ycmkgDl+T6Ms7PhiNZpuGEE2QE=",
                    "signature": "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",
                    "header": {
                        "ephemeralPublicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEX1ievoT8DRB8T5zGkhHZHeDr0oBmYEgsDSxyT0MD0IZ2Mpfjz2LdWq6LUwSH9EmxdPEzMunsZKWMyOr3K/zlsw==",
                        "publicKeyHash": "tqYV+tmG9aMh+l/K6cicUnPqkb1gUiLjSTM9gEz6Nl0=",
                        "transactionId": "3cee89679130a4b2617c76118a1c62fd400cd45b49dc0916d5b951b560cd17b4"
                    }
                }
            }
            self.request_data = json.dumps(payload)
            # url = "https://api.checkout.com/tokens"
            url = "https://api.sandbox.checkout.com/tokens"
            response = requests.post(url, data=self.request_data, headers={})
            logger.info("Applepay Generate token response for "
                        "transaction id {} is {}".format(
                self.transaction_id, response))

            if response:
                logger.info(
                    "Applepay Generate token response for "
                    "transaction id {} is {}".format(self.transaction_id,
                                                     response.text))
                self.response_data = response.text
                response_code = self.SUCCESS
            else:
                logger.error("Error in apple pay generate token, {}".format(
                    response))
                self.payment_status = PAYMENT_STATUS_ERROR
                self.response_data = {"error": str(response)}
                response_code = self.APPLE_PAY_CONNECTION_ERROR

            success_response_sample = {
                "type": "applepay",
                "token": "tok_ymu4qlccztkedmd6b7c3hcf6ae",
                "expires_on": "2019-10-21T10:48:35Z",
                "expiry_month": 8,
                "expiry_year": 2023,
                "scheme": "Visa",
                "last4": "6222",
                "bin": "481891",
                "card_type": "Debit",
                "card_category": "Consumer",
                "issuer": "HSBC BANK PLC",
                "issuer_country": "GB",
                "product_id": "F",
                "product_type": "Visa Classic"
            }
            return success_response_sample, response_code
        except Exception as e:
            logger.error("Error in generating apple pay token, {}".format(
                str(e)))
            return None, self.APPLE_PAY_CONNECTION_ERROR
        finally:
            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=self.request_data,
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_GENERATE_TOKEN,
            )

    def request_payment(self):
        try:
            # url = "https://api.checkout.com/payments"
            url = "https://api.sandbox.checkout.com/payments"
            payload = {
                "source": {
                    "type": "token",
                    "token": "tok_ymu4qlccztkedmd6b7c3hcf6ae"
                },
                "amount": 6500,
                "currency": "USD"
            }
            self.request_data = json.dumps(payload)
            response = requests.post(url, data=self.request_data, headers={})
            if response:
                self.response_data = {"response_data": response.json()}
                response_code = self.SUCCESS
            else:
                self.response_data = {"response_data": str(response)}
                response_code = self.APPLE_PAY_CONNECTION_ERROR

            return self.response_data, response_code
        except Exception as e:
            self.response_data = {"response_data": str(e)}
            logger.error("Error in apple pay payment, {}".format(str(e)))
            return self.response_data, self.APPLE_PAY_CONNECTION_ERROR
        finally:

            self.create_youpay_to_payment_gateways_data(
                transaction_obj=self.transaction_obj,
                transaction_id=self.transaction_id,
                request_data=self.request_data,
                response_data=json.dumps(self.response_data),
                request_method=REQUEST_METHOD_POST,
                request_type=PAYMENT_REQUEST_TYPE_PAYMENT,
            )

# pip install pyngrok
