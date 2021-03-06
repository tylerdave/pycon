from decimal import Decimal
import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _


SEX_NO_ANSWER = 0
SEX_CHOICES = (
    (SEX_NO_ANSWER, '-'),
    (1, _('Female')),
    (2, _('Male')),
)

PRESENTING_CHOICES = (
    (1, _("Yes")),
    (2, _("No")),
    (3, _("I have applied but don't know yet")),
)

STATUS_SUBMITTED = 1
STATUS_WITHDRAWN = 2
STATUS_INFO_NEEDED = 3
STATUS_OFFERED = 4
STATUS_REJECTED = 5
STATUS_DECLINED = 6
STATUS_ACCEPTED = 7
STATUS_NEED_MORE = 8

STATUS_CHOICES = (
    (STATUS_SUBMITTED, _(u"Submitted")),
    (STATUS_WITHDRAWN, _(u"Withdrawn")),
    (STATUS_INFO_NEEDED, _(u"Information needed")),
    (STATUS_OFFERED, _(u"Offered")),
    (STATUS_NEED_MORE, _(u"Requesting more funds")),
    (STATUS_REJECTED, _(u"Rejected")),
    (STATUS_DECLINED, _(u"Declined")),
    (STATUS_ACCEPTED, _(u"Accepted"))
)

PAYMENT_CHECK = 1
PAYMENT_WIRE = 2
PAYMENT_PAYPAL = 3
PAYMENT_CHOICES = (
    (PAYMENT_CHECK, _(u"Check")),
    (PAYMENT_WIRE, _(u"Wire Transfer")),
    (PAYMENT_PAYPAL, _(u"PayPal")),
)

PYTHON_EXPERIENCE_BEGINNER = "Beginner"
PYTHON_EXPERIENCE_INTERMEDIATE = "Intermediate"
PYTHON_EXPERIENCE_EXPERT = "Expert"
PYTHON_EXPERIENCE_CHOICES = (
    (PYTHON_EXPERIENCE_BEGINNER, _("Beginner")),
    (PYTHON_EXPERIENCE_INTERMEDIATE, _("Intermediate")),
    (PYTHON_EXPERIENCE_EXPERT, _("Expert")),
)


class FinancialAidApplication(models.Model):
    # The primary key ('id') is used as application number
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    last_update = models.DateTimeField(auto_now=True, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                related_name='financial_aid', db_index=True)

    pyladies_grant_requested = models.BooleanField(
        default=False,
        verbose_name=_("PyLadies grant"),
        help_text=_("Would you like to be considered for a "
                    "PyLadies grant? (Women only.)"))

    international = models.BooleanField(
        default=False,
        verbose_name=_("International"),
        help_text=_("Will you be traveling internationally?"))
    amount_requested = models.DecimalField(
        verbose_name=_("Amount"),
        help_text=_("Please enter the amount of assistance you "
                    "need, in US dollars."),
        decimal_places=2, max_digits=8, default=Decimal("0.00"))
    travel_plans = models.CharField(
        verbose_name=_("Travel plans"),
        max_length=1024,
        help_text=_("Please describe your travel plans, "
                    " including the country you will travel from."))

    profession = models.CharField(
        verbose_name=_("Profession"),
        help_text=_("What is your career, or where are you a student?"),
        max_length=500)
    involvement = models.CharField(
        verbose_name=_("Your involvement"),
        help_text=_("Describe your involvement in any open source "
                    "projects or community."),
        blank=True, max_length=1024)
    what_you_want = models.CharField(
        verbose_name=u"How you use Python and how PyCon will help",
        help_text=_("Please tell us how you use Python currently, "
                    "and what you hope to get out of attending PyCon."),
        max_length=500)
    presenting = models.IntegerField(
        verbose_name=_("Presenting"),
        help_text=_("Will you be speaking, hosting a poster session, "
                    "or otherwise presenting at this PyCon?"),
        choices=PRESENTING_CHOICES)
    experience_level = models.CharField(
        verbose_name=_("Python experience level"),
        help_text=_("What is your experience level with Python?"),
        choices=PYTHON_EXPERIENCE_CHOICES,
        max_length=200)
    first_time = models.BooleanField(
        default=True,
        verbose_name=_("First time"),
        help_text=_("Is this your first time attending PyCon?"))
    presented = models.BooleanField(
        verbose_name=_("Presented"),
        help_text=_("Have you spoken at PyCon in the past?"),
        default=False)

    def __unicode__(self):
        return u"Financial aid application for %s" % self.user

    @property
    def status(self):
        try:
            return self.review.status
        except FinancialAidReviewData.DoesNotExist:
            return STATUS_SUBMITTED  # Default status

    def set_status(self, status, save=False):
        if status != self.status:
            try:
                review = self.review
            except FinancialAidReviewData.DoesNotExist:
                review = FinancialAidReviewData(application=self)
            review.status = status
            review.save()
        if save:
            self.save()

    def get_status_display(self):
        try:
            return self.review.get_status_display()
        except FinancialAidReviewData.DoesNotExist:
            return _(u"Submitted")

    def get_last_update(self):
        """Return last time the application or its review data or
        its attached messages were updated"""
        last_update = self.last_update
        try:
            last_review_update = self.review.last_update
        except FinancialAidReviewData.DoesNotExist:
            pass
        else:
            last_update = max(last_update, last_review_update)
        for msg in self.messages.all():
            last_update = max(last_update, msg.submitted_at)
        return last_update

    def get_last_update_display(self):
        return self.get_last_update().isoformat(' ')

    def fa_app_url(self):
        """URL for the detail view of a financial aid application"""
        return reverse('finaid_review_detail', args=[str(self.pk)])

    @property
    def show_status_button(self):
        return self.status != STATUS_WITHDRAWN

    @property
    def show_edit_button(self):
        return self.status == STATUS_SUBMITTED

    @property
    def show_withdraw_button(self):
        return self.status in [STATUS_SUBMITTED, STATUS_INFO_NEEDED]

    @property
    def show_accept_button(self):
        return self.status == STATUS_OFFERED

    @property
    def show_decline_button(self):
        return self.status == STATUS_OFFERED

    @property
    def show_request_more_button(self):
        return self.status == STATUS_OFFERED

    @property
    def show_provide_info_button(self):
        return self.status == STATUS_INFO_NEEDED


