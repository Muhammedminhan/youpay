from django.db import models

# Create your models here.

class AbstractDateTime(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AbstractPayBack(AbstractDateTime):
    request_id = models.CharField(max_length=50, db_index=True, unique=True)
    invoice = models.CharField(max_length=50)
    reference_id = models.CharField(max_length=50, db_index=True)
    platform = models.CharField(max_length=50,null=True, blank=True)
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='Denotes the actual amount to pay')
    currency = models.CharField(null=True, blank=True, max_length=10,
                                help_text='Denotes the actual currency to pay')
    amount_in_aed = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='Denotes converted amount to AED')
    redemption_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='amount to redeem from b2c payback')
    redeemed_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='amount which is redeemed on '
                                         'b2c payback')
    redeemed_points = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='points which is redeemed by '
                                         'b2c payback')
    redemption_method = models.CharField(max_length=50, null=True, blank=True,)
    customer_email = models.CharField(max_length=500, null=True, blank=True)
    available_points = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='Available points for the card')
    available_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True, help_text='Available amounts for the card')
    is_full_redemption = models.BooleanField(
        db_index=True, null=True, blank=True,
        help_text='Denotes whether the redemption is full or not.')
    redemption_status = models.BooleanField(
        default=False,
        help_text='Denotes the redemption is completed')

    class Meta:
        abstract = True


class QitafPayment(AbstractPayBack):
    branch_id = models.CharField(max_length=20, null=True, blank=True,
                                 help_text="Unique id of branch")
    MSISDN = models.CharField(max_length=100, null=True, blank=True,
                              help_text="Customer’s GSM phone number")
    request_date = models.CharField(max_length=100, null=True, blank=True,
                                    help_text="Date of request (24-Hour)")
    request_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Unique id of redemption transaction")
    terminal_id = models.CharField(max_length=100, null=True, blank=True,
                                   help_text="Unique id of terminal")
    ref_request_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="reference id of redemption transaction")
    language_code = models.CharField(max_length=100, null=True, blank=True,
                                     help_text="Language code like ‘en-US’")
    is_reversed = models.BooleanField(default=False, null=True, blank=True,
                                      help_text="Is transaction reversed")