class FinancialAidMessage(models.Model):
    """Message attached to a financial aid application."""
    application = models.ForeignKey(FinancialAidApplication,
                                    related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             help_text=_(u"User who submitted the message"))
    visible = models.BooleanField(
        default=False,
        help_text=_(u"Whether message is visible to applicant"))
    message = models.TextField()
    submitted_at = models.DateTimeField(default=datetime.datetime.now,
                                        editable=False)

    class Meta:
        ordering = ["submitted_at"]

    def __unicode__(self):
        return u"Financial aid application message for %s" \
               % self.application.user

    def has_seen(self, user):
        """Return True if this user has seen this message"""
        return self.seen.filter(user=user).exists()

    @classmethod
    def unseen(cls, user):
        """
        Return queryset of all messages, on any application and by any
        user, this user has not seen.
        Typically you'd filter this further on a particular application
        or something."""
        return cls.objects.exclude(seen__user=user)


class FinancialAidApplicationPeriod(models.Model):
    """Represents periods when applications are open"""
    start = models.DateTimeField()
    end = models.DateTimeField()

    @classmethod
    def open(cls):
        """Return True if applications are open right now"""
        now = datetime.datetime.now()
        return bool(cls._default_manager.filter(start__lt=now, end__gt=now))

    def __unicode__(self):
        return u"Applications open %s-%s" % (self.start, self.end)


class FinancialAidReviewData(models.Model):
    """
    Data used by reviewers - about amounts granted, delivery of
    funds, etc etc.
    """
    application = models.OneToOneField(FinancialAidApplication,
                                       related_name='review',
                                       editable=False)
    last_update = models.DateTimeField(auto_now=True,
                                       editable=False)
    status = models.IntegerField(choices=STATUS_CHOICES,
                                 default=STATUS_SUBMITTED)
    amount = models.DecimalField(
        decimal_places=2, max_digits=8, default=Decimal("0.00"))
    grant_letter_sent = models.BooleanField(default=False)
    reimbursement_method = models.IntegerField(choices=PAYMENT_CHOICES,
                                              verbose_name="Reimbursement Method",
                                              blank=True, null=True)
    notes = models.TextField(blank=True)
    disbursement_notes = models.TextField(blank=True)
    promo_code = models.CharField(blank=True, max_length=20)
    legal_name = models.CharField(blank=True, max_length=2048)
    address = models.TextField(blank=True)



class FinancialAidEmailTemplate(models.Model):
    """Template for bulk mailing applicants"""
    name = models.CharField(max_length=80)
    template = models.TextField(
        help_text=u"Django template used to compose text email to applicants."
                  u"Context variables include 'application' and 'review'"
    )

    def __unicode__(self):
        return self.name


def user_directory_path(instance, filename):
    """
    Method for finding the directory path to upload a receipt to.

    This method should live inside of the Receipt model, but support for this
    behavior is only added in python3. See the following for more info:
    https://docs.djangoproject.com/en/1.7/topics/migrations/#serializing-values
    """
    # file will be uploaded to MEDIA_ROOT/finaid_receipts/<user>/<filename>
    return 'finaid_receipts/{}/{}'.format(instance.application.user.username, filename)


class Receipt(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    application = models.ForeignKey(FinancialAidApplication,
                                    related_name="receipts")

    description = models.CharField(max_length=255,
                                   help_text="Please enter a description of this receipt image.")
    amount = models.DecimalField(
        verbose_name=_("Amount"),
        help_text=_("Please enter the amount of the receipt in US dollars."),
        decimal_places=2, max_digits=8, default=Decimal("0.00"))
    receipt_image = models.FileField(upload_to=user_directory_path)
    logged = models.BooleanField(blank=False, default=False)
